"""Competitions for parameter tuning using Monte-carlo tree search."""

from __future__ import division

import random
from math import log, sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError,
    Player_config, game_jobs_player_from_config)


# Implementing three-branching tree.

INITIAL_VISITS          =     10
INITIAL_WINS            =     5
INITIAL_VALUE           =     0.5
EXPLORATION_COEFFICIENT =     0.5
_INITIAL_RSQRT_VISITS   =     1.0 / sqrt(INITIAL_VISITS)
BRANCHING_FACTOR        =     3

class Node(object):
    """A MCTS node.

    Public attributes:
      children     -- list of Nodes, or None for unexpanded
      wins
      visits
      value        -- wins / visits

    """
    def __init__(self):
        self.children = None
        self.wins = INITIAL_WINS
        self.visits = INITIAL_VISITS
        self.value = INITIAL_VALUE
        self.rsqrt_visits = _INITIAL_RSQRT_VISITS

    __slots__ = (
        'children',
        'wins',
        'visits',
        'value',
        'rsqrt_visits',
        )

class Tree(object):
    """Run monte-carlo tree search over parameter space.

    """
    def __init__(self):
        self.node_count = 1 # FIXME: For description
        self.root = Node()
        self.expand(self.root)

    def expand(self, node):
        assert node.children is None
        # FIXME: Refuse to expand if too fine.
        node.children = [Node() for _ in xrange(BRANCHING_FACTOR)]
        self.node_count += BRANCHING_FACTOR

    def choose_action(self, node):
        assert node.children is not None
        child_count = len(node.children)
        uct_numerator = EXPLORATION_COEFFICIENT * sqrt(log(node.visits))
        start = random.randrange(child_count)
        best_urgency = -1.0
        best_choice = None
        best_child = None
        for i in range(start, child_count) + range(start):
            child = node.children[i]
            uct_term = uct_numerator * child.rsqrt_visits
            urgency = child.value + uct_term
            if urgency > best_urgency:
                best_urgency = urgency
                best_choice = i
                best_child = child
        return best_choice, best_child

    def retrieve_best_parameters(self):
        lo = 0.0
        breadth = 1.0
        node = self.root
        while node.children is not None:
            best = None
            best_choice = None
            best_value = -1
            for i, child in enumerate(node.children):
                if child.value > best_value:
                    best_value = child.value
                    best = child
                    best_choice = i
            breadth /= BRANCHING_FACTOR
            lo += breadth * best_choice
            node = best
        return [lo + 0.5*breadth]

    def describe(self):
        root = self.root
        wins = root.wins - INITIAL_WINS
        visits = root.visits - INITIAL_VISITS
        try:
            win_rate = "%.2f" % (wins/visits)
        except ZeroDivisionError:
            win_rate = "--"
        node_stats = []
        for choice, node in enumerate(self.root.children):
            node_stats.append(
                "  %d %.2f %3d" %
                (choice, node.value, node.visits - INITIAL_VISITS))
        return "\n".join([
            "%d nodes" % self.node_count,
            "Win rate %d/%d = %s" % (wins, visits, win_rate)
            ] + node_stats)

class Walker(object):
    """FIXME"""
    def __init__(self, tree):
        self.tree = tree
        self.node_path = []
        self.parameter_min = 0.0
        self.parameter_breadth = 1.0
        self.debug = []

    def get_parameter(self):
        return self.parameter_min + .5*self.parameter_breadth

    def step(self, choice, node):
        self.parameter_breadth /= BRANCHING_FACTOR
        self.parameter_min += self.parameter_breadth * choice
        self.node_path.append(node)
        self.debug.append("%s %s" % (choice, self.get_parameter()))

    def walk(self):
        node = self.tree.root
        while node.children is not None:
            choice, node = self.tree.choose_action(node)
            self.step(choice, node)
        if node.visits != INITIAL_VISITS:
            # FIXME: Cope with terminal node
            self.tree.expand(node)
            choice, child = self.tree.choose_action(node)
            self.step(choice, child)

    def update_stats(self, candidate_won):
        for node in self.node_path:
            node.visits += 1
            node.rsqrt_visits = sqrt(1/node.visits)
            if candidate_won:
                node.wins += 1
            node.value = node.wins / node.visits
        self.tree.root.visits += 1
        if candidate_won:
            self.tree.root.wins += 1 # For description
        self.tree.root.rsqrt_visits = sqrt(1/self.tree.root.visits)



