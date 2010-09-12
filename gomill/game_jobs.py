"""Connection between GTP games and the job manager."""

import datetime
import os

from gomill import gtp_controller
from gomill import gtp_games
from gomill import job_manager
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

class Player(object):
    """Player description for Game_jobs.

    required attributes:
      code     -- short string
      cmd_args -- list of strings, as for subprocess.Popen

    optional attributes:
      is_reliable_scorer   -- bool (default True)
      gtp_translations     -- map command string -> command string
      startup_gtp_commands -- list of pairs (command_name, arguments)
      stderr_pathname      -- pathname or None (default None)
      cwd                  -- working directory to change to (default None)

    See gtp_games for an explanation of gtp_translations.

    The startup commands will be executed before starting the game. Their
    responses will be ignored, but the game will be aborted if any startup
    command returns an error.

    If stderr_pathname is set, the specified file will be opened in append mode
    and the player's standard error will be sent there. Otherwise the player's
    standard error will be left as the standard error of the calling process.

    Players are suitable for pickling.

    """
    def __init__(self):
        self.is_reliable_scorer = True
        self.gtp_translations = {}
        self.startup_gtp_commands = []
        self.stderr_pathname = None
        self.cwd = None

class Game_job_result(object):
    """Information returned after a worker process plays a game.

    Public attributes:
      game_id               -- short string
      game_data             -- arbitrary (copied from the Game_job)
      game_result           -- gtp_games.Game_result
      engine_names          -- map player code -> string
      engine_descriptions   -- map player code -> string

    Game_job_results are suitable for pickling.

    """

