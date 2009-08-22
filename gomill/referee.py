"""Organise tournaments using GTP."""

from __future__ import division

import datetime
import os
import sys
from optparse import OptionParser

import simplejson as json

from gomill import compact_tracebacks
from gomill import gtp_games
from gomill import job_manager
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)


def read_python_file(pathname, provided_globals):
    result = {}
    f = open(pathname)
    exec f in provided_globals.copy(), result
    f.close()
    return result


def json_decode_game_result(dct):
    if 'winning_colour' not in dct:
        return dct
    result = gtp_games.Game_result()
    for key, value in dct.iteritems():
        setattr(result, key, value)
    return result

def json_encode_game_result(obj):
    if isinstance(obj, gtp_games.Game_result):
        return obj.__dict__
    raise TypeError(repr(obj) + " is not JSON serializable")


class Play_game_response(object):
    """Response from Play_game_job.run().

    This is the data that is passed back from worker processes.

    Public attributes:
      game_number
      game_result
      engine_names
      engine_descriptions

    """

class Play_game_job(object):
    """Play a game in a worker process.

    This is a job object used by the job manager. That means it may be run in a
    separate process.

    attributes:

      game_number
      players
      commands
      board_size
      komi
      move_limit
      use_internal_scorer
      preferred_scorers
      tournament_code
      record_sgf
      sgf_dir_pathname

    """

    def run(self):
        game = gtp_games.Game(self.players, self.commands,
                              self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        elif self.preferred_scorers:
            game.use_players_to_score(self.preferred_scorers)
        try:
            game.start_players()
            game.request_engine_descriptions()
            game.run()
        except (GtpProtocolError, GtpTransportError, GtpEngineError), e:
            raise job_manager.JobFailed("aborting game due to error:\n%s\n" % e)
        try:
            game.close_players()
        except StandardError, e:
            raise job_manager.JobFailed(
                "error shutting down players:\n%s\n" % e)
        if self.record_sgf:
            self.record_game(game)
        response = Play_game_response()
        response.game_number = self.game_number
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        return response

    def record_game(self, game):
        b_player = game.players['b']
        w_player = game.players['w']

        sgf_game = game.make_sgf()
        sgf_game.set('application', "gomill-referee:?")
        sgf_game.set('event', self.tournament_code)
        sgf_game.set('round', self.game_number)
        notes = [
            "Tournament %s" % self.tournament_code,
            "Game number %d" % self.game_number,
            "Date %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Black %s %s" % (b_player, game.engine_descriptions[b_player]),
            "White %s %s" % (w_player, game.engine_descriptions[w_player]),
            "Result %s" % game.result.describe(),
            ]
        for player in [b_player, w_player]:
            cpu_time = game.result.cpu_times[player]
            if cpu_time is not None and cpu_time != "?":
                notes.append("%s cpu time: %ss" % (player, "%.2f" % cpu_time))
        sgf_game.set('root-comment', "\n".join(notes))
        if not os.path.exists(self.sgf_dir_pathname):
            os.mkdir(self.sgf_dir_pathname)
        filename = "%d.sgf" % self.game_number
        f = open(os.path.join(self.sgf_dir_pathname, filename), "w")
        f.write(sgf_game.as_string())
        f.close()

class Player_config(object):
    """Player description for use in tournament files."""
    def __init__(self, command_string):
        self.cmd_args = command_string.split()
        self.cmd_args[0] = os.path.expanduser(self.cmd_args[0])

tournament_globals = {
    'Player' : Player_config,
    }


class TournamentError(StandardError):
    """Error reported by a Tournament."""

class Tournament(object):
    """Manage a tournament as described by a tournament configuration file.

    Tournament objects are suitable for use as a job source for the job manager.

    """

    def __init__(self, tourn_pathname):
        self.chatty = True
        self.worker_count = None

        stem = tourn_pathname.rpartition(".tourn")[0]
        self.tournament_code = os.path.basename(stem)
        self.log_pathname = stem + ".log"
        self.status_pathname = stem + ".status"
        self.command_pathname = stem + ".cmd"
        self.report_pathname = stem + ".report"
        self.sgf_dir_pathname = stem + ".games"

        try:
            config = read_python_file(tourn_pathname, tournament_globals)
        except EnvironmentError, e:
            raise TournamentError("failed to open tournament file:\n%s" % e)
        except:
            raise TournamentError("error in tournament file:\n%s" %
                                  compact_tracebacks.format_error_and_line())

        try:
            if os.path.exists(self.command_pathname):
                os.remove(self.command_pathname)
        except EnvironmentError, e:
            raise TournamentError("error removing existing .cmd file:\n%s" % e)


        # Ought to validate.
        self.description = config['description']
        self.players = config.get('players', {})
        for player, s in config.get('player_commands', {}).items():
            self.players[player] = Player_config(s)

        self.board_size = config['board_size']
        self.komi = config['komi']
        self.move_limit = config['move_limit']
        self.number_of_games = config.get('number_of_games')
        self.record_games = config['record_games']
        self.use_internal_scorer = False
        self.preferred_scorers = None
        if 'scorer' in config:
            if config['scorer'] == "internal":
                self.use_internal_scorer = True
            elif config['scorer'] == "players":
                self.preferred_scorers = config.get('preferred_scorers')
            else:
                raise ValueError

        uses_legacy_matchups = ('player_x' in config or
                                'player_y' in config or
                                'alternating' in config)
        if uses_legacy_matchups:
            if 'matchups' in config:
                raise ValueError
            self.matchups = [(config['player_x'], config['player_y'])]
            if config['alternating']:
                self.matchups.append((config['player_y'], config['player_x']))
        else:
            self.matchups = config['matchups']
        for p1, p2 in self.matchups:
            if p1 not in self.players or p2 not in self.players:
                raise ValueError

        self.engine_names = {}
        self.engine_descriptions = {}
        self.results = []
        self.total_errors = 0
        self.next_game_number = 0

        self.games_in_progress = 0
        self.recent_errors = 0
        self.stopping = False
        self.stopping_reason = None
        self.max_games_this_run = None

        try:
            self.logfile = open(self.log_pathname, "a")
        except EnvironmentError, e:
            raise TournamentError("failed to open log file:\n%s" % e)

    def set_parallel_worker_count(self, n):
        self.worker_count = n

    def log(self, s):
        print >>self.logfile, s

    def warn(self, s):
        print >>sys.stderr, "**", s
        print >>self.logfile, s

    def games_played(self):
        return len(self.results)

    def write_status(self):
        status = {
            'results' : self.results,
            'total_errors' : self.total_errors,
            'next_game_number' : self.next_game_number,
            'engine_names' : self.engine_names,
            'engine_descriptions' : self.engine_descriptions,
            }
        f = open(self.status_pathname + ".new", "w")
        json.dump(status, f, default=json_encode_game_result)
        f.close()
        os.rename(self.status_pathname + ".new", self.status_pathname)

    def load_status(self):
        f = open(self.status_pathname)
        status = json.load(f, object_hook=json_decode_game_result)
        self.results = status['results']
        self.total_errors = status['total_errors']
        self.next_game_number = status['next_game_number']
        self.engine_names = status['engine_names']
        self.engine_descriptions = status['engine_descriptions']
        f.close()

    def status_file_exists(self):
        return os.path.exists(self.status_pathname)

    def format_report_header(self, out):
        def p(s):
            print >>out, s
        p("tournament: %s" % self.tournament_code)
        for code, description in sorted(self.engine_descriptions.items()):
            p("player %s: %s" % (code, description))
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)
        p(self.description)

    def format_pairing_report(self, out, player_x, player_y):
        def p(s):
            print >>out, s
        results = [r for r in self.results
                   if (r.player_b == player_x and r.player_w == player_y) or
                      (r.player_b == player_y and r.player_w == player_x)]
        total = len(results)
        if total == 0:
            return
        x_wins = len([1 for r in results if r.winning_player == player_x])
        y_wins = len([1 for r in results if r.winning_player == player_y])
        unknown = len([1 for r in results if r.winning_player is None])
        b_wins = len([1 for r in results if r.winning_colour == 'b'])
        w_wins = len([1 for r in results if r.winning_colour == 'w'])
        xb_wins = len([1 for r in results if
                       r.winning_player == player_x and
                       r.winning_colour == 'b'])
        xw_wins = len([1 for r in results if
                       r.winning_player == player_x and
                       r.winning_colour == 'w'])
        yb_wins = len([1 for r in results if
                       r.winning_player == player_y and
                       r.winning_colour == 'b'])
        yw_wins = len([1 for r in results if
                       r.winning_player == player_y and
                       r.winning_colour == 'w'])
        xb_played = len([1 for r in results if
                         r.player_b == player_x])
        xw_played = len([1 for r in results if
                         r.player_w == player_x])
        yb_played = len([1 for r in results if
                         r.player_b == player_y])
        yw_played = len([1 for r in results if
                         r.player_w == player_y])

        x_times = [r.cpu_times[player_x] for r in results]
        x_known_times = [t for t in x_times if t is not None and t != '?']
        if x_known_times:
            x_avg_time_s = "%7.2f" % (sum(x_known_times) / len(x_known_times))
        else:
            x_avg_time = "----"
        y_times = [r.cpu_times[player_y] for r in results]
        y_known_times = [t for t in y_times if t is not None and t != '?']
        if y_known_times:
            y_avg_time_s = "%7.2f" % (sum(y_known_times) / len(y_known_times))
        else:
            y_avg_time = "----"

        p("%s vs %s (%d games)" % (player_x, player_y, total))
        def pct(n, baseline):
            if baseline == 0:
                if n == 0:
                    return "--"
                else:
                    return "??"
            return "%.2f%%" % (100 * n/baseline)
        if unknown > 0:
            p("unknown results: %d %s" % (unknown, pct(unknown, total)))

        pad = max(len(player_x), len(player_y)) + 2
        xname = player_x.ljust(pad)
        yname = player_y.ljust(pad)

        p(" " * (pad+17) + "   black         white        avg cpu")
        p("%s %4d %7s    %4d %7s  %4d %7s  %s"
          % (xname, x_wins, pct(x_wins, total),
             xb_wins, pct(xb_wins, xb_played),
             xw_wins, pct(xw_wins, xw_played),
             x_avg_time_s))
        p("%s %4d %7s    %4d %7s  %4d %7s  %s"
          % (yname, y_wins, pct(y_wins, total),
             yb_wins, pct(yb_wins, yb_played),
             yw_wins, pct(yw_wins, yw_played),
             y_avg_time_s))
        p(" " * (pad+17) + "%4d %7s  %4d %7s"
          % (b_wins, pct(b_wins, total), w_wins, pct(w_wins, total)))
        p("")

    def format_brief_report(self, out):
        # matchups without regard to colour choice
        pairings = sorted(set(tuple(sorted(t)) for t in self.matchups))
        for player_x, player_y in pairings:
            self.format_pairing_report(out, player_x, player_y)

    def format_report(self, out):
        self.format_report_header(out)
        self.format_brief_report(out)
        def p(s):
            print >>out, s
        for i, result in enumerate(self.results):
            p("%3d %s" % (i, result.describe()))

    def report(self):
        f = open(self.report_pathname, "w")
        self.format_report(f)
        f.close()

    def get_job(self):
        if self.chatty:
            if self.total_errors > 0:
                print "!! %d errors occurred; see log file." % self.total_errors
            if self.stopping:
                print "waiting for workers to finish: %s" % self.stopping_reason
        if self.stopping:
            return job_manager.NoJobAvailable
        if self.recent_errors > 1:
            self.stopping = True
            self.stopping_reason = "too many errors"
            self.warn("too many errors, giving up tournament")
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
                    return job_manager.NoJobAvailable
        except EnvironmentError, e:
            self.warn("error reading .cmd file:\n%s" % e)
        if self.max_games_this_run is not None:
            if self.max_games_this_run == 0:
                self.warn("max-games reached for this run")
                self.stopping = True
                self.stopping_reason = "max-games reached for this run"
                return job_manager.NoJobAvailable
            self.max_games_this_run -= 1

        games_played = self.games_played()
        if (self.number_of_games is not None and
            games_played + self.games_in_progress >= self.number_of_games):
            return job_manager.NoJobAvailable
        game_number = self.next_game_number
        self.next_game_number += 1
        player_b, player_w = self.matchups[game_number % len(self.matchups)]
        commands = {'b' : self.players[player_b].cmd_args,
                    'w' : self.players[player_w].cmd_args}
        players = {'b' : player_b, 'w' : player_w}
        start_msg = "starting game %d: %s (b) vs %s (w)" % (
            game_number, player_b, player_w)
        if self.chatty:
            if self.number_of_games is None:
                print "%d games played; %d in progress" % (
                    games_played, self.games_in_progress)
            else:
                print "%d/%d games played; %d in progress" % (
                    games_played, self.number_of_games, self.games_in_progress)
            print start_msg
            if self.max_games_this_run is not None:
                print ("will start at most %d more games in this run" %
                       self.max_games_this_run)
        self.log(start_msg)
        self.games_in_progress += 1
        job = Play_game_job()
        job.game_number = game_number
        job.players = players
        job.commands = commands
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = self.use_internal_scorer
        job.preferred_scorers = self.preferred_scorers
        job.tournament_code = self.tournament_code
        job.record_sgf = self.record_games
        job.sgf_dir_pathname = self.sgf_dir_pathname
        return job

    def process_response(self, response):
        self.games_in_progress -= 1
        self.recent_errors = 0
        self.engine_names.update(response.engine_names)
        self.engine_descriptions.update(response.engine_names)
        self.results.append(response.game_result)
        if self.chatty:
            os.system("clear")
            print "game %d completed: %s" % (
                response.game_number, response.game_result.describe())
            print
            self.format_brief_report(sys.stdout)
        self.write_status()

    def process_error_response(self, job, message):
        self.games_in_progress -= 1
        self.total_errors += 1
        self.recent_errors += 1
        self.warn("error from worker for game %d\n%s" %
                  (job.game_number, message))

    def run(self, max_games=None):
        self.max_games_this_run = max_games
        try:
            allow_mp = (self.worker_count is not None)
            job_manager.run_jobs(
                job_source=self,
                allow_mp=allow_mp, max_workers=self.worker_count)
        except KeyboardInterrupt:
            self.log("interrupted")
            raise


