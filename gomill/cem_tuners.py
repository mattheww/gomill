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

    def format(self):
        return " ".join("%5.2f~%4.2f" % (mean, stddev)
                        for (mean, stddev) in self.parameters)

    def __str__(self):
        return "<distribution %s>" % self.format()

def format_parameters(parameters):
    return " ".join("%5.2f" % v for v in parameters)

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



# FIXME
old_kiai_gtp_translations = {
    'gomill-describe_engine' : 'kiai-describe_engine',
    'gomill-cpu_time' : 'kiai-cpu_time',
    'gomill-explain_last_move' : 'kiai-explain_last_move',
    }

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
        self.candidate_base = config['candidate_base']
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
        # FIXME: Ringmaster should call this
        self.set_clean_status()

    def translate_parameters(self, optimiser_params):
        """Translate an optimiser parameter vector to an engine one."""
        # The dimensions are resign_at and log_10 (playouts_per_move)
        opt_resign_at, opt_playouts_per_move = optimiser_params
        resign_at = max(0.0, min(1.0, opt_resign_at))
        playouts_per_move = int(10**opt_playouts_per_move)
        playouts_per_move = max(10, min(3000, playouts_per_move))
        return [resign_at, playouts_per_move]

    def make_candidate_command(self, parameters):
        """Return the command for use for a candidate with the given parameters.

        parameters -- engine parameter vector

        Returns a command suitable for use with a Game_job.

        """
        resign_at, playouts_per_move = parameters
        opts = ["--ppm=%d" % playouts_per_move,
                "--resign-at=%f" % resign_at]
        return self.candidate_base.cmd_args + opts

    @staticmethod
    def make_candidate_code(generation, candidate_number):
        return "g%d#%d" % (generation, candidate_number)

    @staticmethod
    def is_candidate_code(player_code):
        return '#' in player_code

    def get_status(self):
        return {}

    def set_status(self, status):
        FIXME

    def reset_for_new_generation(self):
        get_sample = self.distribution.get_sample
        self.sample_parameters = [get_sample()
                                  for _ in xrange(SAMPLES_PER_GENERATION)]
        assert len(self.sample_parameters) == SAMPLES_PER_GENERATION
        # List of pairs (player code, cmd_args),
        # to be indexed by candidate number
        self.candidates = []
        self.candidate_numbers_by_code = {}
        for candidate_number, optimiser_params in \
                enumerate(self.sample_parameters):
            candidate_code = self.make_candidate_code(
                self.generation, candidate_number)
            cmd_args = self.make_candidate_command(
                self.translate_parameters(optimiser_params))
            self.candidates.append((candidate_code, cmd_args))
            self.candidate_numbers_by_code[candidate_code] = candidate_number
        self.round = 0
        self.next_candidate = 0
        self.wins = [0] * SAMPLES_PER_GENERATION
        self.results_required_count = BATCH_SIZE * SAMPLES_PER_GENERATION
        self.results_seen_count = 0

    def finish_generation(self):
        sorter = [(wins, index)
                  for (index, wins) in enumerate(self.wins)]
        sorter.sort(reverse=True)
        elite_count = max(1,
            int(ELITE_PROPORTION * SAMPLES_PER_GENERATION + 0.5))

        for i, (wins, index) in enumerate(sorter):
            self.log("%s%d %s" %
                     ("*" if i < elite_count else " ", wins,
                      format_parameters(self.sample_parameters[index])))

        elite_samples = [self.sample_parameters[index]
                         for (wins, index) in sorter[:elite_count]]
        self.distribution = update_distribution(
            self.distribution, elite_samples)

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

        player_code, candidate_cmd_args = self.candidates[self.next_candidate]
        game_id = "%sr%d" % (player_code, self.round)

        self.next_candidate += 1
        if self.next_candidate == SAMPLES_PER_GENERATION:
            self.next_candidate = 0
            self.round += 1

        commands = {'b' : candidate_cmd_args,
                    'w' : self.players[self.opponent].cmd_args}
        gtp_translations = {'b' : old_kiai_gtp_translations, # FIXME
                            'w' : self.players[self.opponent].gtp_translations}
        players = {'b' : player_code, 'w' : self.opponent}

        job = game_jobs.Game_job()
        job.game_id = game_id
        job.players = players
        job.commands = commands
        job.gtp_translations = gtp_translations
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = self.use_internal_scorer
        job.preferred_scorers = self.preferred_scorers
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        winner = response.game_result.winning_player
        # Counting no-result as loss for the candidate
        if self.is_candidate_code(winner):
            candidate_number = self.candidate_numbers_by_code[winner]
            self.wins[candidate_number] += 1
        self.results_seen_count += 1
        if self.results_seen_count == self.results_required_count:
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
        print >>out, self.wins
        print >>out, self.distribution

    def write_results_report(self, out):
        pass
