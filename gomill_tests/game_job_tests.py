"""Tests for game_jobs.py"""

from __future__ import with_statement

import os

from gomill import gtp_controller
from gomill import game_jobs
from gomill.job_manager import JobFailed

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


### Game_job proper

class Game_job_fixture(test_framework.Fixture):
    """Fixture setting up a Game_job.

    attributes:
      job -- game_jobs.Game_job

    """
    def __init__(self, tc):
        player_b = game_jobs.Player()
        player_b.code = 'one'
        player_b.cmd_args = ['test', 'id=one']
        player_w = game_jobs.Player()
        player_w.code = 'two'
        player_w.cmd_args = ['test', 'id=two']
        self.job = game_jobs.Game_job()
        self.job.game_id = 'gameid'
        self.job.player_b = player_b
        self.job.player_w = player_w
        self.job.board_size = 9
        self.job.komi = 7.5
        self.job.move_limit = 1000

def test_game_job(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    gj = Game_job_fixture(tc)
    gj.job.game_data = 'gamedata'
    result = gj.job.run()
    # Win by 18 on the board minus 7.5 komi
    tc.assertEqual(result.game_result.sgf_result, "B+10.5")
    tc.assertEqual(result.game_id, 'gameid')
    tc.assertEqual(result.game_data, 'gamedata')
    channel = fx.get_channel('one')
    tc.assertIsNone(channel.requested_stderr)
    tc.assertIsNone(channel.requested_cwd)
    tc.assertIsNone(channel.requested_env)

def test_game_job_exec_failure(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    gj = Game_job_fixture(tc)
    gj.job.player_w.cmd_args.append('fail=startup')
    with tc.assertRaises(JobFailed) as ar:
        gj.job.run()
    tc.assertEqual(str(ar.exception),
                   "aborting game due to error:\n"
                   "error starting subprocess for player two:\n"
                   "exec forced to fail")

def test_game_job_channel_error(tc):
    def fail_first_command(channel):
        channel.fail_next_command = True
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    fx.register_init_callback('fail_first_command', fail_first_command)
    gj = Game_job_fixture(tc)
    gj.job.player_w.cmd_args.append('init=fail_first_command')
    with tc.assertRaises(JobFailed) as ar:
        gj.job.run()
    tc.assertEqual(str(ar.exception),
                   "aborting game due to error:\n"
                   "transport error sending first command (protocol_version) "
                   "to player two:\n"
                   "forced failure for send_command_line")

def test_game_job_stderr_cwd_env(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    gj = Game_job_fixture(tc)
    gj.job.player_b.stderr_pathname = os.devnull
    gj.job.player_b.cwd = "/nonexistent_directory"
    gj.job.player_b.environ = {'GOMILL_TEST' : 'gomill'}
    result = gj.job.run()
    channel = fx.get_channel('one')
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, os.devnull)
    tc.assertEqual(channel.requested_cwd, "/nonexistent_directory")
    tc.assertEqual(channel.requested_env['GOMILL_TEST'], 'gomill')
    # Check environment was merged, not replaced
    tc.assertIn('PATH', channel.requested_env)

def test_game_job_claim(tc):
    def handle_genmove_ex(args):
        tc.assertIn('claim', args)
        return "claim"
    def register_genmove_ex(channel):
        channel.engine.add_command('gomill-genmove_ex', handle_genmove_ex)
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    fx.register_init_callback('genmove_ex', register_genmove_ex)
    gj = Game_job_fixture(tc)
    gj.job.player_b.cmd_args.append('init=genmove_ex')
    gj.job.player_w.cmd_args.append('init=genmove_ex')
    gj.job.player_w.allow_claim = True
    result = gj.job.run()
    tc.assertEqual(result.game_result.sgf_result, "W+C")


### check_player

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
    tc.assertIsNone(channel.requested_cwd)
    tc.assertIsNone(channel.requested_env)

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

def test_check_player_cwd(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    ck.player.cwd = "/"
    game_jobs.check_player(ck.check)
    channel = fx.get_channel('test')
    tc.assertEqual(channel.requested_cwd, "/")

def test_check_player_env(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    ck.player.environ = {'GOMILL_TEST' : 'gomill'}
    game_jobs.check_player(ck.check)
    channel = fx.get_channel('test')
    tc.assertEqual(channel.requested_env['GOMILL_TEST'], 'gomill')
    # Check environment was merged, not replaced
    tc.assertIn('PATH', channel.requested_env)

def test_check_player_exec_failure(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    ck = Player_check_fixture(tc)
    ck.player.cmd_args.append('fail=startup')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "error starting subprocess for test:\n"
                   "exec forced to fail")

def test_check_player_channel_error(tc):
    def fail_first_command(channel):
        channel.fail_next_command = True
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    fx.register_init_callback('fail_first_command', fail_first_command)
    ck = Player_check_fixture(tc)
    ck.player.cmd_args.append('init=fail_first_command')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "transport error sending first command (protocol_version) "
                   "to test:\n"
                   "forced failure for send_command_line")

def test_check_player_channel_error_on_close(tc):
    def fail_close(channel):
        channel.fail_close = True
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    fx.register_init_callback('fail_close', fail_close)
    ck = Player_check_fixture(tc)
    ck.player.cmd_args.append('init=fail_close')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(ck.check)
    tc.assertEqual(str(ar.exception),
                   "error closing test:\n"
                   "forced failure for close")

