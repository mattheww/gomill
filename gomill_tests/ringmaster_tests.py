"""Tests for ringmaster.py."""

import os
import re
from textwrap import dedent

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import ringmaster_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests.playoff_tests import fake_response

from gomill.ringmasters import RingmasterError

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

class Ringmaster_fixture(test_framework.Fixture):
    """Fixture setting up a Ringmaster with mock suprocesses.

    Instantiate with testcase, the text to be used as the contents of the
    control file, and a list of strings to be added (as a line each) to the end
    of the control file.

    attributes:
      ringmaster -- Testing_ringmaster
      msf        -- Mock_subprocess_fixture

    See Mock_subprocess_gtp_channel for an explanation of how player command
    lines are interpreted.

    """
    def __init__(self, tc, control_file_contents, extra_lines=[]):
        self.ringmaster = ringmaster_test_support.Testing_ringmaster(
            control_file_contents + "\n".join(extra_lines))
        self.ringmaster.set_display_mode('test')
        self.msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)

    def messages(self, channel):
        """Return messages sent to the specified channel."""
        return self.ringmaster.presenter.recent_messages(channel)

    def initialise_clean(self):
        """Initialise the ringmaster (with clean status)."""
        self.ringmaster.set_clean_status()
        self.ringmaster._open_files()
        self.ringmaster._initialise_presenter()
        self.ringmaster._initialise_terminal_reader()

    def initialise_with_state(self, ringmaster_status):
        """Initialise the ringmaster with specified status."""
        self.ringmaster.set_test_status(ringmaster_status)
        self.ringmaster.load_status()
        self.ringmaster._open_files()
        self.ringmaster._initialise_presenter()
        self.ringmaster._initialise_terminal_reader()

    def get_job(self):
        """Initialise the ringmaster, and call get_job() once."""
        self.initialise_clean()
        return self.ringmaster.get_job()

    def get_log(self):
        """Retrieve the log file contents with timestamps scrubbed out."""
        s = self.ringmaster.logfile.getvalue()
        s = re.sub(r"(?<= at )([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})",
                   "***", s)
        return s

    def get_history(self):
        """Retrieve the history file contents."""
        return self.ringmaster.historyfile.getvalue()

    def get_written_state(self):
        """Return the unpickled value written to the state file."""
        return self.ringmaster._written_status


playoff_ctl = """

competition_type = 'playoff'

description = 'gomill_tests playoff.'

players = {
    'p1'  : Player('test'),
    'p2'  : Player('test'),
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

"""

allplayall_ctl = """

competition_type = 'allplayall'

description = 'gomill_tests allplayall_ctl.'

players = {
    'p1'  : Player('test'),
    'p2'  : Player('test'),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = 'internal'

rounds = 8

competitors = ['p1', 'p2']

"""

mcts_ctl = """

competition_type = 'mc_tuner'

description = 'gomill_tests mc_tuner.'

players = {
    'p1'  : Player('test'),
    }

record_games = False
board_size = 9
komi = 7.5
candidate_colour = 'w'
opponent = 'p1'

exploration_coefficient = 0.45
initial_visits = 10
initial_wins = 5

parameters = [
    Parameter('foo',
              scale = LOG(0.01, 5.0),
              split = 8,
              format = 'I: %4.2f'),
    ]

def make_candidate(foo):
    return Player('candidate')

"""

