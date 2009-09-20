"""Organise tournaments using GTP."""

from __future__ import division

import datetime
import os
import shlex
import shutil
import sys
from optparse import OptionParser

import simplejson as json

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import gtp_games
from gomill import job_manager
from gomill.competitions import NoGameAvailable
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

class Player_config(object):
    """Player description for use in tournament files."""
    def __init__(self, command_string, gtp_translations=None):
        # Ought to validate
        self.cmd_args = shlex.split(command_string)
        self.cmd_args[0] = os.path.expanduser(self.cmd_args[0])
        if gtp_translations is None:
            self.gtp_translations = {}
        else:
            self.gtp_translations = gtp_translations

tournament_globals = {
    'Player' : Player_config,
    }

def read_tourn_file(pathname):
    """Read the specified file as a .tourn file.

    A copy of tournament_globals is used as the global namespace. Returns this
    namespace as a dict.

    """
    result = tournament_globals.copy()
    f = open(pathname)
    exec f in result
    f.close()
    return result


# To be work here, a class must be a simple holder for its attributes, all its
# attributes must be json-serialisable, and __init__ must accept no parameters.
# Also, the class shouldn't have any attributes that don't need serialising.

json_encodable_classes = {
    gtp_games.Game_result : 'R',
    game_jobs.Game_job    : 'J',
    }

json_decodable_classes = {
    'R' : gtp_games.Game_result,
    'J' : game_jobs.Game_job,
    }

def ringmaster_json_encode_default(obj):
    cls = json_encodable_classes.get(obj.__class__)
    if cls is None:
        raise TypeError(repr(obj) + " is not JSON-serialisable")
    result = obj.__dict__
    result['_cls'] = cls
    return result

def ringmaster_json_decode_object_hook(dct):
    try:
        cls = json_decodable_classes[dct.pop('_cls')]
    except KeyError:
        return dct
    result = cls()
    for key, value in dct.iteritems():
        setattr(result, key, value)
    return result


def clear_screen():
    os.system("clear")

class RingmasterError(StandardError):
    """Error reported by a Ringmaster."""

