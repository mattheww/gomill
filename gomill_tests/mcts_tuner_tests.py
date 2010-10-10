"""Tests for mcts_tuners.py"""

from __future__ import with_statement, division

from math import sqrt
import random
from textwrap import dedent

from gomill import mcts_tuners
from gomill.mcts_tuners import Parameter_config
from gomill.competitions import (
    Player_config, CompetitionError, ControlFileError)

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def simple_make_candidate(*args):
    if -1 in args:
        raise ValueError("oops")
    return Player_config("cand " + " ".join(map(str, args)))

def default_config():
    return {
        'board_size' : 13,
        'komi' : 7.5,
        'players' : {
            'opp' : Player_config("test"),
            },
        'candidate_colour' : 'w',
        'opponent' : 'opp',
        'exploration_coefficient' : 0.2,
        'initial_visits' : 10,
        'initial_wins' : 5,
        'parameters' : [
            Parameter_config(
                'resign_at',
                scale = float,
                split = 12,
                format = "rsn@ %.2f"),

            Parameter_config(
                'initial_wins',
                scale = mcts_tuners.LINEAR(0, 100),
                split = 10,
                format = "iwins %d"),
            ],
        'make_candidate' : simple_make_candidate,
        }

def test_parameter_config(tc):
    comp = mcts_tuners.Mcts_tuner('mctstest')
    config = default_config()
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.tree.max_depth, 1)
    tc.assertEqual(comp.format_engine_parameters((0.5, 23)),
                   "rsn@ 0.50; iwins 23")
    tc.assertEqual(comp.format_engine_parameters(('x', 23)),
                   "[resign_at?x]; iwins 23")
    tc.assertEqual(comp.format_optimiser_parameters((0.5, 0.23)),
                   "rsn@ 0.50; iwins 23")
    tc.assertEqual(comp.scale_parameters((0.5, 0.23)), (0.5, 23))
    with tc.assertRaises(CompetitionError) as ar:
        comp.scale_parameters((0.5, None))
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    error from scaler for initial_wins
    TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'
    traceback (most recent call last):
    mcts_tuners|__call__
    failing line:
    result = (f * self.range) + self.lower_bound
    """))

    tc.assertRaisesRegexp(
        ValueError, "'code' not specified",
        comp.parameter_spec_from_config, Parameter_config())
    tc.assertRaisesRegexp(
        ValueError, "code specified as both positional and keyword argument",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', code='pa2', scale=float, split=2, format="%s"))
    tc.assertRaisesRegexp(
        ValueError, "too many positional arguments",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', float, scale=float, split=2, format="%s"))
    tc.assertRaisesRegexp(
        ValueError, "'scale': invalid callable",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', scale=None, split=2, format="%s"))
    pspec = comp.parameter_spec_from_config(
        Parameter_config('pa1', scale=float, split=2))
    tc.assertRaisesRegexp(
        ControlFileError, "'format': invalid format string",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', scale=float, split=2, format="nopct"))

def test_bad_parameter_config(tc):
    comp = mcts_tuners.Mcts_tuner('mctstest')
    config = default_config()
    config['parameters'].append(
        Parameter_config(
            'bad',
            scale = mcts_tuners.LINEAR(0, 'a'),
            split = 10))
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    parameter bad: 'scale': invalid parameters for LINEAR:
    invalid literal for float(): a"""))

