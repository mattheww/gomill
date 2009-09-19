"""Connection between GTP games and the job manager."""

import datetime
import os

from gomill import gtp_games
from gomill import job_manager
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

class Game_job(object):
    """A game to be played in a worker process.

    FIXME: Let some have useful defaults, and doc

    attributes:
      game_id             -- short string (identifier-like)
      players             -- map colour -> player code
      commands            -- map colour -> string (used to launch the program)
      gtp_translations    -- map colour ->
                                 (map command string -> command string)
      board_size          -- int
      komi                -- float
      move_limit          -- int
      use_internal_scorer -- bool
      preferred_scorers   -- set or list of player codes, or None
      record_sgf          -- bool
      sgf_dir_pathname    -- directory to write SGF files to
      sgf_event           -- string to show as SGF EVent

    This is suitable for use as a job object for the job manager.

    """
    def __init__(self):
        # Set defaults here
        pass

    # The code here has to be happy to run in a separate process.

    def run(self):
        game = gtp_games.Game(self.players, self.commands,
                              self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        elif self.preferred_scorers:
            game.use_players_to_score(self.preferred_scorers)
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
        if self.record_sgf:
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
        sgf_game.set('event', self.sgf_event)
        notes = [
            "Event %s" % self.sgf_event,
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
        if not os.path.exists(self.sgf_dir_pathname):
            os.mkdir(self.sgf_dir_pathname)
        filename = "%s.sgf" % self.game_id
        f = open(os.path.join(self.sgf_dir_pathname, filename), "w")
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
