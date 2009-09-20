"""Competitions for parameter tuning using the cross-entropy method."""

from gomill import cem
from gomill import game_jobs
from gomill.competitions import Competition, NoGameAvailable, Player_config

BATCH_SIZE = 3
SAMPLES_PER_GENERATION = 5

def get_initial_distribution():
    # FIXME
    return cem.Distribution([(10.0, 4.0), (3.0, 4.0), (3.0, 3.0)])


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
        return optimiser_params[:]

    def make_candidate_command(self, parameters):
        """Return the command for use for a candidate with the given parameters.

        parameters -- engine parameter vector

        Returns a command suitable for use with a Game_job.

        """
        args = self.candidate_base.cmd_args
        opts = ["--ppm=100"]
        return args + opts

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
        sample_parameters = self.optimiser.get_sample_parameters()
        assert len(sample_parameters) == SAMPLES_PER_GENERATION
        # List of pairs (player code, cmd_args),
        # to be indexed by candidate number
        self.candidates = []
        self.candidate_numbers_by_code = {}
        for candidate_number, optimiser_params in enumerate(sample_parameters):
            candidate_code = self.make_candidate_code(
                self.generation, candidate_number)
            cmd_args = self.make_candidate_command(
                self.translate_parameters(optimiser_params))
            self.candidates.append((candidate_code, cmd_args))
            self.candidate_numbers_by_code[candidate_code] = candidate_number
        self.round = 0
        self.next_candidate = 0
        self.wins = [0] * SAMPLES_PER_GENERATION

    def set_clean_status(self):
        self.optimiser = cem.Cem_optimiser(
            fitness_fn="FIXME",
            samples_per_generation=SAMPLES_PER_GENERATION,
            elite_proportion=0.1,
            step_size=0.8)
        self.optimiser.set_brief_logger(self.log) # FIXME
        self.optimiser.set_distribution(get_initial_distribution())
        self.generation = 0
        self.reset_for_new_generation()

    def get_game(self):
        if self.round == BATCH_SIZE:
            # Send no more games until the new generation
            return NoGameAvailable

        player_code, candidate_cmd_args = self.candidates[self.next_candidate]
        game_id = "%sr%d" % (player_code, self.round)

        # FIXME: Can use a generator for this bit?
        self.next_candidate += 1
        if self.next_candidate == SAMPLES_PER_GENERATION:
            self.next_candidate = 0
            self.round += 1

        commands = {'b' : candidate_cmd_args,
                    'w' : self.players[self.opponent].cmd_args}
        gtp_translations = {'b' : {}, # FIXME
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

    def write_results_report(self, out):
        pass
