"""Connection between GTP games and the job manager."""

import datetime

from gomill import gtp_games
from gomill import job_manager
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

class Game_job(object):
    """A game to be played in a worker process.

    A Game_job is designed to be used a job object for the job manager. When the
    job is run, it plays a GTP game as described by its attributes, and
    optionally writes an SGF file.

    required attributes:
      game_id             -- short string
      players             -- map colour -> player code
      commands            -- map colour -> string (used to launch the program)
      board_size          -- int
      komi                -- float
      move_limit          -- int

    optional attributes:
      sgf_pathname        -- pathname to use for the SGF file, or None
      sgf_event           -- string to show as SGF EVent
      use_internal_scorer -- bool
      preferred_scorers   -- set or list of player codes, or None
      gtp_translations    -- map colour ->
                                 (map command string -> command string)

    The game_id will be returned in the job result, so you can tell which game
    you're getting the result for. It also appears in a comment in the SGF file.

    Leave sgf_pathname None if you don't want to write an SGF file.

    See gtp_games for an explanation of the 'scorer' attributes and
    gtp_translations.

    """
    def __init__(self):
        self.sgf_pathname = None
        self.sgf_event = None
        self.use_internal_scorer = True
        self.preferred_scorers = None
        self.gtp_translations = None

    # The code here has to be happy to run in a separate process.

    def run(self):
        game = gtp_games.Game(self.players, self.commands,
                              self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        elif self.preferred_scorers:
            game.use_players_to_score(self.preferred_scorers)
        if self.gtp_translations is not None:
            game.set_gtp_translations(self.gtp_translations)
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

class Game_job_result(object):
    """Information returned after a worker process plays a game.

    Public attributes:
      game_id               -- int
      game_result           -- gtp_games.Game_result
      engine_names          -- map colour -> string
      engine_descriptions   -- map colour -> string

    """
