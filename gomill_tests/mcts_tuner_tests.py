"""Tests for mcts_tuners.py"""

from math import sqrt
from textwrap import dedent

from gomill import mcts_tuners
from gomill.mcts_tuners import Parameter_config
from gomill.competitions import (
    Player_config, CompetitionError, ControlFileError)

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def trivial_scale_fn(f):
    return f

def times_100_fn(f):
    return int(100*f)

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
                scale_fn = trivial_scale_fn,
                format = "rsn@ %.2f"),

            Parameter_config(
                'initial_wins',
                scale_fn = times_100_fn,
                format = "iwins %d"),
            ],
        'make_candidate' : simple_make_candidate,
        # FIXME: The remainder should be optional
        'max_depth' : 1,
        'subdivisions' : 2,
        }

def test_parameter_config(tc):
    comp = mcts_tuners.Mcts_tuner('mctstest')
    config = default_config()
    comp.initialise_from_control_file(config)
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
    error from scale_fn for initial_wins
    TypeError: unsupported operand type(s) for *: 'int' and 'NoneType'
    traceback (most recent call last):
    mcts_tuner_tests|times_100_fn
    failing line:
    return int(100*f)
    """))

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
    ls = mcts_tuners.Linear_scale_fn(20.0, 30.0)
    tc.assertEqual(ls(0.0), 20.0)
    tc.assertEqual(ls(1.0), 30.0)
    tc.assertEqual(ls(0.5), 25.0)

def test_log_scale(tc):
    ls = mcts_tuners.Log_scale_fn(2, 200000)
    tc.assertAlmostEqual(ls(0.0), 2.0)
    tc.assertAlmostEqual(ls(0.2), 20.0)
    tc.assertAlmostEqual(ls(0.4), 200.0)
    tc.assertAlmostEqual(ls(0.5), 2*sqrt(100000.00))
    tc.assertAlmostEqual(ls(0.6), 2000.0)
    tc.assertAlmostEqual(ls(0.8), 20000.0)
    tc.assertAlmostEqual(ls(1.0), 200000.0)
