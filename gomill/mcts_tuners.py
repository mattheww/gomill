"""Competitions for parameter tuning using Monte-carlo tree search."""

from __future__ import division

import random
from heapq import nlargest
from math import log, sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill import competitions
from gomill import competition_schedulers
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError,
    Player_config)
from gomill.settings import *


class Node(object):
    """A MCTS node.

    Public attributes:
      children     -- list of Nodes, or None for unexpanded
      wins
      visits
      value        -- wins / visits
      rsqrt_visits -- 1 / sqrt(visits)

    """
    def count_tree_size(self):
        if self.children is None:
            return 1
        return sum(child.count_tree_size() for child in self.children) + 1

    def recalculate(self):
        """Update value and rsqrt_visits from changed wins and visits."""
        self.value = self.wins / self.visits
        self.rsqrt_visits = sqrt(1/self.visits)

    def __getstate__(self):
        return (self.children, self.wins, self.visits)

    def __setstate__(self, state):
        self.children, self.wins, self.visits = state
        self.recalculate()

    __slots__ = (
        'children',
        'wins',
        'visits',
        'value',
        'rsqrt_visits',
        )

    def __repr__(self):
        return "<Node:%.2f{%s}>" % (self.value, repr(self.children))


class Tree(object):
    """A tree of MCTS nodes representing N-dimensional parameter space.

    Parameters (available as read-only attributes):
      dimensions       -- number of dimensions in the parameter space
      subdivisions     -- subdivisions of each dimension at each generation
      max_depth        -- number of generations below the root
      initial_visits   -- visit count for newly-created nodes
      initial_wins     -- win count for newly-created nodes
      exploration_coefficient -- constant for UCT formula (float)

    Public attributes:
      root             -- Node

    All changing state is in the tree of Node objects started at 'root'.

    References to 'optimiser_parameters' below mean a sequence of length
    'dimensions', whose values are floats in the range 0.0..1.0 representing
    a point in this space.

    Each node in the tree represents an N-cube of parameter space. Each
    expanded node has subdivisions**dimension children, tiling its cube.

    Instantiate with:
      all parameters listed above
      parameter_formatter -- function optimiser_parameters -> string

    """
    def __init__(self, dimensions, subdivisions, max_depth,
                 exploration_coefficient,
                 initial_visits, initial_wins,
                 parameter_formatter):
        self.dimensions = dimensions
        self.subdivisions = subdivisions
        self.branching_factor = subdivisions ** dimensions
        self.max_depth = max_depth
        self.exploration_coefficient = exploration_coefficient
        self.initial_visits = initial_visits
        self.initial_wins = initial_wins
        self._initial_value = initial_wins / initial_visits
        self._initial_rsqrt_visits = 1/sqrt(initial_visits)
        self.format_parameters = parameter_formatter

        # map child index -> coordinate vector
        # coordinate vector -- tuple length 'dimensions' with values in
        #                      range(subdivisions)
        self._cube_coordinates = []
        for child_index in xrange(self.branching_factor):
            v = []
            i = child_index
            for d in range(dimensions):
                i, coord = divmod(i, subdivisions)
                v.append(coord)
            v.reverse() # so that first coordinate changes most slowly
            self._cube_coordinates.append(tuple(v))

    def new_root(self):
        """Initialise the tree with an expanded root node."""
        self.node_count = 1 # For description only
        self.root = Node()
        self.root.children = None
        self.root.wins = self.initial_wins
        self.root.visits = self.initial_visits
        self.root.value = self.initial_wins / self.initial_visits
        self.root.rsqrt_visits = self._initial_rsqrt_visits
        self.expand(self.root)

    def set_root(self, node):
        """Use the specified node as the tree's root.

        This is used when restoring serialised state.

        """
        self.root = node
        self.node_count = node.count_tree_size()

    def expand(self, node):
        """Add children to the specified node."""
        assert node.children is None
        node.children = []
        child_count = self.branching_factor
        for _ in xrange(child_count):
            child = Node()
            child.children = None
            child.wins = self.initial_wins
            child.visits = self.initial_visits
            child.value = self._initial_value
            child.rsqrt_visits = self._initial_rsqrt_visits
            node.children.append(child)
        self.node_count += child_count

    def is_ripe(self, node):
        """Say whether a node has been visted enough times to be expanded."""
        return node.visits != self.initial_visits

    def parameters_for_path(self, choice_path):
        """Retrieve the point in parameter space given by a node.

        choice_path -- sequence of child indices

        Returns optimiser_parameters representing the centre of the region
        of parameter space represented by the node of interest.

        choice_path must represent a path from the root to the node of interest.

        """
        lo = [0.0] * self.dimensions
        breadth = 1.0
        for child_index in choice_path:
            cube_pos = self._cube_coordinates[child_index]
            breadth /= self.subdivisions
            for d, coord in enumerate(cube_pos):
                lo[d] += breadth * coord
        return [f + .5*breadth for f in lo]

    def retrieve_best_parameters(self):
        """Find the parameters with the most promising simulation results.

        Returns optimiser_parameters

        This walks the tree from the root, at each point choosing the node with
        most wins, and returns the parameters corresponding to the leaf node.

        """
        simulation = self.retrieve_best_parameter_simulation()
        return simulation.get_parameters()

    def retrieve_best_parameter_simulation(self):
        """Return the Greedy_simulation used for retrieve_best_parameters."""
        simulation = Greedy_simulation(self)
        simulation.walk()
        return simulation

    def get_test_parameters(self):
        """Return a 'typical' optimiser_parameters."""
        return [.5] * self.dimensions

    def describe_choice(self, choice):
        """Return a string describing a child's coordinates in its parent."""
        return str(self._cube_coordinates[choice]).replace(" ", "")

    def describe(self):
        """Return a text description of the current state of the tree.

        This currently dumps the full tree to depth 2.

        """

        def describe_node(node, choice_path):
            parameters = self.format_parameters(
                self.parameters_for_path(choice_path))
            choice_s = self.describe_choice(choice_path[-1])
            return "%s %s %.3f %3d" % (
                choice_s, parameters, node.value,
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

        for choice, node in enumerate(self.root.children):
            result.append("  " + describe_node(node, [choice]))
            if node.children is None:
                continue
            for choice2, node2 in enumerate(node.children):
                result.append("    " + describe_node(node2, [choice, choice2]))
        return "\n".join(result)

    def summarise(self, out, summary_spec):
        """Write a summary of the most-visited parts of the tree.

        out          -- writeable file-like object
        summary_spec -- list of ints

        summary_spec says how many nodes to describe at each depth of the tree
        (so to show only direct children of the root, pass a list of length 1).

        """
        def p(s):
            print >>out, s

        def describe_node(node, choice_path):
            parameters = self.format_parameters(
                self.parameters_for_path(choice_path))
            choice_s = " ".join(map(self.describe_choice, choice_path))
            return "%s %-40s %.3f %3d" % (
                choice_s, parameters, node.value,
                node.visits - self.initial_visits)

        def most_visits((child_index, node)):
            return node.visits

        last_generation = [([], self.root)]
        for i, n in enumerate(summary_spec):
            depth = i + 1
            p("most visited at depth %s" % (depth))

            this_generation = []
            for path, node in last_generation:
                if node.children is not None:
                    this_generation += [
                        (path + [child_index], child)
                        for (child_index, child) in enumerate(node.children)]

            for path, node in sorted(
                nlargest(n, this_generation, key=most_visits)):
                p(describe_node(node, path))
            last_generation = this_generation
            p("")


class Simulation(object):
    """A single monte-carlo simulation.

    Instantiate with the Tree the simulation will run in.

    Use the methods in the following order:
      run()
      get_parameters()
      update_stats(b)
      describe()

    """
    def __init__(self, tree):
        self.tree = tree
        # list of Nodes
        self.node_path = []
        # corresponding list of child indices
        self.choice_path = []
        # bool
        self.candidate_won = None

    def _choose_action(self, node):
        """Choose the best action from the specified node.

        Returns a pair (child index, node)

        """
        uct_numerator = (self.tree.exploration_coefficient *
                         sqrt(log(node.visits)))
        def urgency((i, child)):
            return child.value + uct_numerator * child.rsqrt_visits
        start = random.randrange(len(node.children))
        children = list(enumerate(node.children))
        return max(children[start:] + children[:start], key=urgency)

    def walk(self):
        """Choose a node sequence, without expansion."""
        node = self.tree.root
        while node.children is not None:
            choice, node = self._choose_action(node)
            self.node_path.append(node)
            self.choice_path.append(choice)

    def run(self):
        """Choose the node sequence for this simulation.

        This walks down from the root, using _choose_action() at each level,
        until it reaches a leaf; if the leaf has already been visited, this
        expands it and chooses one more action.

        """
        self.walk()
        node = self.node_path[-1]
        if (len(self.node_path) < self.tree.max_depth and
            self.tree.is_ripe(node)):
            self.tree.expand(node)
            choice, child = self._choose_action(node)
            self.node_path.append(child)
            self.choice_path.append(choice)

    def get_parameters(self):
        """Retrieve the parameters corresponding to the simulation's leaf node.

        Returns optimiser_parameters

        """
        return self.tree.parameters_for_path(self.choice_path)

    def update_stats(self, candidate_won):
        """Update the tree's node statistics with the simulation's results.

        This updates visits (and wins, if appropriate) for each node in the
        simulation's node sequence.

        """
        self.candidate_won = candidate_won
        for node in self.node_path:
            node.visits += 1
            if candidate_won:
                node.wins += 1
            node.recalculate()
        self.tree.root.visits += 1
        if candidate_won:
            self.tree.root.wins += 1 # For description only
        self.tree.root.recalculate()

    def describe_steps(self):
        """Return a text description of the simulation's node sequence."""
        return " ".join(map(self.tree.describe_choice, self.choice_path))

    def describe(self):
        """Return a one-line-ish text description of the simulation."""
        result = "%s [%s]" % (
            self.tree.format_parameters(self.get_parameters()),
            self.describe_steps())
        if self.candidate_won is not None:
            result += (" lost", " won")[self.candidate_won]
        return result

    def describe_briefly(self):
        """Return a shorter description of the simulation."""
        return "%s %s" % (self.tree.format_parameters(self.get_parameters()),
                          ("lost", "won")[self.candidate_won])

class Greedy_simulation(Simulation):
    """Variant of simulation that chooses the node with most wins.

    This is used to pick the 'best' parameters from the current state of the
    tree.

    """
    def _choose_action(self, node):
        def wins((i, node)):
            return node.wins
        return max(enumerate(node.children), key=wins)


class Mcts_tuner(Competition):
    """A Competition for parameter tuning using the Monte-carlo tree search.

    The game ids are strings containing integers starting from zero.

    """
    def __init__(self, competition_code, **kwargs):
        Competition.__init__(self, competition_code, **kwargs)
        self.outstanding_simulations = {}
        self.halt_on_next_failure = True

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
        Setting('number_of_games', allow_none(interpret_int), default=None),
        Setting('candidate_colour', interpret_colour),
        Setting('log_tree_to_history_period',
                allow_none(interpret_positive_int), default=None),
        Setting('summary_spec', interpret_sequence_of(interpret_int),
                default=(30,)),
        Setting('number_of_running_simulations_to_show', interpret_int,
                default=12),
        ]

    special_settings = [
        Setting('opponent', interpret_any),
        Setting('convert_optimiser_parameters_to_engine_parameters',
                interpret_callable),
        Setting('format_parameters', interpret_callable),
        Setting('make_candidate', interpret_callable),
        ]

    # These are used to instantiate Tree; they don't turn into Mcts_tuner
    # attributes.
    tree_settings = [
        Setting('dimensions', interpret_positive_int),
        Setting('subdivisions', interpret_positive_int),
        Setting('max_depth', interpret_positive_int),
        Setting('exploration_coefficient', interpret_float),
        Setting('initial_visits', interpret_positive_int),
        Setting('initial_wins', interpret_positive_int),
        ]

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        competitions.validate_handicap(
            self.handicap, self.handicap_style, self.board_size)

        try:
            specials = load_settings(self.special_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        try:
            self.opponent = self.players[specials['opponent']]
        except KeyError:
            raise ControlFileError(
                "opponent: unknown player %s" % specials['opponent'])

        self.translate_parameters_fn = \
            specials['convert_optimiser_parameters_to_engine_parameters']
        self.format_parameters_fn = specials['format_parameters']
        self.candidate_maker_fn = specials['make_candidate']

        try:
            tree_arguments = load_settings(self.tree_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))
        tree_arguments['parameter_formatter'] = self.format_parameters
        self.tree = Tree(**tree_arguments)


    # State attributes (*: in persistent state):
    #  *scheduler               -- Simple_scheduler
    #  *tree                    -- Tree (root node is persisted)
    #   outstanding_simulations -- map game_number -> Simulation
    #   halt_on_next_failure    -- bool


    def set_clean_status(self):
        self.scheduler = competition_schedulers.Simple_scheduler()
        self.tree.new_root()

    def get_status(self):
        return {
            'scheduler' : self.scheduler,
            'tree_root' : self.tree.root,
            }

    def set_status(self, status):
        self.scheduler = status['scheduler']
        self.scheduler.rollback()
        root = status['tree_root']
        self.tree.set_root(root)

    def format_parameters(self, optimiser_parameters):
        try:
            return self.format_parameters_fn(optimiser_parameters)
        except StandardError:
            return ("[error from user-defined parameter formatter]\n"
                    "[optimiser parameters %s]" % optimiser_parameters)

    def make_candidate(self, player_code, optimiser_parameters):
        """Make a player using the specified optimiser parameters.

        Returns a game_jobs.Player.

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
            candidate = self.game_jobs_player_from_config(
                player_code, candidate_config)
        except StandardError, e:
            raise CompetitionError(
                "error making candidate player\nparameters: %s\nerror: %s" %
                (self.format_parameters(optimiser_parameters), e))
        return candidate

    def get_player_checks(self):
        test_parameters = self.tree.get_test_parameters()
        candidate = self.make_candidate('candidate', test_parameters)
        result = []
        for player in [candidate, self.opponent]:
            check = game_jobs.Player_check()
            check.player = player
            check.board_size = self.board_size
            check.komi = self.komi
            result.append(check)
        return result

    def get_game(self):
        if (self.number_of_games is not None and
            self.scheduler.issued >= self.number_of_games):
            return NoGameAvailable
        game_number = self.scheduler.issue()

        simulation = Simulation(self.tree)
        simulation.run()
        candidate = self.make_candidate(
            "#%d" % game_number, simulation.get_parameters())
        self.outstanding_simulations[game_number] = simulation

        job = game_jobs.Game_job()
        job.game_id = str(game_number)
        job.game_data = game_number
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
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        self.halt_on_next_failure = False
        game_number = response.game_data
        self.scheduler.fix(game_number)
        # Counting no-result as loss for the candidate
        candidate_won = (
            response.game_result.winning_colour == self.candidate_colour)
        simulation = self.outstanding_simulations.pop(game_number)
        simulation.update_stats(candidate_won)
        self.log_history(simulation.describe())
        if (self.log_tree_to_history_period is not None and
            self.scheduler.fixed % self.log_tree_to_history_period == 0):
            self.log_history(self.tree.describe())
        return "%s %s" % (simulation.describe(),
                          response.game_result.sgf_result)

    def process_game_error(self, job, previous_error_count):
        ## If the very first game to return a response gives an error, halt.
        ## If two games in a row give an error, halt.
        ## Otherwise, forget about the failed game
        stop_competition = False
        retry_game = False
        game_number = job.game_data
        del self.outstanding_simulations[game_number]
        self.scheduler.fix(game_number)
        if self.halt_on_next_failure:
            stop_competition = True
        else:
            self.halt_on_next_failure = True
        return stop_competition, retry_game

    def write_static_description(self, out):
        def p(s):
            print >>out, s
        p("MCTS tuning event: %s" % self.competition_code)
        p(self.description)
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)

    def _write_main_report(self, out):
        games_played = self.scheduler.fixed
        if self.number_of_games is None:
            print >>out, "%d games played" % games_played
        else:
            print >>out, "%d/%d games played" % (
                games_played, self.number_of_games)
        print >>out
        best_simulation = self.tree.retrieve_best_parameter_simulation()
        print >>out, "Best parameter vector: %s" % best_simulation.describe()
        print >>out
        self.tree.summarise(out, self.summary_spec)

    def write_screen_report(self, out):
        self._write_main_report(out)
        if self.outstanding_simulations:
            print >>out, "In progress:"
            to_show = sorted(self.outstanding_simulations.iteritems())\
                      [:self.number_of_running_simulations_to_show]
            for game_id, simulation in to_show:
                print >>out, "game %s: %s" % (game_id, simulation.describe())

    def write_short_report(self, out):
        self.write_static_description(out)
        self._write_main_report(out)

    write_full_report = write_short_report

