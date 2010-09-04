"""Connection between GTP games and the job manager."""

import datetime

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

    If gtp_log_pathname is set, all GTP messages to and from both players will
    be logged (this doesn't append; any existing file will be overwritten).


    Game_jobs are suitable for pickling.

    """
    def __init__(self):
        self.handicap = None
        self.handicap_is_free = False
        self.sgf_pathname = None
        self.sgf_event = None
        self.use_internal_scorer = True
        self.game_data = None
        self.gtp_log_pathname = None

    # The code here has to be happy to run in a separate process.

    def run(self):
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
            # the controller will flush() this after each write, so I think we
            # can get away without closing it.
            game.set_gtp_log(open(self.gtp_log_pathname, "w"))
        # we never write to these files in this process, so I think we can get
        # away without closing them.
        if self.player_b.stderr_pathname is not None:
            stderr_b = open(self.player_b.stderr_pathname, "a")
            game.set_stderr('b', stderr_b)
        if self.player_w.stderr_pathname is not None:
            stderr_w = open(self.player_w.stderr_pathname, "a")
            game.set_stderr('w', stderr_w)
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
            raise job_manager.JobFailed("aborting game due to error:\n%s" % e)
        try:
            game.close_players()
        except StandardError, e:
            raise job_manager.JobFailed("error shutting down players:\n%s" % e)
        if self.sgf_pathname is not None:
            self.record_game(game)
        response = Game_job_result()
        response.game_id = self.game_id
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        response.game_data = self.game_data
        return response

    def record_game(self, game):
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
            "Result %s" % game.result.describe(),
            ]
        for player in [b_player, w_player]:
            cpu_time = game.result.cpu_times[player]
            if cpu_time is not None and cpu_time != "?":
                notes.append("%s cpu time: %ss" % (player, "%.2f" % cpu_time))
        notes += [
            "Black %s %s" % (b_player, game.engine_descriptions[b_player]),
            "White %s %s" % (w_player, game.engine_descriptions[w_player]),
            ]
        sgf_game.set('root-comment', "\n".join(notes))
        f = open(self.sgf_pathname, "w")
        f.write(sgf_game.as_string())
        f.close()


class CheckFailed(StandardError):
    """Error reported by check_player()"""

def check_player(player):
    """Do a test run of a GTP engine.

    player -- Player object

    This starts a subprocess for each engine, sends it a GTP command, and ends
    the process again.

    Raises CheckFailed if the player doesn't pass.

    Currently checks:
     - the engine subprocess starts, and can reply to a GTP command
     - the engine supports 'known_command'
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

    controller = gtp_controller.Gtp_controller_protocol()
    try:
        # Leaving stderr as process's stderr
        channel = gtp_controller.Subprocess_gtp_channel(player.cmd_args)
        controller.add_channel(player.code, channel)
        send("known_command", "boardsize")
        for command, arguments in player.startup_gtp_commands:
            send(command, *arguments)
        send("quit")
        controller.close_channel(player.code)
    except (GtpProtocolError, GtpTransportError, GtpEngineError), e:
        raise CheckFailed(str(e))
