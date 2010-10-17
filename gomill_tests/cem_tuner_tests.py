"""Tests for cem_tuners.py"""

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
    return max(0.0, max(100.0, f))

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
                format = "axa %.3f",),
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
    # FIXME
