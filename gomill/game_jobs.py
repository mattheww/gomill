"""Connection between GTP games and the job manager."""

import datetime

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
      gtp_translations     -- map command string -> command string
      startup_gtp_commands -- list of pairs (command_name, arguments)

    See gtp_games for an explanation of gtp_translations.

    The startup commands will be executed before starting the game. Their
    responses will be ignored, but the game will be aborted if any startup
    command returns an error.

    """
    def __init__(self):
        self.gtp_translations = {}

class Game_job_result(object):
    """Information returned after a worker process plays a game.

    Public attributes:
      game_id               -- int
      game_result           -- gtp_games.Game_result
      engine_names          -- map colour -> string
      engine_descriptions   -- map colour -> string

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
      handicap            -- int
      handicap_is_free    -- bool (default False)
      sgf_pathname        -- pathname to use for the SGF file
      sgf_event           -- string to show as SGF EVent
      use_internal_scorer -- bool (default True)
      preferred_scorers   -- set or list of player codes

    The game_id will be returned in the job result, so you can tell which game
    you're getting the result for. It also appears in a comment in the SGF file.

    Leave sgf_pathname None if you don't want to write an SGF file.

    See gtp_games for an explanation of the 'scorer' attributes.

    """
    def __init__(self):
        self.handicap = None
        self.handicap_is_free = False
        self.sgf_pathname = None
        self.sgf_event = None
        self.use_internal_scorer = True
        self.preferred_scorers = None

    # The code here has to be happy to run in a separate process.

    def run(self):
        game = gtp_games.Game(
            {'b' : self.player_b.code, 'w' : self.player_w.code},
            {'b' : self.player_b.cmd_args, 'w' : self.player_w.cmd_args},
            self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        elif self.preferred_scorers:
            game.use_players_to_score(self.preferred_scorers)
        game.set_gtp_translations({'b' : self.player_b.gtp_translations,
                                   'w' : self.player_w.gtp_translations})
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
            raise job_manager.JobFailed("aborting game due to error:\n%s\n" % e)
        try:
            game.close_players()
        except StandardError, e:
            raise job_manager.JobFailed(
                "error shutting down players:\n%s\n" % e)
        if self.sgf_pathname is not None:
            self.record_game(game)
        response = Game_job_result()
        response.game_id = self.game_id
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        return response

    def record_game(self, game):
        b_player = game.players['b']
        w_player = game.players['w']

        sgf_game = game.make_sgf()
        sgf_game.set('application', "gomill:?")
        if self.sgf_event is not None:
            sgf_game.set('event', self.sgf_event)
            notes = ["Event %s" % self.sgf_event]
        else:
            notes = []
        notes += [
            "Game id %s" % self.game_id,
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
        f = open(self.sgf_pathname, "w")
        f.write(sgf_game.as_string())
        f.close()

