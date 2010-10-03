"""Tests for ringmaster.py."""

import string

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import ringmaster_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

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

simple_ctl = string.Template("""

competition_type = 'playoff'

description = 'gomill_tests playoff.'

players = {
    'p1'  : Player("test ${cmdline1}", stderr=DISCARD),
    'p2'  : Player("test ${cmdline2}", stderr=DISCARD),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = 'internal'

number_of_games = 400

matchups = [
    Matchup('p1', 'p2'),
    ]

""")

def test_check_players(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "",
        }
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals))
    tc.assertTrue(fx.ringmaster.check_players(discard_stderr=True))

def test_run(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "",
        }
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals))
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run(max_games=3)
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve('warnings'),
        [])

def test_check_players_fail(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "fail=startup",
        }
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals))
    tc.assertFalse(fx.ringmaster.check_players(discard_stderr=True))

def test_run_fail(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "fail=startup",
        }
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals))
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run()
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve('warnings'),
        ["game 0_0 -- aborting game due to error:\n"
         "error starting subprocess for player p2:\n"
         "exec forced to fail",
         "halting run due to void games"])