class Mcts_tuner(Competition):
    """A Competition for parameter tuning using the Monte-carlo tree search."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)
        # Ought to validate.
        self.number_of_games = config.get('number_of_games')

        try:
            self.translate_parameters_fn = \
                config['convert_optimiser_parameters_to_engine_parameters']
            self.format_parameters_fn = config['format_parameters']
            self.candidate_maker_fn = config['make_candidate']
            opponent = config['opponent']
            if opponent not in self.players:
                raise ValueError("unknown player %s" % opponent)
            self.opponent = self.players[opponent]
        except KeyError, e:
            raise ValueError("%s not specified" % e)
        self.candidate_colour = config['candidate_colour']
        if self.candidate_colour not in ('b', 'w'):
            raise ValueError("invalid candidate_colour: %r" %
                             self.candidate_colour)

    def format_parameters(self, engine_params):
        try:
            return self.format_parameters_fn(engine_params)
        except StandardError:
            return ("[error from user-defined parameter formatter]\n"
                    "[engine parameters %s]" % engine_params)

    def make_candidate(self, optimiser_parameters):
        """FIXME

        Returns a game_jobs.Player with all required attributes set except
        'code'.

        """
        try:
            engine_parameters = \
                self.translate_parameters_fn(optimiser_parameters)
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
        return candidate

    def prepare_simulation(self):
        """FIXME

        Returns a pair (walker, optimiser parameter vector)

        """
        walker = Walker(self.tree)
        walker.walk()
        return walker, [walker.get_parameter()]

    def get_status(self):
        return {}

    def set_status(self, status):
        FIXME

    def set_clean_status(self):
        self.next_game_number = 0
        self.games_played = 0
        self.outstanding_simulations = {}
        self.tree = Tree()
        # FIXME
        self.last_simulation = None
        self.won_last_game = False

    def get_game(self):
        game_number = self.next_game_number
        self.next_game_number += 1
        if (self.number_of_games is not None and
            game_number >= self.number_of_games):
            return NoGameAvailable
        game_id = str(game_number)

        simulation, optimiser_parameters = self.prepare_simulation()
        candidate = self.make_candidate(optimiser_parameters)
        candidate.code = "#" + game_id
        self.outstanding_simulations[game_id] = simulation

        job = game_jobs.Game_job()
        job.game_id = game_id
        if self.candidate_colour == 'b':
            job.player_b = candidate
            job.player_w = self.opponent
        else:
            job.player_b = self.opponent
            job.player_w = candidate
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = self.use_internal_scorer
        job.preferred_scorers = self.preferred_scorers
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        # Counting no-result as loss for the candidate
        candidate_won = (
            response.game_result.winning_colour == self.candidate_colour)
        simulation = self.outstanding_simulations.pop(response.game_id)
        simulation.update_stats(candidate_won)
        self.games_played += 1
        # FIXME: This will do for now for status
        self.last_simulation = simulation
        self.won_last_game = candidate_won

    def write_static_description(self, out):
        def p(s):
            print >>out, s
        p("MCTS tuning event: %s" % self.competition_code)
        p(self.description)
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)
        # FIXME: Should describe the matchup?

    def write_status_summary(self, out):
        if self.number_of_games is None:
            print >>out, "%d games played" % self.games_played
        else:
            print >>out, "%d/%d games played" % (
                self.games_played, self.number_of_games)
        print >>out
        # FIXME: Describe current tree state and winner, I suppose.
        # FIXME: Count nodes in tree.
        if self.last_simulation is not None:
            optimiser_parameters = [self.last_simulation.get_parameter()]
            engine_parameters = \
                self.translate_parameters_fn(optimiser_parameters)
            params_s = self.format_parameters(engine_parameters)
            won_s = ("lost", "won")[self.won_last_game]
            print >>out, "Last simulation: %s %s" % (params_s, won_s)
            print >>out, self.last_simulation.debug
        print >>out, self.tree.describe()
        print >>out, "Best parameter vector: %s" % (
            self.format_parameters(self.tree.retrieve_best_parameters()))
        #waitforkey = raw_input()

    def write_results_report(self, out):
        pass