def do_tournament(tourn_pathname, worker_count=None, quiet=False,
                  max_games=None):
    tournament = Tournament(tourn_pathname)
    if quiet:
        tournament.chatty = False
    if tournament.status_file_exists():
        print "status file exists; continuing"
        tournament.load_status()
    if tournament.number_of_games is None:
        print "no limit on number of games"
        if not tournament.chatty:
            print "%d games played so far" % tournament.games_played()
    else:
        games_remaining = tournament.number_of_games - tournament.games_played()
        if games_remaining <= 0:
            print "tournament already complete"
        if not tournament.chatty:
            print "%d/%d games to play" % (
                games_remaining, tournament.number_of_games)
    if worker_count is not None:
        print "using %d workers" % worker_count
        tournament.set_parallel_worker_count(worker_count)
    tournament.run(max_games)
    tournament.report()

def do_show(tourn_pathname):
    tournament = Tournament(tourn_pathname)
    if not tournament.status_file_exists():
        raise TournamentError("no status file")
    tournament.load_status()
    tournament.format_report_header(sys.stdout)
    tournament.format_brief_report(sys.stdout)

def do_report(tourn_pathname):
    tournament = Tournament(tourn_pathname)
    if not tournament.status_file_exists():
        raise TournamentError("no status file")
    tournament.load_status()
    tournament.report()

