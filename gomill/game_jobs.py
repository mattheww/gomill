"""Connection between GTP games and the job manager."""

import datetime
import os

from gomill import gtp_controller
from gomill import gtp_games
from gomill import job_manager
from gomill import utils
from gomill.gtp_controller import BadGtpResponse, GtpChannelError

class Player(object):
    """Player description for Game_jobs.

    required attributes:
      code     -- short string
      cmd_args -- list of strings, as for subprocess.Popen

    optional attributes:
      is_reliable_scorer   -- bool (default True)
      allow_claim          -- bool (default False)
      gtp_aliases          -- map command string -> command string
      startup_gtp_commands -- list of pairs (command_name, arguments)
      discard_stderr       -- bool (default False)
      cwd                  -- working directory to change to (default None)
      environ              -- maplike of environment variables (default None)
      sgf_player_name_from_gtp -- Use gtp player name in sgf files (default True)

    See gtp_controllers.Gtp_controller for an explanation of gtp_aliases.

    The startup commands will be executed before starting the game. Their
    responses will be ignored, but the game will be aborted if any startup
    command returns an error.

    By default, the player will be given a copy of the parent process's
    environment variables; use 'environ' to add variables or replace particular
    values.

    Players are suitable for pickling.

    """
    def __init__(self):
        self.is_reliable_scorer = True
        self.allow_claim = False
        self.gtp_aliases = {}
        self.startup_gtp_commands = []
        self.discard_stderr = False
        self.cwd = None
        self.environ = None
        self.sgf_player_name_from_gtp = True

    def make_environ(self):
        """Return environment variables to use with the player's subprocess.

        Returns a dict suitable for use with a Subprocess_gtp_channel.

        """
        environ = os.environ.copy()
        if self.environ is not None:
            environ.update(self.environ)
        return environ

    def copy(self, code):
        """Return an independent clone of the Player."""
        result = Player()
        result.code = code
        result.cmd_args = list(self.cmd_args)
        result.is_reliable_scorer = self.is_reliable_scorer
        result.allow_claim = self.allow_claim
        result.discard_stderr = self.discard_stderr
        result.sgf_player_name_from_gtp = self.sgf_player_name_from_gtp
        result.gtp_aliases = dict(self.gtp_aliases)
        result.startup_gtp_commands = list(self.startup_gtp_commands)
        result.cwd = self.cwd
        if self.environ is None:
            result.environ = None
        else:
            result.environ = dict(self.environ)
        return result

