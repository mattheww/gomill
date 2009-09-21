"""Competitions for parameter tuning using the cross-entropy method."""

from random import gauss as random_gauss
from math import sqrt

from gomill import game_jobs
from gomill.competitions import Competition, NoGameAvailable, Player_config

BATCH_SIZE = 3
SAMPLES_PER_GENERATION = 5
NUMBER_OF_GENERATIONS = 3
ELITE_PROPORTION = 0.1
STEP_SIZE = 0.8


def square(f):
    return f * f

class Distribution(object):
    """A multi-dimensional Gaussian probability distribution.

    Instantiate with a list of pairs of floats (mean, variance)

    Public attributes:
      parameters -- the list used to instantiate the distribution

    """
    def __init__(self, parameters):
        self.dimension = len(parameters)
        self.parameters = parameters
        self.gaussian_params = [(mean, sqrt(variance))
                                for (mean, variance) in parameters]

    def get_sample(self):
        """Return a random sample from the distribution.

        Returns a list of floats

        """
        return [random_gauss(mean, stddev)
                for (mean, stddev) in self.gaussian_params]

    def get_means(self):
        """Return just the mean from each dimension.

        Returns a list of floats.

        """
        return [mean for (mean, stddev) in self.parameters]

    def format(self):
        return " ".join("%5.2f~%4.2f" % (mean, stddev)
                        for (mean, stddev) in self.parameters)

    def __str__(self):
        return "<distribution %s>" % self.format()

def update_distribution(distribution, elites):
    """Update a distribution based on the given elitss.

    distribution -- Distribution
    elites       -- list of optimiser parameter vectors

    Returns a new distribution

    """
    n = len(elites)
    new_distribution_parameters = []
    for i in range(distribution.dimension):
        v = [e[i] for e in elites]
        elite_mean = sum(v) / n
        elite_var = sum(map(square, v)) / n - square(elite_mean)
        old_mean, old_var = distribution.parameters[i]
        new_mean = (elite_mean * STEP_SIZE +
                    old_mean * (1.0 - STEP_SIZE))
        new_var = (elite_var * STEP_SIZE +
                   old_var * (1.0 - STEP_SIZE))
        new_distribution_parameters.append((new_mean, new_var))
    return Distribution(new_distribution_parameters)


def get_initial_distribution():
    # FIXME
    # The dimensions are resign_at and log_10 (playouts_per_move)
    return Distribution([(0.5, 1.0), (2.0, 2.0)])