def test_get_job(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p2'] = Player('test sing song')",
        ])
    job = fx.get_job()
    tc.assertEqual(job.game_id, "0_000")
    tc.assertEqual(job.game_data, ("0", 0))
    tc.assertEqual(job.board_size, 9)
    tc.assertEqual(job.komi, 7.5)
    tc.assertEqual(job.move_limit, 400)
    tc.assertEqual(job.handicap, None)
    tc.assertIs(job.handicap_is_free, False)
    tc.assertIs(job.use_internal_scorer, True)
    tc.assertEqual(job.sgf_game_name, 'test 0_000')
    tc.assertEqual(job.sgf_event, 'test')
    tc.assertIsNone(job.gtp_log_pathname)
    tc.assertIsNone(job.sgf_filename)
    tc.assertIsNone(job.sgf_dirname)
    tc.assertIsNone(job.void_sgf_dirname)
    tc.assertEqual(job.player_b.code, 'p1')
    tc.assertEqual(job.player_w.code, 'p2')
    tc.assertEqual(job.player_b.cmd_args, ['test'])
    tc.assertEqual(job.player_w.cmd_args, ['test', 'sing', 'song'])
    tc.assertDictEqual(job.player_b.gtp_aliases, {})
    tc.assertListEqual(job.player_b.startup_gtp_commands, [])
    tc.assertEqual(job.stderr_pathname, "/nonexistent/ctl/test.log")
    tc.assertIsNone(job.player_b.cwd)
    tc.assertIsNone(job.player_b.environ)
    tc.assertEqual(fx.ringmaster.games_in_progress, {'0_000': job})
    tc.assertEqual(fx.get_log(),
                   "starting game 0_000: p1 (b) vs p2 (w)\n")
    tc.assertEqual(fx.get_history(), "")


def test_settings(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "handicap = 9",
        "handicap_style = 'free'",
        "record_games = True",
        "scorer = 'players'"
        ])
    fx.ringmaster.enable_gtp_logging()
    job = fx.get_job()
    tc.assertEqual(job.game_id, "0_000")
    tc.assertEqual(job.handicap, 9)
    tc.assertIs(job.handicap_is_free, True)
    tc.assertIs(job.use_internal_scorer, False)
    tc.assertEqual(job.stderr_pathname, "/nonexistent/ctl/test.log")
    tc.assertEqual(job.gtp_log_pathname,
                   '/nonexistent/ctl/test.gtplogs/0_000.log')
    tc.assertEqual(job.sgf_filename, '0_000.sgf')
    tc.assertEqual(job.sgf_dirname, '/nonexistent/ctl/test.games')
    tc.assertEqual(job.void_sgf_dirname, '/nonexistent/ctl/test.void')
    tc.assertEqual(fx.ringmaster.get_sgf_filename("0_000"), "0_000.sgf")
    tc.assertEqual(fx.ringmaster.get_sgf_pathname("0_000"),
                   "/nonexistent/ctl/test.games/0_000.sgf")

def test_stderr_settings(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    job = fx.get_job()
    tc.assertEqual(job.stderr_pathname, "/nonexistent/ctl/test.log")
    tc.assertIs(job.player_b.discard_stderr, False)
    tc.assertIs(job.player_w.discard_stderr, True)

def test_stderr_settings_nolog(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p2'] = Player('test', discard_stderr=True)",
        "stderr_to_log = False",
        ])
    job = fx.get_job()
    tc.assertIs(job.stderr_pathname, None)
    tc.assertIs(job.player_b.discard_stderr, False)
    tc.assertIs(job.player_w.discard_stderr, True)


def test_get_tournament_results(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl)
    tc.assertRaisesRegexp(RingmasterError, "^status is not loaded$",
                          fx.ringmaster.get_tournament_results)
    fx.initialise_clean()
    tr = fx.ringmaster.get_tournament_results()
    tc.assertEqual(tr.get_matchup_ids(), ['0'])

    fx2 = Ringmaster_fixture(tc, mcts_ctl)
    fx2.initialise_clean()
    tc.assertRaisesRegexp(RingmasterError, "^competition is not a tournament$",
                          fx2.ringmaster.get_tournament_results)