class Game_job_result(object):
    """Information returned after a worker process plays a game.

    Public attributes:
      game_id               -- short string
      game_data             -- arbitrary (copied from the Game_job)
      game_result           -- gtp_games.Game_result
      warnings              -- list of strings
      log_entries           -- list of strings
      engine_descriptions   -- map player code -> Engine_description

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
      internal_scorer_handicap_compensation -- 'no' , 'short', or 'full'
                             (default 'no')
      sgf_filename        -- filename for the SGF file
      sgf_dirname         -- directory pathname for the SGF file
      void_sgf_dirname    -- directory pathname for the SGF file for void games
      sgf_game_name       -- string to show as SGF Game Name (default game_id)
      sgf_event           -- string to show as SGF EVent
      sgf_note            -- multiline string to put into SGF root comment
      gtp_log_pathname    -- pathname to use for the GTP log
      stderr_pathname     -- pathname to send players' stderr to

    The game_id will be returned in the job result, so you can tell which game
    you're getting the result for. It also appears in the SGF file as a comment
    and the GN property.

    game_data is returned in the job result. It's provided as a convenient way
    to pass a small amount of information from get_job() to process_response().

    If use_internal_scorer is False, the Players' is_reliable_scorer attributes
    are used to determine who scores the game (see errors.rst).

    If sgf_dirname and sgf_filename are set, an SGF file will be written after
    the game is over.

    If void_sgf_dirname and sgf_filename are set, an SGF file will be written
    for any void games (games which were aborted due to unhandled errors) which
    have at least one move. The leaf directory will be created if necessary.

    If gtp_log_pathname is set, all GTP messages to and from both players will
    be logged (this doesn't append; any existing file will be overwritten).

    If stderr_pathname is set, the specified file will be opened in append mode
    and both players' standard error streams will be sent there. Otherwise the
    players' standard error streams will be left as the standard error of the
    calling process. But if a player has discard_stderr=True then its standard
    error is sent to os.devnull instead.

    Game_jobs are suitable for pickling.

    """
    def __init__(self):
        self.handicap = None
        self.handicap_is_free = False
        self.sgf_filename = None
        self.sgf_dirname = None
        self.void_sgf_dirname = None
        self.sgf_game_name = None
        self.sgf_event = None
        self.sgf_note = None
        self.use_internal_scorer = True
        self.internal_scorer_handicap_compensation = 'no'
        self.game_data = None
        self.gtp_log_pathname = None
        self.stderr_pathname = None

    # The code here has to be happy to run in a separate process.

    def run(self, worker_id=None):
        """Run the job.

        This method is called by the job manager.

        worker_id -- int or None

        Returns a Game_job_result, or raises JobFailed.

        """
        self._worker_id = worker_id
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

    def _start_player(self, game_controller, game,
                      colour, player, gtp_log_file):
        if player.discard_stderr:
            stderr_pathname = os.devnull
        else:
            stderr_pathname = self.stderr_pathname
        if stderr_pathname is not None:
            stderr = open(stderr_pathname, "a")
            self._files_to_close.append(stderr)
        else:
            stderr = None
        if not self.use_internal_scorer and player.is_reliable_scorer:
            game.allow_scorer(colour)
        if player.allow_claim:
            game.set_claim_allowed(colour)
        env = player.make_environ()
        env['GOMILL_GAME_ID'] = self.game_id
        if self._worker_id is not None:
            env['GOMILL_SLOT'] = str(self._worker_id)
        game_controller.set_player_subprocess(
            colour, player.cmd_args,
            env=env, cwd=player.cwd, stderr=stderr)
        controller = game_controller.get_controller(colour)
        controller.set_gtp_aliases(player.gtp_aliases)
        if gtp_log_file is not None:
            controller.channel.enable_logging(
                gtp_log_file, prefix="%s: " % colour)
        for command, arguments in player.startup_gtp_commands:
            game_controller.send_command(colour, command, *arguments)

    def _run(self):
        warnings = []
        log_entries = []
        try:
            game_controller = gtp_controller.Game_controller(
                self.player_b.code, self.player_w.code)
            game = gtp_games.Gtp_game(
                game_controller, self.board_size, self.komi, self.move_limit)
            game.set_game_id(self.game_id)
        except ValueError, e:
            raise job_manager.JobFailed("error creating game: %s" % e)
        if self.use_internal_scorer:
            game.use_internal_scorer(self.internal_scorer_handicap_compensation)

        if self.gtp_log_pathname is not None:
            gtp_log_file = open(self.gtp_log_pathname, "w")
            self._files_to_close.append(gtp_log_file)
        else:
            gtp_log_file = None

        try:
            self._start_player(game_controller, game,
                               'b', self.player_b, gtp_log_file)
            self._start_player(game_controller, game,
                               'w', self.player_w, gtp_log_file)
            game.prepare()
            if self.handicap:
                try:
                    game.set_handicap(self.handicap, self.handicap_is_free)
                except ValueError:
                    raise BadGtpResponse("invalid handicap")
            game.run()
        except (GtpChannelError, BadGtpResponse), e:
            game_controller.close_players()
            msg = "aborting game due to error:\n%s" % e
            self._record_void_game(game_controller, game, msg)
            late_error_messages = game_controller.describe_late_errors()
            if late_error_messages is not None:
                msg += "\nalso:\n" + late_error_messages
            raise job_manager.JobFailed(msg)
        if game.result.is_forfeit:
            warnings.append(game.result.detail)
        game_controller.close_players()
        ru_cpu_times = game_controller.get_resource_usage_cpu_times()
        for colour in game.cpu_time_errors:
            del ru_cpu_times[colour]
        game.result.soft_update_cpu_times(ru_cpu_times)
        late_error_messages = game_controller.describe_late_errors()
        if late_error_messages:
            log_entries.append(late_error_messages)
        self._record_game(game_controller, game)
        response = Game_job_result()
        response.game_id = self.game_id
        response.game_result = game.result
        response.warnings = warnings
        response.log_entries = log_entries

        response.engine_descriptions = {
            self.player_b.code : game_controller.engine_descriptions['b'],
            self.player_w.code : game_controller.engine_descriptions['w'],
            }
        response.game_data = self.game_data
        return response

    def _make_sgf(self, game_controller, game, game_end_message=None):
        """Return an Sgf_game with annotations.

        This adds the following to the result of Gtp_game.make_sgf:

        GN -- sgf_game_name
        EV -- sgf_event

        Prepends to the root node comment:
          game id
          date and time
          result description (except in zero-move games)
          sgf_note
          cpu times
          engine descriptions

        Adds to the last node's comment:
          any game_end_message
          describe_late_errors() output

        """
        b_player = self.player_b.code
        w_player = self.player_w.code
        notes = []
        sgf_game = game.make_sgf()
        root = sgf_game.get_root()
        last_node = sgf_game.get_last_node()
        if self.sgf_game_name is not None:
            root.set('GN', self.sgf_game_name)
        if self.sgf_event is not None:
            root.set('EV', self.sgf_event)
            notes.append("Event: %s" % self.sgf_event)
        notes += [
            "Game id %s" % self.game_id,
            "Date %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            ]
        if game.result is not None and root is not last_node:
            notes.append("Result %s" % game.result.describe())
        if self.sgf_note is not None:
            notes.append(self.sgf_note)
        if game.result is not None:
            for player in [b_player, w_player]:
                cpu_time = game.result.cpu_times[player]
                if cpu_time is not None:
                    notes.append("%s cpu time: %ss" %
                                 (player, "%.2f" % cpu_time))

        for player, colour, note in ((self.player_b, 'b', "Black"),
                                     (self.player_w, 'w', "White")):
            note += " " + player.code
            ed = game_controller.engine_descriptions[colour]
            longdesc = ed.get_long_description()
            if longdesc:
                note += " " + longdesc
            notes.append(note)
            if not player.sgf_player_name_from_gtp:
                root.set('P' + colour.upper(), player.code)

        if root.has_property("C"):
            existing_comment = root.get("C")
            notes.append("")
            notes.append(existing_comment)
        root.set("C", "\n".join(notes))
        if game_end_message is not None:
            last_node.add_comment_text(game_end_message)
        late_error_messages = game_controller.describe_late_errors()
        if late_error_messages is not None:
            last_node.add_comment_text(late_error_messages)
        return sgf_game

    def _record_game(self, game_controller, game):
        """Record the game in the standard sgf directory."""
        if self.sgf_dirname is None or self.sgf_filename is None:
            return
        pathname = os.path.join(self.sgf_dirname, self.sgf_filename)
        sgf_game = self._make_sgf(game_controller, game)
        self._write_sgf(pathname, sgf_game.serialise())

    def _record_void_game(self, game_controller, game, game_end_message):
        """Record the game in the void sgf directory if it had any moves.

        Sets sgf RE to 'Void'.

        """
        if not game.get_moves():
            return
        if self.void_sgf_dirname is None or self.sgf_filename is None:
            return
        self._ensure_dir(self.void_sgf_dirname)
        pathname = os.path.join(self.void_sgf_dirname, self.sgf_filename)
        sgf_game = self._make_sgf(game_controller, game, game_end_message)
        sgf_game.get_root().set('RE', 'Void')
        self._write_sgf(pathname, sgf_game.serialise())

    def _write_sgf(self, pathname, sgf_string):
        # For overriding in the testsuite
        f = open(pathname, "w")
        f.write(sgf_string)
        f.close()

    def _ensure_dir(self, pathname):
        # For overriding in the testsuite
        utils.ensure_dir(pathname)


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

    Returns a list of warning messages.

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
        stderr = open(os.devnull, "w")
    else:
        stderr = None
    try:
        env = player.make_environ()
        env['GOMILL_GAME_ID'] = 'startup-check'
        try:
            channel = gtp_controller.Subprocess_gtp_channel(
                player.cmd_args,
                env=env, cwd=player.cwd, stderr=stderr)
        except GtpChannelError, e:
            raise GtpChannelError(
                "error starting subprocess for %s:\n%s" % (player.code, e))
        controller = gtp_controller.Gtp_controller(channel, player.code)
        controller.set_gtp_aliases(player.gtp_aliases)
        controller.check_protocol_version()
        for command, arguments in player.startup_gtp_commands:
            controller.do_command(command, *arguments)
        controller.do_command("boardsize", str(player_check.board_size))
        controller.do_command("clear_board")
        controller.do_command("komi", str(player_check.komi))
        controller.safe_close()
    except (GtpChannelError, BadGtpResponse), e:
        raise CheckFailed(str(e))
    else:
        return controller.retrieve_error_messages()
    finally:
        try:
            if stderr is not None:
                stderr.close()
        except Exception:
            pass