class Cem_tuner(Competition):
    """A Competition for parameter tuning using the cross-entropy method."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)
        self.candidate_maker = config['make_candidate']
        # FIXME: Proper CANDIDATE object or something.
        self.matchups = config['matchups']
        for p1, p2 in self.matchups:
            if p1 == "CANDIDATE":
                other = p2
            elif p2 == "CANDIDATE":
                other = p1
            else:
                raise ValueError
            if other not in self.players:
                raise ValueError
        # FIXME: Later sort out rotating through; for now just use last matchup
        # but have candidate always take black
        self.opponent = other

    def translate_parameters(self, optimiser_params):
        """Translate an optimiser parameter vector to an engine one."""
        # The dimensions are resign_at and log_10 (playouts_per_move)
        opt_resign_at, opt_playouts_per_move = optimiser_params
        resign_at = max(0.0, min(1.0, opt_resign_at))
        playouts_per_move = int(10**opt_playouts_per_move)
        playouts_per_move = max(10, min(3000, playouts_per_move))
        return [resign_at, playouts_per_move]

    def format_parameters(self, optimiser_params):
        """Pretty-print an optimiser parameter vector.

        Returns a string.

        """
        resign_at, opt_playouts_per_move = optimiser_params
        clipped_resign_at = max(0.0, min(1.0, resign_at))
        if resign_at == clipped_resign_at:
            resign_at_s = "%.2f       " % resign_at
        else:
            resign_at_s = "%.2f(% .2f)" % (clipped_resign_at, resign_at)
        ppm = int(10**opt_playouts_per_move)
        clipped_ppm = max(10, min(3000, ppm))
        if ppm == clipped_ppm:
            ppm_s = "%4s       " % ppm
        else:
            ppm_s = "%4s(%5s)" % (clipped_ppm, ppm)
        return "%s %s" % (resign_at_s, ppm_s)

    def format_distribution(self, distribution):
        """Pretty-print a distribution.

        Returns a string.

        """
        return "%s\n%s" % (self.format_parameters(distribution.get_means()),
                           distribution.format())

    @staticmethod
    def make_candidate_code(generation, candidate_number):
        return "g%d#%d" % (generation, candidate_number)

    @staticmethod
    def is_candidate_code(player_code):
        return '#' in player_code

    def reset_for_new_generation(self):
        get_sample = self.distribution.get_sample
        self.sample_parameters = [get_sample()
                                  for _ in xrange(SAMPLES_PER_GENERATION)]
        assert len(self.sample_parameters) == SAMPLES_PER_GENERATION
        # List of Players to be indexed by candidate number
        self.candidates = []
        self.candidate_numbers_by_code = {}
        for candidate_number, optimiser_params in \
                enumerate(self.sample_parameters):
            candidate_code = self.make_candidate_code(
                self.generation, candidate_number)
            candidate_config = self.candidate_maker(
                self.translate_parameters(optimiser_params))
            candidate = candidate_config.get_game_jobs_player()
            candidate.code = candidate_code
            self.candidates.append(candidate)
            self.candidate_numbers_by_code[candidate_code] = candidate_number
        self.round = 0
        self.next_candidate = 0
        self.wins = [0] * SAMPLES_PER_GENERATION
        self.results_required_count = BATCH_SIZE * SAMPLES_PER_GENERATION
        self.results_seen_count = 0

    def format_generation_results(self, ordered_samples, elite_count):
        """Pretty-print the results of a single generation.

        ordered_samples -- list of pairs (wins, candidate number)
        elite_count     -- number of samples to mark as elite

        Returns a list of strings

        """
        result = []
        for i, (wins, candidate_number) in enumerate(ordered_samples):
            opt_parameters = self.sample_parameters[candidate_number]
            result.append(
                "%s%s %s %3d" %
                (self.make_candidate_code(self.generation, candidate_number),
                 "*" if i < elite_count else " ",
                 self.format_parameters(opt_parameters),
                 wins))
        return "\n".join(result)

    def finish_generation(self):
        sorter = [(wins, candidate_number)
                  for (candidate_number, wins) in enumerate(self.wins)]
        sorter.sort(reverse=True)
        elite_count = max(1,
            int(ELITE_PROPORTION * SAMPLES_PER_GENERATION + 0.5))
        self.log_history("Generation %s" % self.generation)
        self.log_history("Distribution\n%s" %
                         self.format_distribution(self.distribution))
        self.log_history(self.format_generation_results(sorter, elite_count))
        self.log_history("")
        elite_samples = [self.sample_parameters[index]
                         for (wins, index) in sorter[:elite_count]]
        self.distribution = update_distribution(
            self.distribution, elite_samples)

    def get_status(self):
        return {}

    def set_status(self, status):
        FIXME

    def set_clean_status(self):
        self.finished = False
        self.generation = 0
        self.distribution = get_initial_distribution()
        self.reset_for_new_generation()

    def get_game(self):
        if self.finished:
            return NoGameAvailable

        if self.round == BATCH_SIZE:
            # Send no more games until the new generation
            return NoGameAvailable

        if self.round == 0 and self.next_candidate == 0:
            self.log("\nstarting generation %d" % self.generation)

        candidate = self.candidates[self.next_candidate]
        game_id = "%sr%d" % (candidate.code, self.round)

        self.next_candidate += 1
        if self.next_candidate == SAMPLES_PER_GENERATION:
            self.next_candidate = 0
            self.round += 1

        job = game_jobs.Game_job()
        job.game_id = game_id
        job.player_b = candidate
        job.player_w = self.players[self.opponent]
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = self.use_internal_scorer
        job.preferred_scorers = self.preferred_scorers
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        assert not self.finished
        winner = response.game_result.winning_player
        # Counting no-result as loss for the candidate
        if self.is_candidate_code(winner):
            candidate_number = self.candidate_numbers_by_code[winner]
            self.wins[candidate_number] += 1
        self.results_seen_count += 1
        if self.results_seen_count == self.results_required_count:
            assert self.round == BATCH_SIZE
            self.finish_generation()
            self.generation += 1
            if self.generation == NUMBER_OF_GENERATIONS:
                self.finished = True
            else:
                self.reset_for_new_generation()

    def write_static_description(self, out):
        def p(s):
            print >>out, s
        p("tuning event: %s" % self.competition_code)
        p(self.description)
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)
        # FIXME: Should describe the matchups?

    def write_status_summary(self, out):
        if self.round == BATCH_SIZE:
            print >>out, "generation %d: waiting for completion" % (
                self.generation)
        else:
            print >>out, "generation %d: next candidate round %d #%d" % (
                self.generation, self.round, self.next_candidate)
        print >>out
        print >>out, "wins from current samples:\n%s" % self.wins
        print >>out
        if self.generation == NUMBER_OF_GENERATIONS:
            print >>out, "final distribution:"
        else:
            print >>out, "distribution for generation %d:" % self.generation
        print >>out, self.format_distribution(self.distribution)

    def write_results_report(self, out):
        pass
