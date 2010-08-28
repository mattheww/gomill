"""Competitions for parameter tuning using Monte-carlo tree search."""

from __future__ import division

import cPickle as pickle
import random
from math import log, sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import competitions
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError,
    Player_config, game_jobs_player_from_config)
from gomill.settings import *


class Node(object):
    """A MCTS node.

    Public attributes:
      children     -- list of Nodes, or None for unexpanded
      wins
      visits
      value        -- wins / visits

    """
    def count_tree_size(self):
        if self.children is None:
            return 1
        return sum(child.count_tree_size() for child in self.children) + 1

    def __getstate__(self):
        return (self.children, self.wins, self.visits)

    def __setstate__(self, state):
        self.children, self.wins, self.visits = state
        self.value = self.wins / self.visits
        self.rsqrt_visits = sqrt(1/self.visits)

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
    def __init__(self, dimensions, branching_factor, max_depth,
                 exploration_coefficient,
                 initial_visits, initial_wins,
                 parameter_formatter):
        self.dimensions = dimensions
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.exploration_coefficient = exploration_coefficient
        self.initial_visits = initial_visits
        self.initial_wins = initial_wins
        self.initial_rsqrt_visits = 1/sqrt(initial_visits)
        self.format_parameters = parameter_formatter

    def new_root(self):
        self.node_count = 1 # For description only
        self.root = Node()
        self.root.children = None
        self.root.wins = self.initial_wins
        self.root.visits = self.initial_visits
        self.root.value = self.initial_wins / self.initial_visits
        self.root.rsqrt_visits = self.initial_rsqrt_visits
        self.expand(self.root)

    def set_root(self, node):
        self.root = node
        self.node_count = node.count_tree_size()

    def cube_pos_from_child_number(self, child_number):
        """Work out the position of a given child in a child cube.

        Returns a list of length 'dimensions' with values in
        range('branching_factor').

        """
        result = []
        i = child_number
        for d in range(self.dimensions):
            i, r = divmod(i, self.branching_factor)
            result.append(r)
        return result

    def expand(self, node):
        assert node.children is None
        node.children = []
        child_count = self.branching_factor ** self.dimensions
        for _ in xrange(child_count):
            child = Node()
            child.children = None
            child.wins = self.initial_wins
            child.visits = self.initial_visits
            child.value = self.initial_wins / self.initial_visits
            child.rsqrt_visits = self.initial_rsqrt_visits
            node.children.append(child)
        self.node_count += child_count

    def choose_action(self, node):
        assert node.children is not None
        child_count = len(node.children)
        uct_numerator = self.exploration_coefficient * sqrt(log(node.visits))
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
        lo = [0.0] * self.dimensions
        breadth = 1.0
        node = self.root
        while node.children is not None:
            best = None
            best_choice = None
            best_wins = -1
            for i, child in enumerate(node.children):
                if child.wins > best_wins:
                    best_wins = child.wins
                    best = child
                    best_choice = i
            breadth /= self.branching_factor
            cube_pos = self.cube_pos_from_child_number(best_choice)
            for d in range(self.dimensions):
                lo[d] += breadth * cube_pos[d]
            node = best
        return [lo[d] + 0.5*breadth for d in range(self.dimensions)]

    def describe(self):
        def describe_node(cube_pos, lo_param, node):
            parameters = self.format_parameters(lo_param) + "+"
            return "%s %s %.3f %3d" % (
                cube_pos, parameters, node.value,
                node.visits - self.initial_visits)

        root = self.root
        wins = root.wins - self.initial_wins
        visits = root.visits - self.initial_visits
        try:
            win_rate = "%.3f" % (wins/visits)
        except ZeroDivisionError:
            win_rate = "--"
        result = [
            "%d nodes" % self.node_count,
            "Win rate %d/%d = %s" % (wins, visits, win_rate)
            ]
        lo = [0.0] * self.dimensions
        breadth = 1.0
        for choice, node in enumerate(self.root.children):
            breadth2 = breadth / self.branching_factor
            cube_pos = self.cube_pos_from_child_number(choice)
            lo2 = [lo[d] + breadth2 * cube_pos[d]
                   for d in range(self.dimensions)]
            result.append("  " + describe_node(cube_pos, lo2, node))
            if node.children is None:
                continue
            for choice2, node2 in enumerate(node.children):
                breadth3 = breadth2 / self.branching_factor
                cube_pos2 = self.cube_pos_from_child_number(choice2)
                lo3 = [lo2[d] + breadth3 * cube_pos2[d]
                       for d in range(self.dimensions)]
                result.append("    " + describe_node(cube_pos2, lo3, node2))
        return "\n".join(result)


