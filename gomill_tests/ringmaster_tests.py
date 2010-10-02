"""Tests for ringmaster.py."""

import os

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
    def __init__(self, tc, control_filename):
        self.ringmaster = ringmaster_test_support.Testing_ringmaster(
            os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         "ringmaster_test_files", control_filename))
        self.ringmaster.set_display_mode('test')
        self.msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)

def test_check_players(tc):
    fx = Ringmaster_fixture(tc, 'test1.ctl')
    tc.assertFalse(fx.ringmaster.check_players(discard_stderr=True))

def test_run(tc):
    fx = Ringmaster_fixture(tc, 'test1.ctl')
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run()
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve_warnings(),
        ["game 0_0 -- aborting game due to error:\n"
         "error starting subprocess for player failer:\n"
         "exec forced to fail",
         "halting run due to void games"])
