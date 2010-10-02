"""Tests for ringmaster.py."""

import os

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import ringmaster_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

test1_ctl = """

competition_type = 'playoff'

description = "gomill_tests playoff 'test1'."

players = {
    'gtptest'  : Player("test", stderr=DISCARD),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = "internal"

number_of_games = 400

matchups = [
    Matchup('gtptest', 'gtptest'),
    ]

"""

test2_ctl = """

competition_type = 'playoff'

description = "gomill_tests playoff 'test1'."

players = {
    'gtptest'  : Player("test", stderr=DISCARD),
    'failer'   : Player("test fail=startup", stderr=DISCARD),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = "internal"

number_of_games = 400

matchups = [
    Matchup('gtptest', 'failer', handicap=6, handicap_style='fixed'),
    ]

"""



class Ringmaster_fixture(test_framework.Fixture):
    """Fixture setting up a Ringmaster with mock suprocesses.

    attributes:
      ringmaster -- Testing_ringmaster
      msf        -- Mock_subprocess_fixture

    """
    def __init__(self, tc, control_file_contents):
        self.ringmaster = ringmaster_test_support.Testing_ringmaster(
            control_file_contents)
        self.ringmaster.set_display_mode('test')
        self.msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)

def test_check_players(tc):
    fx = Ringmaster_fixture(tc, test1_ctl)
    tc.assertTrue(fx.ringmaster.check_players(discard_stderr=True))

def test_run(tc):
    fx = Ringmaster_fixture(tc, test1_ctl)
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run(max_games=3)
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve_warnings(),
        [])

def test_check_players_fail(tc):
    fx = Ringmaster_fixture(tc, test2_ctl)
    tc.assertFalse(fx.ringmaster.check_players(discard_stderr=True))

def test_run_fail(tc):
    fx = Ringmaster_fixture(tc, test2_ctl)
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run()
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve_warnings(),
        ["game 0_0 -- aborting game due to error:\n"
         "error starting subprocess for player failer:\n"
         "exec forced to fail",
         "halting run due to void games"])