class Simulation(object):
    """FIXME"""
    def __init__(self, tree):
        self.tree = tree
        self.node_path = []
        self.choice_path = [] # For description only
        self.parameter_min = [0.0] * tree.dimensions
        self.parameter_breadth = 1.0
        self.debug = []

    def get_parameters(self):
        return [self.parameter_min[d] + .5*self.parameter_breadth
                for d in range(self.tree.dimensions)]

    def describe_steps(self):
        return " ".join(map(str, self.choice_path))

    def step(self, choice, node):
        cube_pos = self.tree.cube_pos_from_child_number(choice)
        self.parameter_breadth /= self.tree.branching_factor
        for d in range(self.tree.dimensions):
            self.parameter_min[d] += self.parameter_breadth * cube_pos[d]
        self.node_path.append(node)
        self.choice_path.append(choice)

    def walk(self):
        node = self.tree.root
        while node.children is not None:
            choice, node = self.tree.choose_action(node)
            self.step(choice, node)
        if (node.visits != self.tree.initial_visits and
            len(self.node_path) < self.tree.max_depth):
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
            self.tree.root.wins += 1 # For description only
        self.tree.root.rsqrt_visits = sqrt(1/self.tree.root.visits)

    def describe(self, candidate_won):
        optimiser_parameters = self.get_parameters()
        params_s = self.tree.format_parameters(optimiser_parameters)
        won_s = ("lost", "won")[candidate_won]
        return "%s [%s] %s" % (params_s, self.describe_steps(), won_s)

    def __getstate__(self):
        # We don't want to pickle the tree object (and it's unpicklable, anyway)
        result = self.__dict__.copy()
        del result['tree']
        return result

    def __setstate__(self, state):
        # Leaves tree unset; unpickler has to restore it
        self.__dict__ = state


class Mcts_tuner(Competition):
    """A Competition for parameter tuning using the Monte-carlo tree search."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)
        # These are only for the sake of display
        self.last_simulation = None
        self.won_last_game = False

    global_settings = [
        Setting('board_size', competitions.interpret_board_size),
        Setting('komi', interpret_float),
        Setting('handicap', allow_none(interpret_int), default=None),
        Setting('handicap_style', interpret_enum('fixed', 'free'),
                default='fixed'),
        Setting('move_limit', interpret_int, default=1000),
        Setting('description', interpret_as_utf8, default=""),
        Setting('scorer', interpret_enum('internal', 'players'),
                default='players'),
        ]

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        competitions.validate_handicap(
            self.handicap, self.handicap_style, self.board_size)

        # Ought to validate properly
        dimensions = config['dimensions']
        branching_factor = config['branching_factor']
        max_depth = config['max_depth']
        exploration_coefficient = config['exploration_coefficient']
        initial_visits = config['initial_visits']
        initial_wins = config['initial_wins']
        self.number_of_games = config.get('number_of_games')
        try:
            self.log_after_games = config['log_after_games']
        except KeyError:
            self.log_after_games = 8

        try:
            self.translate_parameters_fn = \
                config['convert_optimiser_parameters_to_engine_parameters']
            self.format_parameters_fn = config['format_parameters']
            self.candidate_maker_fn = config['make_candidate']
            opponent = config['opponent']
            if opponent not in self.players:
                raise ControlFileError("unknown player %s" % opponent)
            self.opponent = self.players[opponent]
        except KeyError, e:
            raise ControlFileError("%s not specified" % e)
        self.candidate_colour = config['candidate_colour']
        if self.candidate_colour not in ('b', 'w'):
            raise ControlFileError("invalid candidate_colour: %r" %
                                   self.candidate_colour)

        self.tree = Tree(dimensions, branching_factor, max_depth,
                         exploration_coefficient,
                         initial_visits, initial_wins,
                         self.format_parameters)

    def format_parameters(self, optimiser_parameters):
        try:
            return self.format_parameters_fn(optimiser_parameters)
        except StandardError:
            return ("[error from user-defined parameter formatter]\n"
                    "[optimiser parameters %s]" % optimiser_parameters)

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
        except StandardError, e:
            raise CompetitionError(
                "error making candidate player\nparameters: %s\nerror: %s" %
                (self.format_parameters(optimiser_parameters), e))
        return candidate

    def prepare_simulation(self):
        """FIXME

        Returns a pair (simulation, optimiser parameter vector)

        """
        simulation = Simulation(self.tree)
        simulation.walk()
        return simulation, simulation.get_parameters()

    def get_status(self):
        return {
            'next_game_number' : self.next_game_number,
            'games_played'     : self.games_played,
            # Pickling these together so that they share the Node objects
            'tree_data'        : pickle.dumps((self.tree.root,
                                               self.outstanding_simulations))
            }

    def set_status(self, status):
        self.next_game_number = status['next_game_number']
        self.games_played = status['games_played']
        root, outstanding_simulations = pickle.loads(
            status['tree_data'].encode('iso-8859-1'))
        self.tree.set_root(root)
        for simulation in outstanding_simulations.values():
            simulation.tree = self.tree
        self.outstanding_simulations = outstanding_simulations

    def set_clean_status(self):
        self.next_game_number = 0
        self.games_played = 0
        self.tree.new_root()
        self.outstanding_simulations = {}

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
        job.handicap = self.handicap
        job.handicap_is_free = (self.handicap_style == 'free')
        job.use_internal_scorer = (self.scorer == 'internal')
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
        self.log_history(simulation.describe(candidate_won))
        # FIXME: Want to describe this stuff; for now, let status summary do it
        self.last_simulation = simulation
        self.won_last_game = candidate_won
        if self.games_played % self.log_after_games == 0:
            self.log_history(self.tree.describe())

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
        if self.last_simulation is not None:
            print >>out, "Last simulation: %s" % (
                self.last_simulation.describe(self.won_last_game))
        print >>out, self.tree.describe()
        print >>out, "Best parameter vector: %s" % (
            self.format_parameters(self.tree.retrieve_best_parameters()))
        #waitforkey = raw_input()

    def write_results_report(self, out):
        pass
