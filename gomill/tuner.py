from gomill import cem
#from gomill import job_manager
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

    def players_for_round(self):
        # Might as well rotate quickly through players, as that's what we'll
        # want if we ever have early-out.
        for round_number in xrange(BATCH_SIZE):
            for candidate_number, player in enumerate(self.players):
                yield candidate_number, player

    def play_game(self, player):
        """

        Returns true if the candidate won

        """
        players = {'b' : 'CANDIDATE', 'w' : self.opponent_code}
        commands = {'b' : player.cmd_args, 'w' : self.opponent.cmd_args}
        game = gtp_games.Game(players, commands,
                              self.board_size, self.komi, self.move_limit)
        game.use_internal_scorer()
        try:
            #game.start_players()
            #game.run()
            game.fake_run(random.choice(["b", "w"]))
        except (GtpProtocolError, GtpTransportError, GtpEngineError), e:
            raise StandardError("aborting game due to error:\n%s\n" % e)
        #try:
        #    game.close_players()
        #except StandardError, e:
        #    raise StandardError(
        #        "error shutting down players:\n%s\n" % e)
        return (game.result.winning_player == 'CANDIDATE')

    def run_round(self, parameter_vectors):
        self.game_number = 0
        self.players = []
        for i, optimiser_parameters in enumerate(parameter_vectors):
            engine_parameters = self.translate_parameters(optimiser_parameters)
            player = get_player(engine_parameters)
            player.candidate_number = i
            self.players.append(player)
        wins = [0] * len(parameter_vectors)
        for candidate_number, player in self.players_for_round():
            if self.play_game(player):
                wins[candidate_number] += 1
        return wins


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
