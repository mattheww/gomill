"""Tests for cem_tuners.py"""

from __future__ import with_statement, division

from textwrap import dedent

from gomill import cem_tuners
from gomill.cem_tuners import Parameter_config
from gomill.competitions import (
    Player_config, CompetitionError, ControlFileError)

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def simple_make_candidate(*args):
    if -1 in args:
        raise ValueError("oops")
    return Player_config("cand " + " ".join(map(str, args)))

def clip_axisb(f):
    f = float(f)
    return max(0.0, min(100.0, f))

def default_config():
    return {
        'board_size' : 13,
        'komi' : 7.5,
        'players' : {
            'opp' : Player_config("test"),
            },
        'candidate_colour' : 'w',
        'opponent' : 'opp',
        'parameters' : [
            Parameter_config(
                'axisa',
                initial_mean = 0.5,
                initial_variance = 1.0,
                format = "axa %.3f"),
            Parameter_config(
                'axisb',
                initial_mean = 50.0,
                initial_variance = 1000.0,
                transform = clip_axisb,
                format = "axb %.1f"),
            ],
        'batch_size' : 3,
        'samples_per_generation' : 12,
        'number_of_generations' : 3,
        'elite_proportion' : 0.1,
        'step_size' : 0.8,
        'make_candidate' : simple_make_candidate,
        }

def test_parameter_config(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    config = default_config()
    comp.initialise_from_control_file(config)

    tc.assertEqual(comp.initial_distribution.format(),
                   " 0.50~1.00 50.00~1000.00")
    tc.assertEqual(comp.format_engine_parameters((0.5, 23)),
                   "axa 0.500; axb 23.0")
    tc.assertEqual(comp.format_engine_parameters(('x', 23)),
                   "[axisa?x]; axb 23.0")
    tc.assertEqual(comp.format_optimiser_parameters((0.5, 500)),
                   "axa 0.500; axb 100.0")

    tc.assertEqual(comp.transform_parameters((0.5, 1e6)), (0.5, 100.0))
    with tc.assertRaises(CompetitionError) as ar:
        comp.transform_parameters((0.5, None))
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    error from transform for axisb
    TypeError: float() argument must be a string or a number
    traceback (most recent call last):
    cem_tuner_tests|clip_axisb
    failing line:
    f = float(f)
    """))

    tc.assertRaisesRegexp(
        ValueError, "'initial_variance': must be nonnegative",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', initial_mean=0,
                         initial_variance=-1, format="%s"))
    tc.assertRaisesRegexp(
        ControlFileError, "'format': invalid format string",
        comp.parameter_spec_from_config,
        Parameter_config('pa1', initial_mean=0, initial_variance=1,
                         format="nopct"))

def test_transform_check(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    config = default_config()
    config['parameters'][0] = Parameter_config(
        'axisa',
        initial_mean = 0.5,
        initial_variance = 1.0,
        transform = str.split)
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    parameter axisa: error from transform (applied to initial_mean)
    TypeError: descriptor 'split' requires a 'str' object but received a 'float'
    traceback (most recent call last):
    """))

def test_format_validation(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    config = default_config()
    config['parameters'][0] = Parameter_config(
        'axisa',
        initial_mean = 0.5,
        initial_variance = 1.0,
        transform = str,
        format = "axa %f")
    tc.assertRaisesRegexp(
        ControlFileError, "'format': invalid format string",
        comp.initialise_from_control_file, config)

def test_make_candidate(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    config = default_config()
    comp.initialise_from_control_file(config)
    cand = comp.make_candidate('g0#1', (0.5, 23.0))
    tc.assertEqual(cand.code, 'g0#1')
    tc.assertListEqual(cand.cmd_args, ['cand', '0.5', '23.0'])
    with tc.assertRaises(CompetitionError) as ar:
        comp.make_candidate('g0#1', (-1, 23))
    tc.assertTracebackStringEqual(str(ar.exception), dedent("""\
    error from make_candidate()
    ValueError: oops
    traceback (most recent call last):
    cem_tuner_tests|simple_make_candidate
    failing line:
    raise ValueError("oops")
    """))