def test_process_response(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl)
    job = fx.get_job()
    tc.assertEqual(fx.ringmaster.games_in_progress, {'0_000': job})
    tc.assertEqual(
        fx.ringmaster.get_tournament_results().get_matchup_results('0'), [])
    response = fake_response(job, 'w')
    response.warnings = ['warningtest']
    response.log_entries = ['logtest']
    fx.ringmaster.process_response(response)
    tc.assertEqual(fx.ringmaster.games_in_progress, {})
    tc.assertListEqual(
        fx.messages('warnings'),
        ["warningtest"])
    tc.assertListEqual(
        fx.messages('results'),
        ["game 0_000: p2 beat p1 W+1.5"])
    tc.assertEqual(
        fx.ringmaster.get_tournament_results().get_matchup_results('0'),
        [response.game_result])
    tc.assertEqual(fx.get_log(),
                   "starting game 0_000: p1 (b) vs p2 (w)\n"
                   "response from game 0_000\n"
                   "warningtest\n"
                   "logtest\n")
    tc.assertEqual(fx.get_history(), "")


def test_check_players(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl)
    tc.assertTrue(fx.ringmaster.check_players(discard_stderr=True))

def test_run(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    fx.initialise_clean()
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
    tc.assertMultiLineEqual(
        fx.get_log(),
        "run started at *** with max_games 3\n"
        "starting game 0_000: p1 (b) vs p2 (w)\n"
        "response from game 0_000\n"
        "starting game 0_001: p1 (b) vs p2 (w)\n"
        "response from game 0_001\n"
        "starting game 0_002: p1 (b) vs p2 (w)\n"
        "response from game 0_002\n"
        "halting competition: max-games reached for this run\n"
        "run finished at ***\n"
        )
    tc.assertMultiLineEqual(
        fx.get_history(),
        "  0_000 p1 beat p2 B+10.5\n"
        "  0_001 p1 beat p2 B+10.5\n"
        "  0_002 p1 beat p2 B+10.5\n")

def test_run_allplayall(tc):
    fx = Ringmaster_fixture(tc, allplayall_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    fx.initialise_clean()
    fx.ringmaster.run(max_games=3)
    tc.assertListEqual(
        fx.messages('warnings'),
        [])
    tc.assertListEqual(
        fx.messages('screen_report'),
        [dedent("""\
        3/8 games played

              A   B
        A p1     2-1
        B p2 1-2""")])
    tc.assertMultiLineEqual(
        fx.get_log(),
        "run started at *** with max_games 3\n"
        "starting game AvB_0: p1 (b) vs p2 (w)\n"
        "response from game AvB_0\n"
        "starting game AvB_1: p2 (b) vs p1 (w)\n"
        "response from game AvB_1\n"
        "starting game AvB_2: p1 (b) vs p2 (w)\n"
        "response from game AvB_2\n"
        "halting competition: max-games reached for this run\n"
        "run finished at ***\n"
        )
    tc.assertMultiLineEqual(
        fx.get_history(),
        "  AvB_0 p1 beat p2 B+10.5\n"
        "  AvB_1 p2 beat p1 B+10.5\n"
        "  AvB_2 p1 beat p2 B+10.5\n")

def test_check_players_fail(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p2'] = Player('test fail=startup')"
        ])
    tc.assertFalse(fx.ringmaster.check_players(discard_stderr=True))

def test_run_fail(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test fail=startup', discard_stderr=True)",
        ])
    fx.initialise_clean()
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
    tc.assertMultiLineEqual(
        fx.get_log(),
        "run started at *** with max_games None\n"
        "starting game 0_000: p1 (b) vs p2 (w)\n"
        "game 0_000 -- aborting game due to error:\n"
        "error starting subprocess for player p2:\n"
        "exec forced to fail\n"
        "halting competition: too many void games\n"
        "run finished at ***\n")
    tc.assertMultiLineEqual(fx.get_history(), "")

