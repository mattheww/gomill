"""Competitions for parameter tuning using the cross-entropy method."""

from __future__ import division

from random import gauss as random_gauss
from math import sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import competitions
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError,
    Player_config, game_jobs_player_from_config)
from gomill.settings import *


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

def update_distribution(distribution, elites, step_size):
    """Update a distribution based on the given elites.

    distribution -- Distribution
    elites       -- list of optimiser parameter vectors
    step_size    -- float between 0.0 and 1.0 ('alpha')

    Returns a new distribution

    """
    n = len(elites)
    new_distribution_parameters = []
    for i in range(distribution.dimension):
        v = [e[i] for e in elites]
        elite_mean = sum(v) / n
        elite_var = sum(map(square, v)) / n - square(elite_mean)
        old_mean, old_var = distribution.parameters[i]
        new_mean = (elite_mean * step_size +
                    old_mean * (1.0 - step_size))
        new_var = (elite_var * step_size +
                   old_var * (1.0 - step_size))
        new_distribution_parameters.append((new_mean, new_var))
    return Distribution(new_distribution_parameters)


class Cem_tuner(Competition):
    """A Competition for parameter tuning using the cross-entropy method."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)

    global_settings = [
        Setting('komi', interpret_float),
        Setting('board_size', competitions.interpret_board_size),
        Setting('move_limit', interpret_int, default=1000),
        Setting('description', interpret_as_utf8, default=""),
        Setting('scorer', interpret_enum('internal', 'players'),
                default='players'),
        ]

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)
        try:
            self.batch_size = config['batch_size']
            self.samples_per_generation = config['samples_per_generation']
            self.number_of_generations = config['number_of_generations']
            self.elite_proportion = config['elite_proportion']
            self.step_size = config['step_size']
            self.initial_distribution = Distribution(
                config['initial_distribution'])
            self.translate_parameters_fn = \
                config['convert_optimiser_parameters_to_engine_parameters']
            self.format_parameters_fn = config['format_parameters']
            self.candidate_maker_fn = config['make_candidate']
            # FIXME: Proper CANDIDATE object or something.
            self.matchups = config['matchups']
            for p1, p2 in self.matchups:
                if p1 == "CANDIDATE":
                    other = p2
                elif p2 == "CANDIDATE":
                    other = p1
                else:
                    raise ValueError("matchup without CANDIDATE")
                if other not in self.players:
                    raise ValueError("unknown player %s" % other)
            # FIXME: Later sort out rotating through; for now just use last
            # matchup but have candidate always take black
            self.opponent = other
        except KeyError, e:
            raise ValueError("%s not specified" % e)

    def format_parameters(self, optimiser_parameters):
        try:
            return self.format_parameters_fn(optimiser_parameters)
        except StandardError:
            return ("[error from user-defined parameter formatter]\n"
                    "[optimiser parameters %s]" % optimiser_parameters)

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

    def prepare_candidates(self):
        """Set up the candidates array.

        This is run for each new generation, and when reloading state.

        Requires generation and sample_parameters to be already set.

        """
        # List of Players to be indexed by candidate number
        self.candidates = []
        self.candidate_numbers_by_code = {}
        for candidate_number, optimiser_params in \
                enumerate(self.sample_parameters):
            candidate_code = self.make_candidate_code(
                self.generation, candidate_number)
            try:
                engine_parameters = \
                    self.translate_parameters_fn(optimiser_params)
            except StandardError:
                raise CompetitionError(
                    "error from user-defined parameter converter\n%s" %
                    compact_tracebacks.format_traceback(skip=1))
            try:
                candidate_config = self.candidate_maker_fn(engine_parameters)
            except StandardError:
                raise CompetitionError(
                    "error from user-defined candidate function\n%s" %
                    compact_tracebacks.format_traceback(skip=1))
            if not isinstance(candidate_config, Player_config):
                raise CompetitionError(
                    "user-defined candidate function returned %r, not Player" %
                    candidate_config)
            try:
                candidate = game_jobs_player_from_config(candidate_config)
            except ValueError, e:
                raise CompetitionError(
                    "error making candidate player\nparameters: %s\nerror: %s" %
                    (self.format_parameters(optimiser_params), e))
            candidate.code = candidate_code
            self.candidates.append(candidate)
            self.candidate_numbers_by_code[candidate_code] = candidate_number

    def reset_for_new_generation(self):
        get_sample = self.distribution.get_sample
        self.sample_parameters = [get_sample()
                                  for _ in xrange(self.samples_per_generation)]
        assert len(self.sample_parameters) == self.samples_per_generation
        self.round = 0
        self.next_candidate = 0
        self.wins = [0] * self.samples_per_generation
        self.results_seen_count = 0
        self.prepare_candidates()

    def get_results_required_count(self):
        return self.batch_size * self.samples_per_generation

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
            int(self.elite_proportion * self.samples_per_generation + 0.5))
        self.log_history("Generation %s" % self.generation)
        self.log_history("Distribution\n%s" %
                         self.format_distribution(self.distribution))
        self.log_history(self.format_generation_results(sorter, elite_count))
        self.log_history("")
        elite_samples = [self.sample_parameters[index]
                         for (wins, index) in sorter[:elite_count]]
        self.distribution = update_distribution(
            self.distribution, elite_samples, self.step_size)

    def get_status(self):
        return {
            'finished'           : self.finished,
            'distribution'       : self.distribution.parameters,
            'sample_parameters'  : self.sample_parameters,
            'generation'         : self.generation,
            'round'              : self.round,
            'next_candidate'     : self.next_candidate,
            'wins'               : self.wins,
            'results_seen_count' : self.results_seen_count,
            }

    def set_status(self, status):
        self.finished = status['finished']
        self.distribution = Distribution(status['distribution'])
        self.sample_parameters = status['sample_parameters']
        self.generation = status['generation']
        self.round = status['round']
        self.next_candidate = status['next_candidate']
        self.wins = status['wins']
        self.results_seen_count = status['results_seen_count']
        self.prepare_candidates()

    def set_clean_status(self):
        self.finished = False
        self.generation = 0
        self.distribution = self.initial_distribution
        self.reset_for_new_generation()

    def get_game(self):
        if self.finished:
            return NoGameAvailable

        if self.round == self.batch_size:
            # Send no more games until the new generation
            return NoGameAvailable

        if self.round == 0 and self.next_candidate == 0:
            self.log("\nstarting generation %d" % self.generation)

        candidate = self.candidates[self.next_candidate]
        game_id = "%sr%d" % (candidate.code, self.round)

        self.next_candidate += 1
        if self.next_candidate == self.samples_per_generation:
            self.next_candidate = 0
            self.round += 1

        job = game_jobs.Game_job()
        job.game_id = game_id
        job.player_b = candidate
        job.player_w = self.players[self.opponent]
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = (self.scorer == 'internal')
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
        if self.results_seen_count == self.get_results_required_count():
            assert self.round == self.batch_size
            self.finish_generation()
            self.generation += 1
            if self.generation == self.number_of_generations:
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
        if self.round == self.batch_size:
            print >>out, "generation %d: waiting for completion" % (
                self.generation)
        else:
            print >>out, "generation %d: next candidate round %d #%d" % (
                self.generation, self.round, self.next_candidate)
        print >>out
        print >>out, "wins from current samples:\n%s" % self.wins
        print >>out
        if self.generation == self.number_of_generations:
            print >>out, "final distribution:"
        else:
            print >>out, "distribution for generation %d:" % self.generation
        print >>out, self.format_distribution(self.distribution)

    def write_results_report(self, out):
        pass