class Ringmaster(object):
    """Manage a competition as described by a control file.

    Ringmaster objects are used as a job source for the job manager.

    """
    def __init__(self, tourn_pathname):
        self.chatty = True
        self.worker_count = None
        self.max_games_this_run = None
        self.stopping = False
        self.stopping_reason = None
        self.total_errors = 0
        # These are both maps game_id -> Game_job
        self.games_in_progress = {}
        self.games_to_replay = {}
        # Map game_id -> int
        self.game_error_counts = {}

        stem = tourn_pathname.rpartition(".tourn")[0]
        self.competition_code = os.path.basename(stem)
        self.log_pathname = stem + ".log"
        self.status_pathname = stem + ".status"
        self.command_pathname = stem + ".cmd"
        self.report_pathname = stem + ".report"
        self.sgf_dir_pathname = stem + ".games"

        try:
            config = read_tourn_file(tourn_pathname)
        except EnvironmentError, e:
            raise RingmasterError("failed to open control file:\n%s" % e)
        except:
            raise RingmasterError("error in control file:\n%s" %
                                  compact_tracebacks.format_error_and_line())
        self.initialise_from_control_file(config)

        # Will need a registry, and look up by config file.
        from gomill import tournaments
        self.competition = tournaments.Tournament(self.competition_code)
        self.competition.set_logger(self.log)
        self.competition.initialise_from_control_file(config)

        try:
            if os.path.exists(self.command_pathname):
                os.remove(self.command_pathname)
        except EnvironmentError, e:
            raise RingmasterError("error removing existing .cmd file:\n%s" % e)

        try:
            self.logfile = open(self.log_pathname, "a")
        except EnvironmentError, e:
            raise RingmasterError("failed to open log file:\n%s" % e)

    def initialise_from_control_file(self, config):
        self.record_games = config['record_games']

    def set_quiet_mode(self, b=True):
        self.chatty = not(b)

    def set_parallel_worker_count(self, n):
        self.worker_count = n

    def log(self, s):
        print >>self.logfile, s
        self.logfile.flush()

    def warn(self, s):
        print >>sys.stderr, "**", s
        print >>self.logfile, s
        self.logfile.flush()

    def write_status(self):
        competition_status = self.competition.get_status()
        status = {
            'total_errors' : self.total_errors,
            'in_progress'  : self.games_in_progress,
            'to_replay'    : self.games_to_replay,
            'comp'         : competition_status,
            }
        f = open(self.status_pathname + ".new", "w")
        json.dump(status, f, default=ringmaster_json_encode_default)
        f.close()
        os.rename(self.status_pathname + ".new", self.status_pathname)

    def load_status(self):
        f = open(self.status_pathname)
        status = json.load(f, object_hook=ringmaster_json_decode_object_hook)
        f.close()
        self.total_errors = status['total_errors']
        self.games_in_progress = {}
        self.games_to_replay = status['to_replay']
        self.games_to_replay.update(status['in_progress'])
        competition_status = status['comp']
        self.competition.set_status(competition_status)

    def status_file_exists(self):
        return os.path.exists(self.status_pathname)

    def report(self):
        """Write the full competition report to the report file."""
        f = open(self.report_pathname, "w")
        self.competition.write_static_description(f)
        self.competition.write_status_summary(f)
        self.competition.write_results_report(f)
        f.close()

    def print_status_report(self):
        """Write current status to standard output."""
        self.competition.write_static_description(sys.stdout)
        self.competition.write_status_summary(sys.stdout)

    def get_job(self):

        def describe_stopping():
            if self.chatty:
                print "waiting for workers to finish: %s" % self.stopping_reason
                print "%d games in progress" % len(self.games_in_progress)

        if self.stopping:
            describe_stopping()
            return job_manager.NoJobAvailable
        try:
            if os.path.exists(self.command_pathname):
                command = open(self.command_pathname).read()
                if command == "stop":
                    self.warn("stop command received; "
                              "waiting for games to finish")
                    self.stopping = True
                    self.stopping_reason = "stop command received"
                    try:
                        os.remove(self.command_pathname)
                    except EnvironmentError, e:
                        self.warn("error removing .cmd file:\n%s" % e)
                    describe_stopping()
                    return job_manager.NoJobAvailable
        except EnvironmentError, e:
            self.warn("error reading .cmd file:\n%s" % e)
        if self.max_games_this_run is not None:
            if self.max_games_this_run == 0:
                self.stopping = True
                self.stopping_reason = "max-games reached for this run"
                describe_stopping()
                return job_manager.NoJobAvailable
            self.max_games_this_run -= 1

        if self.games_to_replay:
            _, job = self.games_to_replay.popitem()
        else:
            job = self.competition.get_game()
            if job is NoGameAvailable:
                return job_manager.NoJobAvailable
            if self.record_games:
                job.sgf_pathname = os.path.join(
                    self.sgf_dir_pathname, "%s.sgf" % job.game_id)
        self.games_in_progress[job.game_id] = job
        start_msg = "starting game %s: %s (b) vs %s (w)" % (
            job.game_id, job.players['b'], job.players['w'])
        self.log(start_msg)
        if self.chatty:
            print start_msg
            print "%d games in progress" % len(self.games_in_progress)
            if self.max_games_this_run is not None:
                print ("will start at most %d more games in this run" %
                       self.max_games_this_run)
        return job

    def update_display(self):
        if self.chatty:
            clear_screen()
            if self.total_errors > 0:
                print "!! %d errors occurred; see log file." % self.total_errors
            self.competition.write_status_summary(sys.stdout)

    def process_response(self, response):
        self.log("response from game %s" % response.game_id)
        self.competition.process_game_result(response)
        del self.games_in_progress[response.game_id]
        self.write_status()
        self.update_display()
        if self.chatty:
            print "game %s completed: %s" % (
                response.game_id, response.game_result.describe())

    def process_error_response(self, job, message):
        warning_message = "error from worker for game %s\n%s" % (
            job.game_id, message)
        self.warn(warning_message)
        self.total_errors += 1
        previous_error_count = self.game_error_counts.get(job.game_id, 0)
        stop_competition, retry_game = \
            self.competition.process_game_error(job, previous_error_count)
        if retry_game:
            self.games_to_replay[job.game_id] = \
                self.games_in_progress.pop(job.game_id)
            self.game_error_counts[job.game_id] = previous_error_count + 1
        else:
            del self.games_in_progress.pop[job.game_id]
            if previous_error_count != 0:
                del self.game_error_counts[job.game_id]
        if stop_competition:
            self.stopping = True
            self.stopping_reason = "seen errors, giving up on competition"
        self.write_status()
        self.update_display()
        if self.chatty:
            # we need to reprint this because the screen was cleared
            print warning_message

    def run(self, max_games=None):
        def now():
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        self.log("run started at %s with max_games %s" % (now(), max_games))
        self.max_games_this_run = max_games
        if self.record_games:
            try:
                if not os.path.exists(self.sgf_dir_pathname):
                    os.mkdir(self.sgf_dir_pathname)
            except EnvironmentError:
                raise RingmasterError("failed to create SGF directory:\n%s" % e)
        self.update_display()
        try:
            allow_mp = (self.worker_count is not None)
            job_manager.run_jobs(
                job_source=self,
                allow_mp=allow_mp, max_workers=self.worker_count)
        except KeyboardInterrupt:
            self.log("run interrupted run %s" % now())
            raise
        self.log("run finished at %s" % now())

    def delete_state_and_output(self):
        for pathname in [
            self.log_pathname,
            self.status_pathname,
            self.command_pathname,
            self.report_pathname]:
            if os.path.exists(pathname):
                try:
                    os.remove(pathname)
                except EnvironmentError, e:
                    print >>sys.stderr, e
        if os.path.exists(self.sgf_dir_pathname):
            shutil.rmtree(self.sgf_dir_pathname)

