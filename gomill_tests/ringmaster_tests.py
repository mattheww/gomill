"""Tests for ringmaster.py."""

import os

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import ringmaster_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Ringmaster_fixture(test_framework.Fixture):
    """Fixture setting up a Game_job.

    attributes:
      ringmaster -- Testing_ringmaster

    """
    def __init__(self, tc, control_filename):
        self.ringmaster = ringmaster_test_support.Testing_ringmaster(
            os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         "ringmaster_test_files", control_filename))

def xtest_check_players(tc):
    fx = Ringmaster_fixture(tc, 'test1.ctl')
    fx.ringmaster.check_players(discard_stderr=True)

def test_run(tc):
    fx = Ringmaster_fixture(tc, 'test1.ctl')
    fx.ringmaster.set_display_mode('test')
    fx.ringmaster.set_clean_status()
    fx.ringmaster.run()
    tc.assertListEqual(
        fx.ringmaster.presenter.retrieve_warnings(),
        ["game 0_0 -- aborting game due to error:\n"
         "GTP protocol error reading response to 'gomill-genmove_claim b' "
         "from player failer:\n"
         "no success/failure indication from engine: first line is "
         "`!! forced ill-formed GTP response`",
         "halting run due to void games"])
