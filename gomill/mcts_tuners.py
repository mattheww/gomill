"""Competitions for parameter tuning using Monte-carlo tree search."""

from __future__ import division

import cPickle as pickle
import random
from math import log, sqrt

from gomill import compact_tracebacks
from gomill import game_jobs
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError,
    Player_config, game_jobs_player_from_config)


BRANCHING_FACTOR        =     3
MAX_DEPTH               =     5

LOG_AFTER_GAMES         =     8

class Node(object):
    """A MCTS node.

    Public attributes:
      children     -- list of Nodes, or None for unexpanded
      wins
      visits
      value        -- wins / visits

    """
    pass

    #__slots__ = (
    #    'children',
    #    'wins',
    #    'visits',
    #    'value',
    #    'rsqrt_visits',
    #    )

class Tree(object):
    """Run monte-carlo tree search over parameter space.

    """
    def __init__(self, exploration_coefficient, initial_visits):
        self.exploration_coefficient = exploration_coefficient
        self.initial_visits = initial_visits
        self.initial_wins = initial_visits / 2
        self.initial_rsqrt_visits = 1 / initial_visits
        self.node_count = 1 # For description only
        self.root = Node()
        self.root.children = None
        self.root.wins = self.initial_wins
        self.root.visits = self.initial_visits
        self.root.value = 0.5
        self.root.rsqrt_visits = self.initial_rsqrt_visits
        self.expand(self.root)

    def expand(self, node):
        assert node.children is None
        node.children = []
        for _ in xrange(BRANCHING_FACTOR):
            child = Node()
            child.children = None
            child.wins = self.initial_wins
            child.visits = self.initial_visits
            child.value = 0.5
            child.rsqrt_visits = self.initial_rsqrt_visits
            node.children.append(child)
        self.node_count += BRANCHING_FACTOR

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
        lo = 0.0
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
            breadth /= BRANCHING_FACTOR
            lo += breadth * best_choice
            node = best
        return [lo + 0.5*breadth]

class Walker(object):
    """FIXME"""
    def __init__(self, tree):
        self.tree = tree
        self.node_path = []
        self.choice_path = [] # For description only
        self.parameter_min = 0.0
        self.parameter_breadth = 1.0
        self.debug = []

    def get_parameter(self):
        return self.parameter_min + .5*self.parameter_breadth

    def describe_steps(self):
        return " ".join(map(str, self.choice_path))

    def step(self, choice, node):
        self.parameter_breadth /= BRANCHING_FACTOR
        self.parameter_min += self.parameter_breadth * choice
        self.node_path.append(node)
        self.choice_path.append(choice)

    def walk(self):
        node = self.tree.root
        while node.children is not None:
            choice, node = self.tree.choose_action(node)
            self.step(choice, node)
        if (node.visits != self.tree.initial_visits and
            len(self.node_path) < MAX_DEPTH):
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



class Mcts_tuner(Competition):
    """A Competition for parameter tuning using the Monte-carlo tree search."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)
        # These are only for the sake of display
        self.last_simulation = None
        self.won_last_game = False

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)
        # Ought to validate properly
        self.number_of_games = config.get('number_of_games')
        self.exploration_coefficient = config['exploration_coefficient']
        self.initial_visits = config['initial_visits']
        if (self.initial_visits % 2) != 0:
            raise ValueError("initial_visits must be even")

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
        return {
            'next_game_number' : self.next_game_number,
            'games_played'     : self.games_played,
            'tree'             : pickle.dumps(self.tree),
            'outstanding_sims' : pickle.dumps(self.outstanding_simulations),
            }

    def set_status(self, status):
        self.next_game_number = status['next_game_number']
        self.games_played = status['games_played']
        self.tree = pickle.loads(
            status['tree'].encode('iso-8859-1'))
        self.outstanding_simulations = pickle.loads(
            status['outstanding_sims'].encode('iso-8859-1'))

    def set_clean_status(self):
        self.next_game_number = 0
        self.games_played = 0
        self.tree = Tree(self.exploration_coefficient, self.initial_visits)
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
        self.log_history(self.describe_simulation(simulation, candidate_won))
        # FIXME: Want to describe this stuff; for now, let status summary do it
        self.last_simulation = simulation
        self.won_last_game = candidate_won
        if self.games_played % LOG_AFTER_GAMES == 0:
            self.log_history(self.describe_tree())

    def describe_simulation(self, simulation, candidate_won):
        optimiser_parameters = [simulation.get_parameter()]
        params_s = self.format_parameters(optimiser_parameters)
        won_s = ("lost", "won")[candidate_won]
        return "%s [%s] %s" % (params_s, simulation.describe_steps(), won_s)

    def describe_tree(self):
        def describe_node(choice, lo_param, node):
            parameters = self.format_parameters([lo_param]) + "+"
            return "%d %s %.2f %3d" % (
                choice, parameters, node.value,
                node.visits - self.tree.initial_visits)

        root = self.tree.root
        wins = root.wins - self.tree.initial_wins
        visits = root.visits - self.tree.initial_visits
        try:
            win_rate = "%.2f" % (wins/visits)
        except ZeroDivisionError:
            win_rate = "--"
        result = [
            "%d nodes" % self.tree.node_count,
            "Win rate %d/%d = %s" % (wins, visits, win_rate)
            ]
        lo = 0.0
        breadth = 1.0
        for choice, node in enumerate(self.tree.root.children):
            breadth2 = breadth / BRANCHING_FACTOR
            lo2 = lo + breadth2 * choice
            result.append("  " + describe_node(choice, lo2, node))
            if node.children is None:
                continue
            for choice2, node2 in enumerate(node.children):
                breadth3 = breadth2 / BRANCHING_FACTOR
                lo3 = lo2 + breadth3 * choice2
                result.append("    " + describe_node(choice2, lo3, node2))
        return "\n".join(result)

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
                self.describe_simulation(
                self.last_simulation, self.won_last_game))
        print >>out, self.describe_tree()
        print >>out, "Best parameter vector: %s" % (
            self.format_parameters(self.tree.retrieve_best_parameters()))
        #waitforkey = raw_input()

    def write_results_report(self, out):
        pass
