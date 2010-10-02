"""Tests for game_jobs.py"""

import os

from gomill import gtp_controller
from gomill import game_jobs

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Player_check_fixture(test_framework.Fixture):
    """Fixture setting up a Player_check.

    attributes:
      player -- game_jobs.Player
      check  -- game_jobs.Player_check

    """
    def __init__(self, tc):
        self.player = game_jobs.Player()
        self.player.code = 'test'
        self.player.cmd_args = ['test', 'id=test']
        self.check = game_jobs.Player_check()
        self.check.player = self.player
        self.check.board_size = 9
        self.check.komi = 7.0

def test_check_player(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    game_jobs.check_player(ck.check)
    channel = fx.get_channel('test')
    tc.assertIsNone(channel.requested_stderr)

def test_check_player_discard_stderr(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    game_jobs.check_player(ck.check, discard_stderr=True)
    channel = fx.get_channel('test')
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, os.devnull)

def test_check_player_boardsize_fails(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    engine = gtp_engine_fixtures.get_test_engine()
    fx.register_engine('no_boardsize', engine)
    ck = Player_check_fixture(tc)
    ck.player.cmd_args.append('engine=no_boardsize')

    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'boardsize 9' to test:\n"
                   "unknown command")

def test_check_player_startup_gtp_commands(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    ck.player.startup_gtp_commands = [('list_commands', []),
                                       ('nonexistent', ['command'])]
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'nonexistent command' to test:\n"
                   "unknown command")

def test_check_player_nonexistent_cwd(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    ck.player.cwd = "/nonexistent/directory"
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "bad working directory: /nonexistent/directory")