class Game_job(object):
    """A game to be played in a worker process.

    A Game_job is designed to be used a job object for the job manager. When the
    job is run, it plays a GTP game as described by its attributes, and
    optionally writes an SGF file. The job result is a Game_job_result object.

    required attributes:
      game_id             -- short string
      player_b            -- Player
      player_w            -- Player
      board_size          -- int
      komi                -- float
      move_limit          -- int

    optional attributes (default None unless otherwise stated):
      game_data           -- arbitrary pickleable data
      handicap            -- int
      handicap_is_free    -- bool (default False)
      use_internal_scorer -- bool (default True)
      sgf_pathname        -- pathname to use for the SGF file
      void_sgf_pathname   -- pathname to use for the SGF file for void games
      sgf_event           -- string to show as SGF EVent
      gtp_log_pathname    -- pathname to use for the GTP log

    The game_id will be returned in the job result, so you can tell which game
    you're getting the result for. It also appears in a comment in the SGF file.

    game_data is returned in the job result. It's provided as a convenient way
    to pass a small amount of information from get_job() to process_response().

    If use_internal_scorer is False, the Players' is_reliable_scorer attributes
    are used to decide which player is asked to score the game (if both are
    marked as reliable, black will be tried before white).

    If sgf_pathname is set, an SGF file will be written after the game is over.

    If void_sgf_pathname is set, an SGF file will be written for void games
    (games which were aborted due to unhandled errors). The
    immediately-containing directory will be created if necessary.

    If gtp_log_pathname is set, all GTP messages to and from both players will
    be logged (this doesn't append; any existing file will be overwritten).


    Game_jobs are suitable for pickling.

    """
    def __init__(self):
        self.handicap = None
        self.handicap_is_free = False
        self.sgf_pathname = None
        self.void_sgf_pathname = None
        self.sgf_event = None
        self.use_internal_scorer = True
        self.game_data = None
        self.gtp_log_pathname = None

    # The code here has to be happy to run in a separate process.

    def run(self):
        files_to_close = []
        try:
            return self._run(files_to_close)
        finally:
            # These files are all either flushed after every write, or not
            # written to at all from this process, so there shouldn't be any
            # errors from close().
            for f in files_to_close:
                try:
                    f.close()
                except EnvironmentError:
                    pass

    def _run(self, files_to_close):
        game = gtp_games.Game(
            {'b' : self.player_b.code, 'w' : self.player_w.code},
            {'b' : self.player_b.cmd_args, 'w' : self.player_w.cmd_args},
            self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        else:
            if self.player_b.is_reliable_scorer:
                game.allow_scorer('b')
            if self.player_w.is_reliable_scorer:
                game.allow_scorer('w')
        game.set_gtp_translations({'b' : self.player_b.gtp_translations,
                                   'w' : self.player_w.gtp_translations})
        if self.gtp_log_pathname is not None:
            gtp_log_file = open(self.gtp_log_pathname, "w")
            files_to_close.append(gtp_log_file)
            game.set_gtp_log(gtp_log_file)
        if self.player_b.stderr_pathname is not None:
            stderr_b = open(self.player_b.stderr_pathname, "a")
            files_to_close.append(stderr_b)
            game.set_stderr('b', stderr_b)
        if self.player_w.stderr_pathname is not None:
            stderr_w = open(self.player_w.stderr_pathname, "a")
            files_to_close.append(stderr_w)
            game.set_stderr('w', stderr_w)
        game.set_cwd('b', self.player_b.cwd)
        game.set_cwd('w', self.player_w.cwd)
        try:
            game.start_players()
            for command, arguments in self.player_b.startup_gtp_commands:
                game.send_command('b', command, *arguments)
            for command, arguments in self.player_w.startup_gtp_commands:
                game.send_command('w', command, *arguments)
            game.request_engine_descriptions()
            if self.handicap:
                try:
                    game.set_handicap(self.handicap, self.handicap_is_free)
                except ValueError:
                    raise job_manager.JobFailed(
                        "aborting game: invalid handicap")
            game.run()
        except (GtpProtocolError, GtpTransportError, GtpEngineError), e:
            self.record_void_game(game)
            raise job_manager.JobFailed("aborting game due to error:\n%s" % e)
        try:
            game.close_players()
        except StandardError, e:
            self.record_void_game(game)
            raise job_manager.JobFailed("error shutting down players:\n%s" % e)
        if self.sgf_pathname is not None:
            self.record_game(self.sgf_pathname, game)
        response = Game_job_result()
        response.game_id = self.game_id
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        response.game_data = self.game_data
        return response

    def record_game(self, pathname, game):
        b_player = game.players['b']
        w_player = game.players['w']

        sgf_game = game.make_sgf()
        if self.sgf_event is not None:
            sgf_game.set('event', self.sgf_event)
            notes = ["Event '%s'" % self.sgf_event]
        else:
            notes = []
        notes += [
            "Game id %s" % self.game_id,
            "Date %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            ]
        if game.result is not None:
            notes.append("Result %s" % game.result.describe(),)
            for player in [b_player, w_player]:
                cpu_time = game.result.cpu_times[player]
                if cpu_time is not None and cpu_time != "?":
                    notes.append("%s cpu time: %ss" %
                                 (player, "%.2f" % cpu_time))
        notes += [
            "Black %s %s" % (b_player, game.engine_descriptions[b_player]),
            "White %s %s" % (w_player, game.engine_descriptions[w_player]),
            ]
        sgf_game.set('root-comment', "\n".join(notes))
        f = open(pathname, "w")
        f.write(sgf_game.as_string())
        f.close()

    def record_void_game(self, game):
        """Record the game to void_sgf_pathname if it had any moves."""
        if not game.moves:
            return
        if self.void_sgf_pathname is None:
            return
        dirname = os.path.dirname(self.void_sgf_pathname)
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        self.record_game(self.void_sgf_pathname, game)


class CheckFailed(StandardError):
    """Error reported by check_player()"""

def check_player(player, discard_stderr=False):
    """Do a test run of a GTP engine.

    player -- Player object

    This starts a subprocess for each engine, sends it a GTP command, and ends
    the process again.

    Raises CheckFailed if the player doesn't pass.

    Currently checks:
     - any explicitly specified cwd exists and is a directory
     - the engine subprocess starts, and can reply to a GTP command
     - the engine supports 'known_command'
     - the engine reports protocol version 2 (if it supports protocol_version)
     - the engine accepts any startup_gtp_commands

    """
    def send(command, *arguments):
        try:
            return controller.do_command(player.code, command, *arguments)
        except GtpEngineError, e:
            raise CheckFailed(
                "error from command '%s': %s" % (command, e))
        except GtpTransportError, e:
            raise CheckFailed(
                "transport error sending command '%s': %s" % (command, e))
        except GtpProtocolError, e:
            raise CheckFailed(
                "GTP protocol error sending command '%s': %s" % (command, e))

    if player.cwd is not None and not os.path.isdir(player.cwd):
        raise CheckFailed("bad working directory: %s" % player.cwd)

    if discard_stderr:
        stderr = open("/dev/null", "w")
    else:
        stderr = None
    controller = gtp_controller.Gtp_controller_protocol()
    try:
        channel = gtp_controller.Subprocess_gtp_channel(
            player.cmd_args, stderr=stderr, cwd=player.cwd)
        controller.add_channel(player.code, channel)
        pv_known = send("known_command", "protocol_version")
        if pv_known == "true":
            protocol_version = send("protocol_version")
            if protocol_version != "2":
                raise CheckFailed(
                    "reports GTP protocol version %s" % protocol_version)
        for command, arguments in player.startup_gtp_commands:
            send(command, *arguments)
        send("quit")
        controller.close_channel(player.code)
    except (GtpProtocolError, GtpTransportError, GtpEngineError), e:
        raise CheckFailed(str(e))
    finally:
        try:
            if stderr is not None:
                stderr.close()
        except Exception:
            pass

