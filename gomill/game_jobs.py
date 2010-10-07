"""Connection between GTP games and the job manager."""

import datetime
import os

from gomill import gtp_controller
from gomill import gtp_games
from gomill import job_manager
from gomill.gtp_controller import BadGtpResponse, GtpChannelError

class Player(object):
    """Player description for Game_jobs.

    required attributes:
      code     -- short string
      cmd_args -- list of strings, as for subprocess.Popen

    optional attributes:
      is_reliable_scorer   -- bool (default True)
      allow_claim          -- bool (default False)
      gtp_translations     -- map command string -> command string
      startup_gtp_commands -- list of pairs (command_name, arguments)
      stderr_pathname      -- pathname or None (default None)
      cwd                  -- working directory to change to (default None)
      environ              -- maplike of environment variables (default None)

    See gtp_controllers.Gtp_controller for an explanation of gtp_translations.

    The startup commands will be executed before starting the game. Their
    responses will be ignored, but the game will be aborted if any startup
    command returns an error.

    If stderr_pathname is set, the specified file will be opened in append mode
    and the player's standard error will be sent there. Otherwise the player's
    standard error will be left as the standard error of the calling process.

    By default, the player will be given a copy of the parent process's
    environment variables; use 'environ' to add variables or replace particular
    values.

    Players are suitable for pickling.

    """
    def __init__(self):
        self.is_reliable_scorer = True
        self.allow_claim = False
        self.gtp_translations = {}
        self.startup_gtp_commands = []
        self.stderr_pathname = None
        self.cwd = None
        self.environ = None

    def make_environ(self):
        """Return environment variables to use with the player's subprocess.

        Returns a dict suitable for use with a Subprocess_channel, or None.

        """
        if self.environ is not None:
            environ = os.environ.copy()
            environ.update(self.environ)
        else:
            environ = None
        return environ

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

    A Game_job is designed to be used a job object for the job manager. That is,
    its public interface is the run() method.

    When the job is run, it plays a GTP game as described by its attributes, and
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
      sgf_filename        -- filename for the SGF file
      sgf_dirname         -- directory pathname for the SGF file
      void_sgf_dirhname   -- directory pathname for the SGF file for void games
      sgf_event           -- string to show as SGF EVent
      gtp_log_pathname    -- pathname to use for the GTP log

    The game_id will be returned in the job result, so you can tell which game
    you're getting the result for. It also appears in a comment in the SGF file.

    game_data is returned in the job result. It's provided as a convenient way
    to pass a small amount of information from get_job() to process_response().

    If use_internal_scorer is False, the Players' is_reliable_scorer attributes
    are used to decide which player is asked to score the game (if both are
    marked as reliable, black will be tried before white).

    If sgf_dirname and sgf_filename are set, an SGF file will be written after
    the game is over.

    If void_sgf_dirname and sgf_filename are set, an SGF file will be written
    for void games (games which were aborted due to unhandled errors). The
    leaf directory will be created if necessary.

    If gtp_log_pathname is set, all GTP messages to and from both players will
    be logged (this doesn't append; any existing file will be overwritten).


    Game_jobs are suitable for pickling.

    """
    def __init__(self):
        self.handicap = None
        self.handicap_is_free = False
        self.sgf_filename = None
        self.sgf_dirname = None
        self.void_sgf_dirname = None
        self.sgf_event = None
        self.use_internal_scorer = True
        self.game_data = None
        self.gtp_log_pathname = None

    # The code here has to be happy to run in a separate process.

    def run(self):
        """Run the job.

        This method is called by the job manager.

        Returns a Game_job_result, or raises JobFailed.

        """
        self._files_to_close = []
        try:
            return self._run()
        finally:
            # These files are all either flushed after every write, or not
            # written to at all from this process, so there shouldn't be any
            # errors from close().
            for f in self._files_to_close:
                try:
                    f.close()
                except EnvironmentError:
                    pass

    def _start_player(self, game, colour, player, gtp_log_file):
        if player.stderr_pathname is not None:
            stderr = open(player.stderr_pathname, "a")
            self._files_to_close.append(stderr)
        else:
            stderr = None
        if player.allow_claim:
            game.set_claim_allowed(colour)
        game.set_player_subprocess(
            colour, player.cmd_args,
            env=player.make_environ(), cwd=player.cwd, stderr=stderr)
        controller = game.get_controller(colour)
        controller.set_gtp_translations(player.gtp_translations)
        if gtp_log_file is not None:
            controller.channel.enable_logging(
                gtp_log_file, prefix="%s: " % colour)
        for command, arguments in player.startup_gtp_commands:
            game.send_command(colour, command, *arguments)

    def _run(self):
        game = gtp_games.Game(self.board_size, self.komi, self.move_limit)
        game.set_player_code('b', self.player_b.code)
        game.set_player_code('w', self.player_w.code)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        else:
            if self.player_b.is_reliable_scorer:
                game.allow_scorer('b')
            if self.player_w.is_reliable_scorer:
                game.allow_scorer('w')

        if self.gtp_log_pathname is not None:
            gtp_log_file = open(self.gtp_log_pathname, "w")
            self._files_to_close.append(gtp_log_file)
        else:
            gtp_log_file = None

        try:
            self._start_player(game, 'b', self.player_b, gtp_log_file)
            self._start_player(game, 'w', self.player_w, gtp_log_file)
            game.request_engine_descriptions()
            game.ready()
            if self.handicap:
                try:
                    game.set_handicap(self.handicap, self.handicap_is_free)
                except ValueError:
                    raise BadGtpResponse("invalid handicap")
            game.run()
        except (GtpChannelError, BadGtpResponse), e:
            game.close_players()
            msg = "aborting game due to error:\n%s" % e
            self._record_void_game(game, msg)
            late_error_messages = game.describe_late_errors()
            if late_error_messages is not None:
                msg += "\nalso:\n" + late_error_messages
            raise job_manager.JobFailed(msg)
        game.close_players()
        self._record_game(game)
        response = Game_job_result()
        response.game_id = self.game_id
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        response.game_data = self.game_data
        return response

    def _write_sgf(self, pathname, sgf_string):
        f = open(pathname, "w")
        f.write(sgf_string)
        f.close()

    def _mkdir(self, pathname):
        os.mkdir(pathname)

    def _write_game_record(self, pathname, game,
                           game_end_message=None, result=None):
        b_player = game.players['b']
        w_player = game.players['w']

        sgf_game = game.make_sgf(game_end_message)
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
        elif result is not None:
            sgf_game.set('result', result)
        notes += [
            "Black %s %s" % (b_player, game.engine_descriptions[b_player]),
            "White %s %s" % (w_player, game.engine_descriptions[w_player]),
            ]
        sgf_game.set('root-comment', "\n".join(notes))
        self._write_sgf(pathname, sgf_game.as_string())

    def _record_game(self, game):
        """Record the game in the standard sgf directory."""
        if self.sgf_dirname is None or self.sgf_filename is None:
            return
        pathname = os.path.join(self.sgf_dirname, self.sgf_filename)
        self._write_game_record(pathname, game)

    def _record_void_game(self, game, game_end_message):
        """Record the game in the void sgf directory if it had any moves."""
        if not game.moves:
            return
        if self.void_sgf_dirname is None or self.sgf_filename is None:
            return
        if not os.path.exists(self.void_sgf_dirname):
            self._mkdir(self.void_sgf_dirname)
        pathname = os.path.join(self.void_sgf_dirname, self.sgf_filename)
        self._write_game_record(pathname, game, game_end_message, result='Void')


class CheckFailed(StandardError):
    """Error reported by check_player()"""

class Player_check(object):
    """Information required to check a player.

    required attributes:
      player            -- Player
      board_size        -- int
      komi              -- float

    """

def check_player(player_check, discard_stderr=False):
    """Do a test run of a GTP engine.

    player_check -- Player_check object

    This starts an engine subprocess, sends it some GTP commands, and ends the
    process again.

    Raises CheckFailed if the player doesn't pass the checks.

    Currently checks:
     - any explicitly specified cwd exists and is a directory
     - the engine subprocess starts, and replies to GTP commands
     - the engine reports protocol version 2 (if it supports protocol_version)
     - the engine accepts any startup_gtp_commands
     - the engine accepts the specified board size and komi
     - the engine accepts the 'clear_board' command
     - the engine accepts 'quit' and closes down cleanly

    """
    player = player_check.player
    if player.cwd is not None and not os.path.isdir(player.cwd):
        raise CheckFailed("bad working directory: %s" % player.cwd)

    if discard_stderr:
        stderr = open("/dev/null", "w")
    else:
        stderr = None
    try:
        try:
            channel = gtp_controller.Subprocess_gtp_channel(
                player.cmd_args,
                env=player.make_environ(), cwd=player.cwd, stderr=stderr)
        except GtpChannelError, e:
            raise GtpChannelError(
                "error starting subprocess for %s:\n%s" % (player.code, e))
        controller = gtp_controller.Gtp_controller(channel, player.code)
        controller.set_gtp_translations(player.gtp_translations)
        controller.check_protocol_version()
        for command, arguments in player.startup_gtp_commands:
            controller.do_command(command, *arguments)
        controller.do_command("boardsize", str(player_check.board_size))
        controller.do_command("clear_board")
        controller.do_command("komi", str(player_check.komi))
        controller.do_command("quit")
        controller.close()
    except (GtpChannelError, BadGtpResponse), e:
        raise CheckFailed(str(e))
    finally:
        try:
            if stderr is not None:
                stderr.close()
        except Exception:
            pass

