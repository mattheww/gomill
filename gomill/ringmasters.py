"""Organise tournaments using GTP."""

from __future__ import division

import cPickle as pickle
import datetime
import os
import shutil
import sys
from cStringIO import StringIO

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import job_manager
from gomill import ringmaster_presenters
from gomill.settings import *
from gomill.competitions import (
    NoGameAvailable, CompetitionError, ControlFileError, control_file_globals,
    LOG, DISCARD)

def read_python_file(pathname, provided_globals):
    """Load Python code from the specified file.

    pathname         -- string
    provided_globals -- dict

    The file contents are executed, with a copy of provided_globals as the
    global and local namespace. Returns that namespace.

    """
    result = provided_globals.copy()
    f = open(pathname)
    exec f in result
    f.close()
    return result

class RingmasterError(StandardError):
    """Error reported by a Ringmaster."""

class RingmasterInternalError(StandardError):
    """Error reported by a Ringmaster which indicates a bug."""


class Ringmaster(object):
    """Manage a competition as described by a control file.

    Most methods can raise RingmasterError.

    Instantiate with the pathname of the control file. The control file is read
    and interpreted at instantiation time (and errors are reported at that
    point).

    Ringmaster objects are used as a job source for the job manager.

    """
    # Can bump this to prevent people loading incompatible .status files.
    status_format_version = 0

    # For --version command
    public_version = "gomill ringmaster v0.5"

    # Class attribute so that subclasses can modify
    control_file_globals = control_file_globals

    def __init__(self, tourn_pathname):
        """Instantiate and initialise a Ringmaster.

        Reads the control file.

        Creates the Competition and initialises it from the control file.

        """
        self.chatty = True
        self.worker_count = None
        self.max_games_this_run = None
        self.stopping = False
        self.stopping_reason = None
        # Map game_id -> int
        self.game_error_counts = {}
        self.write_gtp_logs = False

        stem = tourn_pathname.rpartition(".tourn")[0]
        self.competition_code = os.path.basename(stem)
        self.log_pathname = stem + ".log"
        self.status_pathname = stem + ".status"
        self.command_pathname = stem + ".cmd"
        self.history_pathname = stem + ".hist"
        self.report_pathname = stem + ".report"
        self.sgf_dir_pathname = stem + ".games"
        self.gtplog_dir_pathname = stem + ".gtplogs"

        try:
            config = read_python_file(tourn_pathname, self.control_file_globals)
        except EnvironmentError, e:
            raise RingmasterError("failed to read control file:\n%s" % e)
        except:
            raise RingmasterError("error in control file:\n%s" %
                                  compact_tracebacks.format_error_and_line())
        try:
            self._initialise_from_control_file(config)
        except ControlFileError, e:
            raise RingmasterError("error in control file:\n%s" % e)
        except StandardError, e:
            raise RingmasterError("unhandled error in control file:\n%s" %
                                  compact_tracebacks.format_traceback(skip=1))

        try:
            competition_class = self._get_competition_class(
                config.get("competition_type"))
        except ValueError:
            raise RingmasterError("competition_type: unknown value")
        self.competition = competition_class(self.competition_code)
        try:
            self.competition.initialise_from_control_file(config)
        except ControlFileError, e:
            raise RingmasterError("error in control file:\n%s" % e)
        except StandardError, e:
            raise RingmasterError("unhandled error in control file:\n%s" %
                                  compact_tracebacks.format_traceback(skip=1))

        self.presenter = ringmaster_presenters.Presenter()

    @staticmethod
    def _get_competition_class(competition_type):
        """Find the competition class.

        competition_type -- string

        Returns a Competition subclass.

        Raises ValueError if the competition type is unknown.

        """
        if competition_type is None:
            competition_type = "tournament"
        if competition_type == "tournament":
            from gomill import tournaments
            return tournaments.Tournament
        elif competition_type == "cem_tuner":
            from gomill import cem_tuners
            return cem_tuners.Cem_tuner
        elif competition_type == "mcts_tuner":
            from gomill import mcts_tuners
            return mcts_tuners.Mcts_tuner
        else:
            raise ValueError

    def _open_files(self):
        """Open the log files and ensure that output directories exist.

        Also removes the command file if it exists.

        """
        try:
            if os.path.exists(self.command_pathname):
                os.remove(self.command_pathname)
        except EnvironmentError, e:
            raise RingmasterError("error removing existing .cmd file:\n%s" % e)

        try:
            self.logfile = open(self.log_pathname, "a")
        except EnvironmentError, e:
            raise RingmasterError("failed to open log file:\n%s" % e)

        try:
            self.historyfile = open(self.history_pathname, "a")
        except EnvironmentError, e:
            raise RingmasterError("failed to open history file:\n%s" % e)

        if self.record_games:
            try:
                if not os.path.exists(self.sgf_dir_pathname):
                    os.mkdir(self.sgf_dir_pathname)
            except EnvironmentError:
                raise RingmasterError("failed to create SGF directory:\n%s" % e)

        if self.write_gtp_logs:
            try:
                if not os.path.exists(self.gtplog_dir_pathname):
                    os.mkdir(self.gtplog_dir_pathname)
            except EnvironmentError:
                raise RingmasterError(
                    "failed to create GTP log directory:\n%s" % e)

    def _close_files(self):
        """Close the log files."""
        try:
            self.logfile.close()
        except EnvironmentError, e:
            raise RingmasterError("error closing log file:\n%s" % e)
        try:
            self.historyfile.close()
        except EnvironmentError, e:
            raise RingmasterError("error closing history file:\n%s" % e)

    ringmaster_settings = [
        Setting('record_games', interpret_bool, False),
        ]

    def _initialise_from_control_file(self, config):
        """Interpret the parts of the control file which belong to Ringmaster.

        Sets attributes from ringmaster_settings.

        """
        try:
            to_set = load_settings(self.ringmaster_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))
        for name, value in to_set.items():
            setattr(self, name, value)

    def set_quiet_mode(self, b=True):
        self.chatty = not(b)

    def enable_gtp_logging(self, b=True):
        self.write_gtp_logs = b

    def set_parallel_worker_count(self, n):
        self.worker_count = n

    def log(self, s):
        print >>self.logfile, s
        self.logfile.flush()

    def warn(self, s):
        if not self.chatty:
            print >>sys.stderr, s
        self.log(s)
        if self.chatty:
            self.presenter.say('warnings', s)

    def log_history(self, s):
        print >>self.historyfile, s
        self.historyfile.flush()


    # State attributes (*: in persistent state):
    #  * void_game_count   -- int
    #  * comp              -- from Competition.get_status()
    #    games_in_progress -- dict game_id -> Game_job
    #    games_to_replay   -- dict game_id -> Game_job

    def write_status(self):
        """Write the persistent state file."""
        competition_status = self.competition.get_status()
        status = {
            'void_game_count' : self.void_game_count,
            'comp'         : competition_status,
            }
        f = open(self.status_pathname + ".new", "wb")
        pickle.dump((self.status_format_version, status), f, protocol=-1)
        f.close()
        os.rename(self.status_pathname + ".new", self.status_pathname)

    def load_status(self):
        """Read the persistent state file and load the state it contains."""
        try:
            f = open(self.status_pathname, "rb")
            status_format_version, status = pickle.load(f)
            f.close()
        except pickle.UnpicklingError:
            raise RingmasterError("corrupt status file")
        except StandardError, e:
            raise RingmasterError("error reading status file: %s" % e)
        if status_format_version != self.status_format_version:
            raise RingmasterError("incompatible status file")
        self.void_game_count = status['void_game_count']
        self.games_in_progress = {}
        self.games_to_replay = {}
        competition_status = status['comp']
        try:
            self.competition.set_status(competition_status)
        except CompetitionError, e:
            raise RingmasterError(e)

    def set_clean_status(self):
        """Reset persistent state to the initial values."""
        self.void_game_count = 0
        self.games_in_progress = {}
        self.games_to_replay = {}
        try:
            self.competition.set_clean_status()
        except CompetitionError, e:
            raise RingmasterError(e)

    def status_file_exists(self):
        """Check whether the persistent state file exists."""
        return os.path.exists(self.status_pathname)

    def print_status(self):
        """Print the contents of the persistent state file, for debugging."""
        from pprint import pprint
        f = open(self.status_pathname, "rb")
        status_format_version, status = pickle.load(f)
        f.close()
        print "status_format_version:", status_format_version
        pprint(status)

    def write_command(self, command):
        """Write a command to the command file.

        command -- short string

        Overwrites the command file if it already exists.

        """
        # Short enough that I think we can get aw
        try:
            f = open(self.command_pathname, "w")
            f.write(command)
            f.close()
        except EnvironmentError, e:
            raise RingmasterError("error writing command file:\n%s" % e)

    def report(self):
        """Write the full competition report to the report file."""
        f = open(self.report_pathname, "w")
        self.competition.write_full_report(f)
        f.close()

    def print_status_report(self):
        """Write current competition status to standard output.

        This is for the 'show' command.

        """
        self.competition.write_short_report(sys.stdout)

    def update_display(self):
        """Redisplay the 'live' competition description.

        Does nothing in quiet mode.

        """
        if not self.chatty:
            return
        def p(s):
            self.presenter.say('status', s)
        self.presenter.clear('status')
        if self.worker_count is not None:
            p("%d games in progress" % len(self.games_in_progress))
        if self.stopping:
            if self.worker_count is None or not self.games_in_progress:
                p(self.stopping_reason)
            else:
                p("waiting for workers to finish: %s" %
                  self.stopping_reason)
        else:
            if self.max_games_this_run is not None:
                p("will start at most %d more games in this run" %
                  self.max_games_this_run)

        self.presenter.clear('screen_report')
        if self.void_game_count > 0:
            self.presenter.say(
                'screen_report',
                "%d void games; see log file." % self.void_game_count)
        si = StringIO()
        self.competition.write_screen_report(si)
        self.presenter.say('screen_report', si.getvalue())
        si.close()

        self.presenter.refresh()

    def _prepare_job(self, job):
        """Finish off a Game_job provided by the Competition.

        job -- incomplete Game_job, as returned by Competition.get_game()

        """
        if self.record_games:
            job.sgf_pathname = os.path.join(
                self.sgf_dir_pathname, "%s.sgf" % job.game_id)
        if self.write_gtp_logs:
            job.gtp_log_pathname = os.path.join(
                    self.gtplog_dir_pathname, "%s.log" % job.game_id)
        for player in (job.player_b, job.player_w):
            if player._stderr is DISCARD:
                player.stderr_pathname = os.devnull
            elif player._stderr is LOG:
                player.stderr_pathname = self.log_pathname

    def get_job(self):
        """Job supply function for the job manager."""
        job = self._get_job()
        self.update_display()
        return job

    def _get_job(self):
        """Main implementation of get_job()."""

        if self.stopping:
            return job_manager.NoJobAvailable
        try:
            if os.path.exists(self.command_pathname):
                command = open(self.command_pathname).read()
                if command == "stop":
                    self.log("stop command received; "
                             "waiting for games to finish")
                    self.stopping = True
                    self.stopping_reason = "stop command received"
                    try:
                        os.remove(self.command_pathname)
                    except EnvironmentError, e:
                        self.warn("error removing .cmd file:\n%s" % e)
                    return job_manager.NoJobAvailable
        except EnvironmentError, e:
            self.warn("error reading .cmd file:\n%s" % e)
        if self.max_games_this_run is not None:
            if self.max_games_this_run == 0:
                self.stopping = True
                self.stopping_reason = "max-games reached for this run"
                return job_manager.NoJobAvailable
            self.max_games_this_run -= 1

        if self.games_to_replay:
            _, job = self.games_to_replay.popitem()
        else:
            job = self.competition.get_game()
            if job is NoGameAvailable:
                return job_manager.NoJobAvailable
            if job.game_id in self.games_in_progress:
                raise CompetitionError("duplicate game id: %s" % job.game_id)
            self._prepare_job(job)
        self.games_in_progress[job.game_id] = job
        start_msg = "starting game %s: %s (b) vs %s (w)" % (
            job.game_id, job.player_b.code, job.player_w.code)
        self.log(start_msg)

        return job

    def process_response(self, response):
        """Job response function for the job manager."""
        # We log before processing the result, in case there's an error from the
        # competition code.
        self.log("response from game %s" % response.game_id)
        self.competition.process_game_result(response)
        del self.games_in_progress[response.game_id]
        self.write_status()
        if self.chatty:
            self.presenter.say(
                'results',
                "game %s completed: %s" % (
                    response.game_id, response.game_result.describe()))

    def process_error_response(self, job, message):
        """Job error response function for the job manager."""
        self.warn("game %s -- %s" % (
            job.game_id, message))
        self.void_game_count += 1
        previous_error_count = self.game_error_counts.get(job.game_id, 0)
        stop_competition, retry_game = \
            self.competition.process_game_error(job, previous_error_count)
        if retry_game and not stop_competition:
            self.games_to_replay[job.game_id] = \
                self.games_in_progress.pop(job.game_id)
            self.game_error_counts[job.game_id] = previous_error_count + 1
        else:
            del self.games_in_progress[job.game_id]
            if previous_error_count != 0:
                del self.game_error_counts[job.game_id]
        self.write_status()
        if stop_competition:
            self.warn("halting run due to void games")
            self.stopping = True
            self.stopping_reason = "halting run due to void games"

    def run(self, max_games=None):
        """Run the competition.

        max_games -- int or None (maximum games to start in this run)

        Returns when max_games have been played in this run, when the
        Competition is over, or when a 'stop' command is received via the
        command file.

        """
        def now():
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        def log_games_in_progress():
            try:
                msg = "games in progress were: %s" % (
                    " ".join(sorted(self.games_in_progress)))
            except:
                pass
            self.log(msg)

        self._open_files()
        self.competition.set_event_logger(self.log)
        self.competition.set_history_logger(self.log_history)

        self.log("run started at %s with max_games %s" % (now(), max_games))
        self.max_games_this_run = max_games
        self.update_display()
        try:
            allow_mp = (self.worker_count is not None)
            job_manager.run_jobs(
                job_source=self,
                allow_mp=allow_mp, max_workers=self.worker_count,
                passed_exceptions=[CompetitionError])
        except KeyboardInterrupt:
            self.log("run interrupted at %s" % now())
            log_games_in_progress()
            raise
        except CompetitionError, e:
            self.log("run finished with error at %s\n%s" % (now(), e))
            log_games_in_progress()
            raise RingmasterError(e)
        except job_manager.JobSourceError, e:
            self.log("run finished with internal error at %s\n%s" % (now(), e))
            log_games_in_progress()
            raise RingmasterInternalError(e)
        except:
            self.log("run finished with internal error at %s" % now())
            self.log(compact_tracebacks.format_traceback())
            log_games_in_progress()
            raise
        self.log("run finished at %s" % now())
        self._close_files()

    def delete_state_and_output(self):
        """Delete all files generated by this competition.

        Deletes the persistent state file, game records, log files, and reports.

        """
        for pathname in [
            self.log_pathname,
            self.status_pathname,
            self.command_pathname,
            self.history_pathname,
            self.report_pathname,
            ]:
            if os.path.exists(pathname):
                try:
                    os.remove(pathname)
                except EnvironmentError, e:
                    print >>sys.stderr, e
        for pathname in [
            self.sgf_dir_pathname,
            self.gtplog_dir_pathname,
            ]:
            if os.path.exists(pathname):
                try:
                    shutil.rmtree(pathname)
                except EnvironmentError, e:
                    print >>sys.stderr, e

    def check_players(self, discard_stderr=False):
        """Check that the engines required for the competition will run.

        If an engine fails, prints a description of the problem and returns
        False without continuing to check.

        Otherwise returns True.

        """
        try:
            to_check = self.competition.get_players_to_check()
        except CompetitionError, e:
            raise RingmasterError(e)
        for player in to_check:
            try:
                game_jobs.check_player(player, discard_stderr=discard_stderr)
            except game_jobs.CheckFailed, e:
                print "player %s failed startup check:\n%s" % (player.code, e)
                return False
        return True

