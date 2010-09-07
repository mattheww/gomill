"""Competitions for parameter tuning using Monte-carlo tree search."""

from __future__ import division

import random
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

    def __repr__(self):
        return "<Node:%.2f{%s}>" % (self.value, repr(self.children))


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

    def retrieve_best_parameters(self):
        simulation = Greedy_simulation(self)
        simulation.walk()
        return simulation.get_parameters()

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
    """A single monte-carlo simulation."""
    def __init__(self, tree):
        self.tree = tree
        self.node_path = []
        self.choice_path = [] # For description only
        self.parameter_min = [0.0] * tree.dimensions
        self.parameter_breadth = 1.0

    def get_parameters(self):
        return [self.parameter_min[d] + .5*self.parameter_breadth
                for d in range(self.tree.dimensions)]

    def describe_steps(self):
        return " ".join(map(str, self.choice_path))

    def choose_action(self, node):
        uct_numerator = (self.tree.exploration_coefficient *
                         sqrt(log(node.visits)))
        def urgency((i, child)):
            return child.value + uct_numerator * child.rsqrt_visits
        start = random.randrange(len(node.children))
        children = list(enumerate(node.children))
        return max(children[start:] + children[:start], key=urgency)

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
            choice, node = self.choose_action(node)
            self.step(choice, node)

    def run(self):
        self.walk()
        node = self.node_path[-1]
        if (node.visits != self.tree.initial_visits and
            len(self.node_path) < self.tree.max_depth):
            self.tree.expand(node)
            choice, child = self.choose_action(node)
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

class Greedy_simulation(Simulation):
    """Variant of simulation that chooses the node with most wins.

    This is used to pick the 'best' parameters from the current state of the
    tree.

    """
    def choose_action(self, node):
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
        self.last_simulation = None
        self.won_last_game = False
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
        Setting('log_after_games', interpret_positive_int, default=8),
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
        Setting('branching_factor', interpret_positive_int),
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

    # These are used only for the screen report:
    #   last_simulation         -- Simulation or None
    #   won_last_game           -- bool


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

    def make_candidate(self, candidate_code, optimiser_parameters):
        """FIXME

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
                candidate_code, candidate_config)
        except StandardError, e:
            raise CompetitionError(
                "error making candidate player\nparameters: %s\nerror: %s" %
                (self.format_parameters(optimiser_parameters), e))
        return candidate

    def get_players_to_check(self):
        test_parameters = [.5] * self.tree.dimensions
        candidate = self.make_candidate('candidate', test_parameters)
        return [candidate, self.opponent]

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
        self.log_history(simulation.describe(candidate_won))
        # FIXME: Want to describe this stuff; for now, let status summary do it
        self.last_simulation = simulation
        self.won_last_game = candidate_won
        if self.scheduler.fixed % self.log_after_games == 0:
            self.log_history(self.tree.describe())

    def process_game_error(self, job, previous_error_count):
        ## If the very first game gives an error, halt.
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

    def write_screen_report(self, out):
        games_played = self.scheduler.fixed
        if self.number_of_games is None:
            print >>out, "%d games played" % games_played
        else:
            print >>out, "%d/%d games played" % (
                games_played, self.number_of_games)
        print >>out
        if self.last_simulation is not None:
            print >>out, "Last simulation: %s" % (
                self.last_simulation.describe(self.won_last_game))
        print >>out, self.tree.describe()
        print >>out, "Best parameter vector: %s" % (
            self.format_parameters(self.tree.retrieve_best_parameters()))
        #waitforkey = raw_input()

    def write_short_report(self, out):
        self.write_static_description(out)
        self.write_screen_report(out)

    write_full_report = write_short_report

