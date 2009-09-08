from gomill import cem
from gomill import job_manager
from gomill import referee
from gomill import gtp_games
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

# FIXME
import random

BATCH_SIZE = 10


gnugo_fmt = "gnugo --mode=gtp --chinese-rules --capture-all-dead "
gnugo_l0 = referee.Player_config(gnugo_fmt + "--level=0")

kiai_fmt = "~/kiai/kiai13 -m kiai.mcts_player "
def kiai_player(opts):
    return referee.Player_config(kiai_fmt + opts)

def get_player(parameters):
    """

    parameters -- engine parameter vector

    Returns a Player_config

    """
    return kiai_player("--ppm=20")

class Fake_play_game_job(referee.Play_game_job):
    def run(self):
        game = gtp_games.Game(self.players, self.commands,
                              self.board_size, self.komi, self.move_limit)
        if self.use_internal_scorer:
            game.use_internal_scorer()
        elif self.preferred_scorers:
            game.use_players_to_score(self.preferred_scorers)
        game.set_gtp_translations(self.gtp_translations)
        game.fake_run(random.choice(["b", "w"]))
        if self.record_sgf:
            self.record_game(game)
        response = referee.Play_game_response()
        response.game_number = self.game_number
        response.game_result = game.result
        response.engine_names = game.engine_names
        response.engine_descriptions = game.engine_descriptions
        return response

class Tuner(object):
    """Run games in conjunction with an optimiser.

    Tuner objects are suitable for use as a job source for the job manager.

    """
    # FIXME: Doc the state variables associated with run_round.

    def __init__(self):
        self.worker_count = None
        self.opponent = gnugo_l0
        self.opponent_code = 'gnugo-l0'
        self.board_size = 13
        self.komi = 7.5
        self.move_limit = 400

    def translate_parameters(self, parameter_vectors):
        """Translate optimiser parameter vectors to engine ones."""
        return parameter_vectors[:]

    def player_sequence(self):
        # Might as well rotate quickly through players, as that's what we'll
        # want if we ever have early-out.
        for round_number in xrange(BATCH_SIZE):
            for candidate_number, player in enumerate(self.players):
                yield candidate_number, player

    @staticmethod
    def FIXMEextract_candidate_number(player_code):
        return int(player_code[9:])

    @staticmethod
    def FIXMEmake_candidate_code(candidate_number):
        return "CANDIDATE%d" % candidate_number

    @staticmethod
    def FIXMEis_candidate(player_code):
        return player_code.startswith("CANDIDATE")

    def get_job(self):
        try:
            candidate_number, player = self.player_source.next()
        except StopIteration:
            return job_manager.NoJobAvailable

        candidate_player_code = self.FIXMEmake_candidate_code(candidate_number)
        job = Fake_play_game_job()
        job.game_number = self.game_number
        job.players = {'b' : candidate_player_code, 'w' : self.opponent_code}
        job.commands = {'b' : player.cmd_args, 'w' : self.opponent.cmd_args}
        job.gtp_translations = {'b' : {}, 'w' : {}}
        job.board_size = 13
        job.komi = 7.5
        job.move_limit = 400
        job.use_internal_scorer = True
        job.preferred_scorers = {}
        job.tournament_code = "tuner"
        job.record_sgf = False
        job.sgf_dir_pathname = None
        job.run_fake_game = True
        self.game_number += 1
        return job

    def process_response(self, response):
        game_result = response.game_result
        if self.FIXMEis_candidate(game_result.winning_player):
            candidate_number = self.FIXMEextract_candidate_number(
                game_result.winning_player)
            self.wins[candidate_number] += 1

    def process_error_response(self, job, message):
        raise StandardError("error from worker for game %d\n%s" %
                            (job.game_number, message))

    def run_round(self, parameter_vectors):
        self.game_number = 0
        self.players = []
        for optimiser_parameters in parameter_vectors:
            engine_parameters = self.translate_parameters(optimiser_parameters)
            player = get_player(engine_parameters)
            self.players.append(player)
        self.wins = [0] * len(parameter_vectors)
        self.player_source = self.player_sequence()

        try:
            allow_mp = (self.worker_count is not None)
            job_manager.run_jobs(
                job_source=self,
                allow_mp=allow_mp, max_workers=self.worker_count)
        except KeyboardInterrupt:
            self.log("interrupted")
            raise
        return self.wins


def get_initial_distribution():
    # FIXME
    return cem.Distribution([(10.0, 4.0), (3.0, 4.0), (3.0, 3.0)])

def log(s):
    print s

def test():
    tuner = Tuner()
    optimiser = cem.Cem_optimiser(fitness_fn=tuner.run_round,
                                  samples_per_generation=100,
                                  elite_proportion=0.1,
                                  step_size=0.8)
    optimiser.set_brief_logger(log)
    optimiser.set_distribution(get_initial_distribution())
    converged_after = optimiser.run(
        number_of_generations=100, convergence_threshold=0.02)
    print converged_after
    print (converged_after * optimiser.samples_per_generation *
           BATCH_SIZE)
    print optimiser.distribution

if __name__ == "__main__":
    test()