def do_run(tourn_pathname, worker_count=None, quiet=False,
           max_games=None):
    ringmaster = Ringmaster(tourn_pathname)
    if quiet:
        ringmaster.set_quiet_mode()
    if ringmaster.status_file_exists():
        ringmaster.load_status()
    if worker_count is not None:
        ringmaster.set_parallel_worker_count(worker_count)
    ringmaster.run(max_games)
    ringmaster.report()

def do_show(tourn_pathname):
    ringmaster = Ringmaster(tourn_pathname)
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.print_status_report()

def do_report(tourn_pathname):
    ringmaster = Ringmaster(tourn_pathname)
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.report()

def do_stop(tourn_pathname):
    ringmaster = Ringmaster(tourn_pathname)
    try:
        f = open(ringmaster.command_pathname, "w")
        f.write("stop")
        f.close()
    except EnvironmentError, e:
        raise RingmasterError("error writing command file:\n%s" % e)

def do_reset(tourn_pathname):
    ringmaster = Ringmaster(tourn_pathname)
    ringmaster.delete_state_and_output()

def main():
    usage = ("%prog [options] <control file> [command]\n\n"
             "commands: run (default), stop, show, report, reset")
    parser = OptionParser(usage=usage)
    parser.add_option("--max-games", "-g", type="int",
                      help="maximum number of games to play in this run")
    parser.add_option("--parallel", "-j", type="int",
                      help="number of worker processes")
    parser.add_option("--quiet", "-q", action="store_true",
                      help="silent except for warnings and errors")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("no control file specified")
    if len(args) > 2:
        parser.error("too many arguments")
    if len(args) == 1:
        command = "run"
    else:
        command = args[1]
        if command not in ("run", "stop", "show", "report", "reset"):
            parser.error("no such command: %s" % command)
    tourn_pathname = args[0]
    if not tourn_pathname.endswith(".tourn"):
        parser.error("not a .tourn file")
    try:
        if not os.path.exists(tourn_pathname):
            raise RingmasterError("control file not found")
        if command == "run":
            do_run(tourn_pathname,
                   options.parallel, options.quiet, options.max_games)
        elif command == "show":
            do_show(tourn_pathname)
        elif command == "stop":
            do_stop(tourn_pathname)
        elif command == "report":
            do_report(tourn_pathname)
        elif command == "reset":
            do_reset(tourn_pathname)
        else:
            raise AssertionError
    except RingmasterError, e:
        print >>sys.stderr, "ringmaster:", e
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(3)

if __name__ == "__main__":
    main()

