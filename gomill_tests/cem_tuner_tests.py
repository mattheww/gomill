"""Tests for cem_tuners.py"""

from __future__ import with_statement, division

import cPickle as pickle
from textwrap import dedent

from gomill import cem_tuners
from gomill.game_jobs import Game_job, Game_job_result
from gomill.gtp_games import Game_result
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
        'samples_per_generation' : 4,
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
    TypeError: expected-float
    traceback (most recent call last):
    cem_tuner_tests|clip_axisb
    failing line:
    f = float(f)
    """), fixups=[
    ("float() argument must be a string or a number", "expected-float"),
    ("expected float, got NoneType object", "expected-float"),
    ])

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

def test_nonsense_parameter_config(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    config = default_config()
    config['parameters'].append(99)
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    'parameters': item 2: not a Parameter"""))

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
    TypeError: split-wants-float-not-str
    traceback (most recent call last):
    """), fixups=[
     ("descriptor 'split' requires a 'str' object but received a 'float'",
      "split-wants-float-not-str"),
     ("unbound method split() must be called with str instance as "
      "first argument (got float instance instead)",
      "split-wants-float-not-str"),
     ])

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

def test_play(tc):
    comp = cem_tuners.Cem_tuner('cemtest')
    comp.initialise_from_control_file(default_config())
    comp.set_clean_status()

    tc.assertEqual(comp.generation, 0)
    tc.assertEqual(comp.distribution.format(),
                   " 0.50~1.00 50.00~1000.00")

    job1 = comp.get_game()
    tc.assertIsInstance(job1, Game_job)
    tc.assertEqual(job1.game_id, 'g0#0r0')
    tc.assertEqual(job1.player_b.code, 'g0#0')
    tc.assertEqual(job1.player_w.code, 'opp')
    tc.assertEqual(job1.board_size, 13)
    tc.assertEqual(job1.komi, 7.5)
    tc.assertEqual(job1.move_limit, 1000)
    tc.assertIs(job1.use_internal_scorer, False)
    tc.assertEqual(job1.internal_scorer_handicap_compensation, 'full')
    tc.assertEqual(job1.game_data, (0, 'g0#0', 0))
    tc.assertEqual(job1.sgf_event, 'cemtest')
    tc.assertRegexpMatches(job1.sgf_note, '^Candidate parameters: axa ')

    job2 = comp.get_game()
    tc.assertIsInstance(job2, Game_job)
    tc.assertEqual(job2.game_id, 'g0#1r0')
    tc.assertEqual(job2.player_b.code, 'g0#1')
    tc.assertEqual(job2.player_w.code, 'opp')

    tc.assertEqual(comp.wins, [0, 0, 0, 0])

    result1 = Game_result({'b' : 'g0#0', 'w' : 'opp'}, 'b')
    result1.sgf_result = "B+8.5"
    response1 = Game_job_result()
    response1.game_id = job1.game_id
    response1.game_result = result1
    response1.engine_names = {
        'opp'  : 'opp engine:v1.2.3',
        'g0#0' : 'candidate engine',
        }
    response1.engine_descriptions = {
        'opp'  : 'opp engine:v1.2.3',
        'g0#0' : 'candidate engine description',
        }
    response1.game_data = job1.game_data
    comp.process_game_result(response1)

    tc.assertEqual(comp.wins, [1, 0, 0, 0])

    comp2 = cem_tuners.Cem_tuner('cemtest')
    comp2.initialise_from_control_file(default_config())
    status = pickle.loads(pickle.dumps(comp.get_status()))
    comp2.set_status(status)
    tc.assertEqual(comp2.wins, [1, 0, 0, 0])

    result2 = Game_result({'b' : 'g0#1', 'w' : 'opp'}, None)
    result2.set_jigo()
    response2 = Game_job_result()
    response2.game_id = job2.game_id
    response2.game_result = result2
    response2.engine_names = response1.engine_names
    response2.engine_descriptions = response1.engine_descriptions
    response2.game_data = job2.game_data
    comp.process_game_result(response2)

    tc.assertEqual(comp.wins, [1, 0.5, 0, 0])

