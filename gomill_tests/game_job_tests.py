"""Tests for game_jobs.py"""

from gomill import gtp_controller
from gomill import game_jobs

from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_check_player(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)

    player = game_jobs.Player()
    player.code = 'test'
    player.cmd_args = ['test']

    check = game_jobs.Player_check()
    check.player = player
    check.board_size = 9
    check.komi = 7.0

    game_jobs.check_player(check)

def test_check_player_boardsize_fails(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    engine = gtp_engine_fixtures.get_test_engine()
    fx.register_engine('no_boardsize', engine)

    player = game_jobs.Player()
    player.code = 'test'
    player.cmd_args = ['no_boardsize']

    check = game_jobs.Player_check()
    check.player = player
    check.board_size = 9
    check.komi = 7.0

    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'boardsize 9' to test:\n"
                   "unknown command")

def test_check_player_startup_gtp_commands(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)

    player = game_jobs.Player()
    player.code = 'test'
    player.cmd_args = ['test']
    player.startup_gtp_commands = [('list_commands', []),
                                   ('nonexistent', ['command'])]
    check = game_jobs.Player_check()
    check.player = player
    check.board_size = 9
    check.komi = 7.0

    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'nonexistent command' to test:\n"
                   "unknown command")