def test_run_with_late_errors(tc):
    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test init=fail_close', discard_stderr=True)",
        ])
    def fail_close(channel):
        channel.fail_close = True
    fx.msf.register_init_callback('fail_close', fail_close)
    fx.initialise_clean()
    fx.ringmaster.run(max_games=2)
    tc.assertListEqual(fx.messages('warnings'), [])
    tc.assertMultiLineEqual(
        fx.get_log(),
        "run started at *** with max_games 2\n"
        "starting game 0_000: p1 (b) vs p2 (w)\n"
        "response from game 0_000\n"
        "error closing player p2:\n"
        "forced failure for close\n"
        "starting game 0_001: p1 (b) vs p2 (w)\n"
        "response from game 0_001\n"
        "error closing player p2:\n"
        "forced failure for close\n"
        "halting competition: max-games reached for this run\n"
        "run finished at ***\n")
    tc.assertMultiLineEqual(
        fx.get_history(),
        "  0_000 p1 beat p2 B+10.5\n"
        "  0_001 p1 beat p2 B+10.5\n")

def test_status_roundtrip(tc):
    fx1 = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    fx1.initialise_clean()
    fx1.ringmaster.run(max_games=2)
    tc.assertListEqual(
        fx1.messages('warnings'),
        [])
    state = fx1.get_written_state()

    fx2 = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    fx2.initialise_with_state(state)
    fx2.ringmaster.run(max_games=1)
    tc.assertListEqual(
        fx2.messages('warnings'),
        [])
    tc.assertListEqual(
        fx2.messages('screen_report'),
        ["p1 v p2 (3/400 games)\n"
         "board size: 9   komi: 7.5\n"
         "     wins\n"
         "p1      3 100.00%   (black)\n"
         "p2      0   0.00%   (white)"])

def test_status(tc):
    # Construct suitable competition status
    fx1 = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    sfv = fx1.ringmaster.status_format_version
    fx1.initialise_clean()
    fx1.ringmaster.run(max_games=2)
    competition_status = fx1.ringmaster.competition.get_status()
    tc.assertListEqual(
        fx1.messages('warnings'),
        [])
    status = {
        'void_game_count' : 0,
        'comp_vn'         : fx1.ringmaster.competition.status_format_version,
        'comp'            : competition_status,
        }

    fx = Ringmaster_fixture(tc, playoff_ctl, [
        "players['p1'] = Player('test', discard_stderr=True)",
        "players['p2'] = Player('test', discard_stderr=True)",
        ])
    fx.initialise_with_state((sfv, status.copy()))
    fx.ringmaster.run(max_games=1)
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

    fx.ringmaster.set_test_status((-1, status.copy()))
    tc.assertRaisesRegexp(
        RingmasterError,
        "incompatible status file",
        fx.ringmaster.load_status)

    bad_status = status.copy()
    del bad_status['void_game_count']
    fx.ringmaster.set_test_status((sfv, bad_status))
    tc.assertRaisesRegexp(
        RingmasterError,
        "incompatible status file: missing 'void_game_count'",
        fx.ringmaster.load_status)

    bad_competition_status = competition_status.copy()
    del bad_competition_status['results']
    bad_status_2 = status.copy()
    bad_status_2['comp'] = bad_competition_status
    fx.ringmaster.set_test_status((sfv, bad_status_2))
    tc.assertRaisesRegexp(
        RingmasterError,
        "error loading competition state: missing 'results'",
        fx.ringmaster.load_status)

    bad_competition_status_2 = competition_status.copy()
    bad_competition_status_2['scheduler'] = None
    bad_status_3 = status.copy()
    bad_status_3['comp'] = bad_competition_status_2
    fx.ringmaster.set_test_status((sfv, bad_status_3))
    tc.assertRaisesRegexp(
        RingmasterError,
        "error loading competition state:\n"
        "AttributeError: 'NoneType' object has no attribute 'set_groups'",
        fx.ringmaster.load_status)

    bad_status_4 = status.copy()
    bad_status_4['comp_vn'] = -1
    fx.ringmaster.set_test_status((sfv, bad_status_4))
    tc.assertRaisesRegexp(
        RingmasterError,
        "incompatible status file",
        fx.ringmaster.load_status)