def do_stop(tourn_pathname):
    tournament = Tournament(tourn_pathname)
    try:
        f = open(tournament.command_pathname, "w")
        f.write("stop")
        f.close()
    except EnvironmentError, e:
        raise TournamentError("error writing command file:\n%s" % e)

def main():
    usage = ("%prog [options] <tournament file> [command]\n\n"
             "commands: run (default), stop, show, report")
    parser = OptionParser(usage=usage)
    parser.add_option("--max-games", "-g", type="int",
                      help="maximum number of games to play in this run")
    parser.add_option("--parallel", "-j", type="int",
                      help="number of worker processes")
    parser.add_option("--quiet", "-q", action="store_true",
                      help="print less information while running")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("no tournament specified")
    if len(args) > 2:
        parser.error("too many arguments")
    if len(args) == 1:
        command = "run"
    else:
        command = args[1]
        if command not in ("run", "stop", "show", "report"):
            parser.error("no such command: %s" % command)
    tourn_pathname = args[0]
    if not tourn_pathname.endswith(".tourn"):
        parser.error("not a .tourn file")
    try:
        if not os.path.exists(tourn_pathname):
            raise TournamentError("no such tournament")
        if command == "run":
            do_tournament(tourn_pathname,
                          options.parallel, options.quiet, options.max_games)
        elif command == "show":
            do_show(tourn_pathname)
        elif command == "stop":
            do_stop(tourn_pathname)
        elif command == "report":
            do_report(tourn_pathname)
        else:
            raise AssertionError
    except TournamentError, e:
        print >>sys.stderr, "referee.py:", e
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(3)

if __name__ == "__main__":
    main()

