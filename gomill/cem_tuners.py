"""Competitions for parameter tuning using the cross-entropy method."""

from __future__ import division

from random import gauss as random_gauss
from math import sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import competitions
from gomill import competition_schedulers
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError,
    Player_config)
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
        if self.dimension == 0:
            raise ValueError
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
    """A Competition for parameter tuning using the cross-entropy method.

    The game ids are like 'g0#1r3', where 0 is the generation number, 1 is the
    candidate number and 3 is the round number.

    """
    def __init__(self, competition_code, **kwargs):
        Competition.__init__(self, competition_code, **kwargs)
        self.seen_successful_game = False

    global_settings = [
        Setting('board_size', competitions.interpret_board_size),
        Setting('komi', interpret_float),
        Setting('handicap', allow_none(interpret_int), default=None),
        Setting('handicap_style', interpret_enum('fixed', 'free'),
                default='fixed'),
        Setting('move_limit', interpret_positive_int, default=1000),
        Setting('description', interpret_as_utf8, default=""),
        Setting('scorer', interpret_enum('internal', 'players'),
                default='players'),
        Setting('batch_size', interpret_positive_int),
        Setting('samples_per_generation', interpret_positive_int),
        Setting('number_of_generations', interpret_positive_int),
        Setting('elite_proportion', interpret_float),
        Setting('step_size', interpret_float),
        ]

    special_settings = [
        Setting('opponent', interpret_any),
        Setting('initial_distribution', interpret_any),
        Setting('convert_optimiser_parameters_to_engine_parameters',
                interpret_callable),
        Setting('format_parameters', interpret_callable),
        Setting('make_candidate', interpret_callable),
        ]

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        competitions.validate_handicap(
            self.handicap, self.handicap_style, self.board_size)

        if not 0.0 < self.elite_proportion < 1.0:
            raise ControlFileError("elite_proportion out of range (0.0 to 1.0)")
        if not 0.0 < self.step_size < 1.0:
            raise ControlFileError("step_size out of range (0.0 to 1.0)")

        try:
            specials = load_settings(self.special_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        try:
            self.initial_distribution = Distribution(
                specials['initial_distribution'])
        except StandardError:
            raise ControlFileError("initial_distribution: invalid")

        try:
            self.opponent = self.players[specials['opponent']]
        except KeyError:
            raise ControlFileError(
                "opponent: unknown player %s" % specials['opponent'])

        self.translate_parameters_fn = \
            specials['convert_optimiser_parameters_to_engine_parameters']
        self.format_parameters_fn = specials['format_parameters']
        self.candidate_maker_fn = specials['make_candidate']


    # State attributes (*: in persistent state):
    #  *generation        -- current generation (0-based int)
    #  *distribution      -- Distribution for current generation
    #  *sample_parameters -- optimiser_params
    #                        (list indexed by candidate number)
    #  *wins              -- number of games won
    #                        (list indexed by candidate number)
    #   candidates        -- Players (code attribute is the candidate code)
    #                        (list indexed by candidate number)
    #  *scheduler         -- Group_scheduler (group codes are candidate numbers)
    #
    # These are all reset for each new generation.
    #
    #   seen_successful_game -- bool (per-run state)

    def set_clean_status(self):
        self.generation = 0
        self.distribution = self.initial_distribution
        self.reset_for_new_generation()

    def _set_scheduler_groups(self):
        self.scheduler.set_groups(
            (i, self.batch_size) for i in xrange(self.samples_per_generation)
            )

    def get_status(self):
        return {
            'generation'         : self.generation,
            'distribution'       : self.distribution.parameters,
            'sample_parameters'  : self.sample_parameters,
            'wins'               : self.wins,
            'scheduler'          : self.scheduler,
            }

    def set_status(self, status):
        self.generation = status['generation']
        self.distribution = Distribution(status['distribution'])
        self.sample_parameters = status['sample_parameters']
        self.wins = status['wins']
        self.prepare_candidates()
        self.scheduler = status['scheduler']
        # Might as well notice if they changed the batch_size
        self._set_scheduler_groups()
        self.scheduler.rollback()

    def reset_for_new_generation(self):
        get_sample = self.distribution.get_sample
        self.sample_parameters = [get_sample()
                                  for _ in xrange(self.samples_per_generation)]
        self.wins = [0] * self.samples_per_generation
        self.prepare_candidates()
        self.scheduler = competition_schedulers.Group_scheduler()
        self._set_scheduler_groups()

    @staticmethod
    def make_candidate_code(generation, candidate_number):
        return "g%d#%d" % (generation, candidate_number)

    def prepare_candidates(self):
        """Set up the candidates array.

        This is run for each new generation, and when reloading state.

        Requires generation and sample_parameters to be already set.

        Initialises self.candidates.

        """
        self.candidates = []
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
                candidate = self.game_jobs_player_from_config(
                    candidate_code, candidate_config)
            except StandardError, e:
                raise CompetitionError(
                    "error making candidate player\nparameters: %s\nerror: %s" %
                    (self.format_parameters(optimiser_params), e))
            self.candidates.append(candidate)

    def finish_generation(self):
        """Process a generation's results and calculate the new distribution.

        Writes a description of the generation to the history log.

        Updates self.distribution.

        """
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

    def get_game(self):
        if self.scheduler.nothing_issued_yet():
            self.log_event("\nstarting generation %d" % self.generation)

        candidate_number, round_id = self.scheduler.issue()
        if candidate_number is None:
            return NoGameAvailable

        candidate = self.candidates[candidate_number]

        job = game_jobs.Game_job()
        job.game_id = "%sr%d" % (candidate.code, round_id)
        job.game_data = (candidate_number, candidate.code, round_id)
        job.player_b = candidate
        job.player_w = self.opponent
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.handicap = self.handicap
        job.handicap_is_free = (self.handicap_style == 'free')
        job.use_internal_scorer = (self.scorer == 'internal')
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        self.seen_successful_game = True
        candidate_number, candidate_code, round_id = response.game_data
        self.scheduler.fix(candidate_number, round_id)
        gr = response.game_result
        assert candidate_code in (gr.player_b, gr.player_w)

        # Counting no-result as loss for the candidate
        if gr.winning_player == candidate_code:
            self.wins[candidate_number] += 1

        if self.scheduler.all_fixed():
            self.finish_generation()
            self.generation += 1
            if self.generation != self.number_of_generations:
                self.reset_for_new_generation()

    def process_game_error(self, job, previous_error_count):
        ## If the very first game gives an error, halt.
        ## Otherwise, retry once and halt on a second failure.
        if (not self.seen_successful_game) or (previous_error_count > 0):
            # Stop the tournament
            return True, False
        # Retry the game
        return False, True


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

    def write_static_description(self, out):
        def p(s):
            print >>out, s
        p("CEM tuning event: %s" % self.competition_code)
        p(self.description)
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)

    def write_screen_report(self, out):
        print >>out, "generation %d" % self.generation
        print >>out
        print >>out, "wins from current samples:\n%s" % self.wins
        print >>out
        if self.generation == self.number_of_generations:
            print >>out, "final distribution:"
        else:
            print >>out, "distribution for generation %d:" % self.generation
        print >>out, self.format_distribution(self.distribution)

    def write_short_report(self, out):
        self.write_static_description(out)
        self.write_screen_report(out)

    write_full_report = write_short_report

