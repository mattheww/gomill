"""Tests for ringmaster.py."""

import os
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

    def messages(self, channel):
        """Return messages sent to the specified channel."""
        return self.ringmaster.presenter.recent_messages(channel)

    def get_job(self):
        """Initialise the ringmaster, and call get_job() once."""
        self.ringmaster.set_clean_status()
        self.ringmaster._open_files()
        self.ringmaster._initialise_presenter()
        self.ringmaster._initialise_terminal_reader()
        return self.ringmaster.get_job()


simple_ctl = string.Template("""

competition_type = 'playoff'

description = 'gomill_tests playoff.'

players = {
    'p1'  : Player("test ${cmdline1}", discard_stderr=True),
    'p2'  : Player("test ${cmdline2}", discard_stderr=True),
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

def test_get_job(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "sing song",
        }
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals))
    job = fx.get_job()
    tc.assertEqual(job.game_id, "0_000")
    tc.assertEqual(job.game_data, ("0", 0))
    tc.assertEqual(job.board_size, 9)
    tc.assertEqual(job.komi, 7.5)
    tc.assertEqual(job.move_limit, 400)
    tc.assertEqual(job.handicap, None)
    tc.assertIs(job.handicap_is_free, False)
    tc.assertIs(job.use_internal_scorer, True)
    tc.assertEqual(job.sgf_event, 'test')
    tc.assertIsNone(job.gtp_log_pathname)
    tc.assertIsNone(job.sgf_filename)
    tc.assertIsNone(job.sgf_dirname)
    tc.assertIsNone(job.void_sgf_dirname)
    tc.assertEqual(job.player_b.code, 'p1')
    tc.assertEqual(job.player_w.code, 'p2')
    tc.assertEqual(job.player_b.cmd_args, ['test'])
    tc.assertEqual(job.player_w.cmd_args, ['test', 'sing', 'song'])
    tc.assertDictEqual(job.player_b.gtp_translations, {})
    tc.assertListEqual(job.player_b.startup_gtp_commands, [])
    tc.assertEqual(job.player_b.stderr_pathname, os.devnull)
    tc.assertIsNone(job.player_b.cwd)
    tc.assertIsNone(job.player_b.environ)

def test_settings(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "",
        }
    extra = "\n".join([
        "handicap = 9",
        "handicap_style = 'free'",
        "record_games = True",
        "scorer = 'players'"
        ])
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals) + extra)
    fx.ringmaster.enable_gtp_logging()
    job = fx.get_job()
    tc.assertEqual(job.game_id, "0_000")
    tc.assertEqual(job.handicap, 9)
    tc.assertIs(job.handicap_is_free, True)
    tc.assertIs(job.use_internal_scorer, False)
    tc.assertEqual(job.player_b.stderr_pathname, os.devnull)
    tc.assertEqual(job.gtp_log_pathname,
                   '/nonexistent/ctl/test.gtplogs/0_000.log')
    tc.assertEqual(job.sgf_filename, '0_000.sgf')
    tc.assertEqual(job.sgf_dirname, '/nonexistent/ctl/test.games')
    tc.assertEqual(job.void_sgf_dirname, '/nonexistent/ctl/test.void')
    tc.assertEqual(fx.ringmaster.get_sgf_filename("0_000"), "0_000.sgf")
    tc.assertEqual(fx.ringmaster.get_sgf_pathname("0_000"),
                   "/nonexistent/ctl/test.games/0_000.sgf")

def test_stderr_settings(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "",
        }
    extra = "\n".join([
        "players['p1'] = Player('test')\n"
        ])
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals) + extra)
    job = fx.get_job()
    tc.assertEqual(job.player_b.stderr_pathname, "/nonexistent/ctl/test.log")
    tc.assertEqual(job.player_w.stderr_pathname, os.devnull)

def test_stderr_settings_nolog(tc):
    vals = {
        'cmdline1' : "",
        'cmdline2' : "",
        }
    extra = "\n".join([
        "players['p1'] = Player('test')\n"
        "stderr_to_log = False\n"
        ])
    fx = Ringmaster_fixture(tc, simple_ctl.substitute(vals) + extra)
    job = fx.get_job()
    tc.assertIsNone(job.player_b.stderr_pathname, None)
    tc.assertEqual(job.player_w.stderr_pathname, os.devnull)


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
        fx.messages('warnings'),
        [])
    tc.assertListEqual(
        fx.messages('screen_report'),
        ["p1 v p2 (3/400 games)\n"
         "board size: 9   komi: 7.5\n"
         "     wins\n"
         "p1      3 100.00%   (black)\n"
         "p2      0   0.00%   (white)"])

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
        fx.messages('warnings'),
        ["game 0_000 -- aborting game due to error:\n"
         "error starting subprocess for player p2:\n"
         "exec forced to fail",
         "halting run due to void games"])
    tc.assertListEqual(
        fx.messages('screen_report'),
        ["1 void games; see log file."])

