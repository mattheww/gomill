"""Tests for mcts_tuners.py"""

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
    return Player_config("cand " + " ".join(map(str, args)))

def test_parameter_config(tc):
    comp = mcts_tuners.Mcts_tuner('mctstest')
    config = {
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
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.format_parameters((0.5, 23)), "rsn@ 0.50; iwins 23")
    tc.assertEqual(comp.format_parameters(('x', 3)), "[resign_at?x]; iwins 3")
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
    cand = comp.make_candidate('c#1', (0.5, 0.23))
    tc.assertEqual(cand.code, 'c#1')
    tc.assertListEqual(cand.cmd_args, ['cand', '0.5', '23'])