def test_make_candidate(tc):
    comp = mcts_tuners.Mcts_tuner('mctstest')
    config = default_config()
    comp.initialise_from_control_file(config)
    cand = comp.make_candidate('c#1', (0.5, 23))
    tc.assertEqual(cand.code, 'c#1')
    tc.assertListEqual(cand.cmd_args, ['cand', '0.5', '23'])
    with tc.assertRaises(CompetitionError) as ar:
        comp.make_candidate('c#1', (-1, 23))
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    error from make_candidate()
    ValueError: oops
    traceback (most recent call last):
    mcts_tuner_tests|simple_make_candidate
    failing line:
    raise ValueError("oops")
    """))

def test_linear_scale(tc):
    lsf = mcts_tuners.Linear_scale_fn(20.0, 30.0)
    tc.assertEqual(lsf(0.0), 20.0)
    tc.assertEqual(lsf(1.0), 30.0)
    tc.assertEqual(lsf(0.5), 25.0)
    tc.assertEqual(lsf(0.49), 24.9)

    lsi = mcts_tuners.Linear_scale_fn(20.0, 30.0, integer=True)
    tc.assertEqual(lsi(0.0), 20)
    tc.assertEqual(lsi(1.0), 30)
    tc.assertEqual(lsi(0.49), 25)
    tc.assertEqual(lsi(0.51), 25)

def test_log_scale(tc):
    lsf = mcts_tuners.Log_scale_fn(2, 200000)
    tc.assertAlmostEqual(lsf(0.0), 2.0)
    tc.assertAlmostEqual(lsf(0.2), 20.0)
    tc.assertAlmostEqual(lsf(0.4), 200.0)
    tc.assertAlmostEqual(lsf(0.5), 2*sqrt(100000.00))
    tc.assertAlmostEqual(lsf(0.6), 2000.0)
    tc.assertAlmostEqual(lsf(0.8), 20000.0)
    tc.assertAlmostEqual(lsf(1.0), 200000.0)

    lsi = mcts_tuners.Log_scale_fn(1, 100, integer=True)
    tc.assertAlmostEqual(lsi(0.1), 2)

def test_tree(tc):
    tree1 = mcts_tuners.Tree(
        splits=[3, 3],
        max_depth=5,
        exploration_coefficient=0.5,
        initial_visits=10,
        initial_wins=5,
        parameter_formatter=str,
        )

    tree2 = mcts_tuners.Tree(
        splits=[2, 4],
        max_depth=5,
        exploration_coefficient=0.5,
        initial_visits=10,
        initial_wins=5,
        parameter_formatter=str,
        )

    tc.assertEqual(tree1.max_depth, 5)

    tc.assertEqual(tree1._cube_coordinates, [
        (0, 0), (0, 1), (0, 2),
        (1, 0), (1, 1), (1, 2),
        (2, 0), (2, 1), (2, 2),
        ])

    tc.assertEqual(tree2._cube_coordinates, [
        (0, 0), (0, 1), (0, 2), (0, 3),
        (1, 0), (1, 1), (1, 2), (1, 3),
        ])

    def scaleup(vector, scales):
        """Multiply each member of 'vector' by the corresponding scale.

        Rounds to nearest integer if the difference is very small.

        """
        result = []
        for v, scale in zip(vector, scales):
            f = v*scale
            i = int(f+.5)
            if abs(f - i) > 0.0000000001:
                result.append(f)
            else:
                result.append(i)
        return result

    def pfp1(choice_path):
        optimiser_params = tree1.parameters_for_path(choice_path)
        scale = 3**len(choice_path) * 2
        return scaleup(optimiser_params, [scale, scale])

    # scale is 1/6
    tc.assertEqual(pfp1([0]), [1, 1])
    tc.assertEqual(pfp1([1]), [1, 3])
    tc.assertEqual(pfp1([3]), [3, 1])
    tc.assertEqual(pfp1([8]), [5, 5])
    # scale is 1/18
    tc.assertEqual(pfp1([0, 0]), [1, 1])
    tc.assertEqual(pfp1([0, 1]), [1, 3])
    tc.assertEqual(pfp1([3, 1]), [7, 3])
    tc.assertEqual(pfp1([3, 4]), [9, 3])

    def pfp2(choice_path):
        optimiser_params = tree2.parameters_for_path(choice_path)
        scale1 = 2**len(choice_path) * 2
        scale2 = 4**len(choice_path) * 2
        return scaleup(optimiser_params, [scale1, scale2])

    # scale is 1/4, 1/8
    tc.assertEqual(pfp2([0]), [1, 1])
    tc.assertEqual(pfp2([1]), [1, 3])
    tc.assertEqual(pfp2([2]), [1, 5])
    tc.assertEqual(pfp2([3]), [1, 7])
    tc.assertEqual(pfp2([4]), [3, 1])
    tc.assertEqual(pfp2([5]), [3, 3])
    # scale is 1/8, 1/32
    tc.assertEqual(pfp2([0, 0]), [1, 1])
    tc.assertEqual(pfp2([0, 1]), [1, 3])
    tc.assertEqual(pfp2([0, 2]), [1, 5])
    tc.assertEqual(pfp2([0, 3]), [1, 7])
    tc.assertEqual(pfp2([0, 4]), [3, 1])
    tc.assertEqual(pfp2([1, 0]), [1, 9])
    tc.assertEqual(pfp2([7, 7]), [7, 31])



def _disabled_test_tree_run(tc):
    # Something like this test can be useful when changing the tree code,
    # if you want to verify that you're not changing behaviour.

    tree = mcts_tuners.Tree(
        splits=[2, 3],
        max_depth=5,
        exploration_coefficient=0.5,
        initial_visits=10,
        initial_wins=5,
        parameter_formatter=str,
        )

    tree.new_root()
    random.seed(12345)
    for i in range(1100):
        simulation = mcts_tuners.Simulation(tree)
        simulation.run()
        simulation.update_stats(candidate_won=random.randrange(2))
    tc.assertEqual(simulation.get_parameters(),
                   [0.0625, 0.42592592592592593])
    tc.assertEqual(tree.node_count, 1597)
    tc.assertEqual(simulation.choice_path, [1, 0, 2])
    tc.assertEqual(tree.retrieve_best_parameters(),
                   [0.609375, 0.68930041152263366])

