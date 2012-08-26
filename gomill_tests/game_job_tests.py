"""Tests for game_jobs.py"""

from __future__ import with_statement

import os
from textwrap import dedent

from gomill import gtp_controller
from gomill import game_jobs
from gomill.job_manager import JobFailed

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


### Game_job proper

class Test_game_job(game_jobs.Game_job):
    """Variant of Game_job that doesn't write sgf files.

    Additional attributes:
     _sgf_pathname_written -- pathname sgf file would have been written to
     _sgf_written          -- contents that would have been written
     _mkdir_pathname       -- directory pathname that would have been created

    """
    def __init__(self, *args, **kwargs):
        game_jobs.Game_job.__init__(self, *args, **kwargs)
        self._sgf_pathname_written = None
        self._sgf_written = None
        self._mkdir_pathname = None

    def _write_sgf(self, pathname, sgf_string):
        self._sgf_pathname_written = pathname
        self._sgf_written = sgf_string

    def _ensure_dir(self, pathname):
        self._mkdir_pathname = pathname

    def _get_sgf_written(self):
        """Return the 'scrubbed' sgf contents."""
        if self._sgf_written is None:
            return None
        return gomill_test_support.scrub_sgf(self._sgf_written)

class Game_job_fixture(gtp_engine_fixtures.Mock_subprocess_fixture):
    """Fixture setting up a Game_job.

    Acts as a Mock_subprocess_fixture.

    attributes:
      job -- game_jobs.Game_job (in fact, a Test_game_job)

    """
    def __init__(self, tc):
        gtp_engine_fixtures.Mock_subprocess_fixture.__init__(self, tc)
        player_b = game_jobs.Player()
        player_b.code = 'one'
        player_b.cmd_args = ['testb', 'id=one']
        player_w = game_jobs.Player()
        player_w.code = 'two'
        player_w.cmd_args = ['testw', 'id=two']
        self.job = Test_game_job()
        self.job.game_id = 'gameid'
        self.job.player_b = player_b
        self.job.player_w = player_w
        self.job.board_size = 9
        self.job.komi = 7.5
        self.job.move_limit = 1000
        self.job.sgf_dirname = "/sgf/test.games"
        self.job.void_sgf_dirname = "/sgf/test.void"
        self.job.sgf_filename = "gjtest.sgf"
        self._ctr = 0
        self._players = {'b' : player_b, 'w' : player_w}

    def init_player(self, colour, fn):
        """Set up an initialisation function for a player.

        fn -- function taking a Mock_subprocess_gtp_channel parameter

        """
        init_code = str(self._ctr)
        self._ctr += 1
        self._players[colour].cmd_args.append("init=%s" % init_code)
        self.register_init_callback(init_code, fn)

    def add_handler(self, colour, command, handler):
        """Add a GTP handler to a player.

        command -- GTP command name
        handler -- normal Gtp_engine_protocol handler function

        """
        def register_handler(channel):
            channel.engine.add_command(command, handler)
        self.init_player(colour, register_handler)

    def force_error(self, colour, command):
        """Force the specified GTP command to report failure.

        command -- GTP command name

        """
        def register(channel):
            channel.engine.force_error(command)
        self.init_player(colour, register)

    def force_fatal_error(self, colour, command):
        """Force the specified GTP command to report failure and exit.

        command -- GTP command name

        """
        def register(channel):
            channel.engine.force_fatal_error(command)
        self.init_player(colour, register)

    def sgf_moves_and_comments(self):
        return gomill_test_support.sgf_moves_and_comments_from_string(
            self.job._get_sgf_written())


def test_player_copy(tc):
    fx = Game_job_fixture(tc)
    p1 = fx.job.player_b
    p2 = p1.copy("clone")
    tc.assertEqual(p2.code, "clone")
    tc.assertEqual(p2.cmd_args, ['testb', 'id=one'])
    tc.assertIsNot(p1.cmd_args, p2.cmd_args)

def test_game_job(tc):
    fx = Game_job_fixture(tc)
    fx.job.game_data = 'gamedata'
    fx.job.sgf_game_name = "gjt 0_000"
    fx.job.sgf_event = "game_job_tests"
    fx.job.sgf_note = "test sgf_note\non two lines"
    result = fx.job.run()
    # Win by 18 on the board minus 7.5 komi
    tc.assertEqual(result.game_result.sgf_result, "B+10.5")
    tc.assertEqual(result.game_id, 'gameid')
    tc.assertEqual(result.game_result.game_id, 'gameid')
    tc.assertEqual(result.game_data, 'gamedata')
    tc.assertEqual(result.warnings, [])
    tc.assertEqual(result.log_entries, [])
    tc.assertIsNone(result.engine_descriptions['b'].get_short_description())
    tc.assertIsNone(result.engine_descriptions['w'].get_short_description())
    channel = fx.get_channel('one')
    tc.assertFalse(channel.is_nonblocking)
    tc.assertIsNone(channel.requested_stderr)
    tc.assertIsNone(channel.requested_cwd)
    tc.assertIn('PATH', channel.requested_env)
    tc.assertEqual(channel.requested_env['GOMILL_GAME_ID'], 'gameid')
    tc.assertNotIn('GOMILL_SLOT', channel.requested_env)
    tc.assertTrue(channel.is_closed)
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')
    tc.assertIsNone(fx.job._mkdir_pathname)
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Event: game_job_tests
    Game id gameid
    Date ***
    Result one beat two B+10.5
    test sgf_note
    on two lines
    one cpu time: 546.20s
    two cpu time: 567.20s
    Black one
    White two]
    CA[UTF-8]DT[***]EV[game_job_tests]GM[1]GN[gjt 0_000]KM[7.5]PB[one]
    PW[two]RE[B+10.5]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];
    W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];
    C[one beat two B+10.5]W[tt])
    """))

def test_game_job_duplicate_player_codes(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_w.code = "one"
    tc.assertRaisesRegexp(
        JobFailed, "error creating game: player codes must be distinct",
        fx.job.run)

def test_game_job_no_sgf(tc):
    fx = Game_job_fixture(tc)
    fx.job.sgf_dirname = None
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+10.5")
    tc.assertIsNone(fx.job._sgf_pathname_written)

def test_game_job_forfeit(tc):
    fx = Game_job_fixture(tc)
    fx.force_error('w', 'genmove')
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+F")
    tc.assertEqual(
        result.game_result.detail,
        "forfeit by two: failure response from 'genmove w' to player two:\n"
        "handler forced to fail")
    tc.assertEqual(
        result.warnings,
        ["forfeit by two: failure response from 'genmove w' to player two:\n"
        "handler forced to fail"])
    tc.assertEqual(result.log_entries, [])
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')

def test_game_job_forfeit_and_quit(tc):
    fx = Game_job_fixture(tc)
    fx.force_fatal_error('w', 'genmove')
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+F")
    tc.assertEqual(
        result.game_result.detail,
        "forfeit by two: failure response from 'genmove w' to player two:\n"
        "handler forced to fail and exit")
    tc.assertEqual(
        result.warnings,
        ["forfeit by two: failure response from 'genmove w' to player two:\n"
         "handler forced to fail and exit"])
    tc.assertEqual(
        result.log_entries,
        ["error sending 'known_command gomill-explain_last_move' to player two:\n"
         "engine has closed the command channel"])
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')

def test_game_job_exec_failure(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_w.cmd_args.append('fail=startup')
    with tc.assertRaises(JobFailed) as ar:
        fx.job.run()
    tc.assertEqual(str(ar.exception),
                   "aborting game due to error:\n"
                   "error starting subprocess for player two:\n"
                   "exec forced to fail")
    # No void sgf file unless at least one move was played
    tc.assertIsNone(fx.job._sgf_pathname_written)

def test_game_job_channel_error(tc):
    def fail_first_genmove(channel):
        channel.fail_command = 'genmove'
    fx = Game_job_fixture(tc)
    fx.init_player('w', fail_first_genmove)
    with tc.assertRaises(JobFailed) as ar:
        fx.job.run()
    tc.assertEqual(str(ar.exception),
                   "aborting game due to error:\n"
                   "transport error sending 'genmove w' to player two:\n"
                   "forced failure for send_command_line")
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.void/gjtest.sgf')
    tc.assertEqual(fx.job._mkdir_pathname, '/sgf/test.void')
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Black one
    White two]CA[UTF-8]
    DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[Void]SZ[9];B[ei]
    C[aborting game due to error:
    transport error sending 'genmove w' to player two:
    forced failure for send_command_line]
    )
    """))

def test_game_job_late_errors(tc):
    def fail_close(channel):
        channel.fail_close = True
    fx = Game_job_fixture(tc)
    fx.init_player('w', fail_close)
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+10.5")
    tc.assertEqual(result.warnings, [])
    tc.assertEqual(result.log_entries,
                   ["error closing player two:\nforced failure for close"])
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Result one beat two B+10.5
    one cpu time: 546.20s
    Black one
    White two]
    CA[UTF-8]DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[B+10.5]SZ[9];
    B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];
    W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];
    C[one beat two B+10.5

    error closing player two:
    forced failure for close]W[tt]
    )
    """))

def test_game_job_late_error_from_void_game(tc):
    def fail_genmove_and_close(channel):
        channel.fail_command = 'genmove'
        channel.fail_close = True
    fx = Game_job_fixture(tc)
    fx.init_player('w', fail_genmove_and_close)
    with tc.assertRaises(JobFailed) as ar:
        fx.job.run()
    tc.assertMultiLineEqual(
        str(ar.exception),
        "aborting game due to error:\n"
        "transport error sending 'genmove w' to player two:\n"
        "forced failure for send_command_line\n"
        "also:\n"
        "error closing player two:\n"
        "forced failure for close")
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.void/gjtest.sgf')
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Black one
    White two]CA[UTF-8]
    DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[Void]SZ[9];B[ei]
    C[aborting game due to error:
    transport error sending 'genmove w' to player two:
    forced failure for send_command_line

    error closing player two:
    forced failure for close]
    )
    """))

def test_game_job_cwd_env(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_b.cwd = "/nonexistent_directory"
    fx.job.player_b.environ = {'GOMILL_TEST' : 'gomill'}
    result = fx.job.run()
    channel = fx.get_channel('one')
    tc.assertFalse(channel.is_nonblocking)
    tc.assertIsNone(channel.requested_stderr)
    tc.assertEqual(channel.requested_cwd, "/nonexistent_directory")
    tc.assertEqual(channel.requested_env['GOMILL_TEST'], 'gomill')
    # Check environment was merged, not replaced
    tc.assertEqual(channel.requested_env['GOMILL_GAME_ID'], 'gameid')
    tc.assertIn('PATH', channel.requested_env)
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')

def test_game_job_worker_id(tc):
    fx = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    gj = Game_job_fixture(tc)
    result = gj.job.run(0)
    channel = fx.get_channel('one')
    tc.assertEqual(channel.requested_env['GOMILL_GAME_ID'], 'gameid')
    tc.assertEqual(channel.requested_env['GOMILL_SLOT'], '0')

def test_game_job_stderr_discarded(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_b.stderr_to = 'discard'
    result = fx.job.run()
    channel = fx.get_channel('one')
    tc.assertFalse(channel.is_nonblocking)
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, os.devnull)

def test_game_job_stderr_captured(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_b.stderr_to = 'capture'
    result = fx.job.run()
    channel1 = fx.get_channel('one')
    tc.assertTrue(channel1.is_nonblocking)
    tc.assertEqual(channel1.requested_stderr, "capture")
    channel2 = fx.get_channel('two')
    tc.assertTrue(channel2.is_nonblocking)
    tc.assertIsNone(channel2.requested_stderr)

def test_game_job_stderr_set(tc):
    fx = Game_job_fixture(tc)
    fx.job.stderr_pathname = "/dev/full"
    result = fx.job.run()
    channel = fx.get_channel('one')
    tc.assertFalse(channel.is_nonblocking)
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, "/dev/full")

def test_game_job_stderr_set_and_discarded(tc):
    fx = Game_job_fixture(tc)
    fx.job.stderr_pathname = "/dev/full"
    fx.job.player_b.stderr_to = 'discard'
    result = fx.job.run()
    channel = fx.get_channel('one')
    tc.assertFalse(channel.is_nonblocking)
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, os.devnull)

def test_game_job_stderr_set_and_captured(tc):
    fx = Game_job_fixture(tc)
    fx.job.stderr_pathname = "/dev/full"
    fx.job.player_b.stderr_to = 'capture'
    result = fx.job.run()
    channel1 = fx.get_channel('one')
    tc.assertTrue(channel1.is_nonblocking)
    tc.assertEqual(channel1.requested_stderr, "capture")
    channel2 = fx.get_channel('two')
    tc.assertTrue(channel2.is_nonblocking)
    tc.assertIsInstance(channel2.requested_stderr, file)
    tc.assertEqual(channel2.requested_stderr.name, "/dev/full")

def test_game_job_gtp_aliases(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_w.gtp_aliases = {'genmove': 'fail'}
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+F")

def test_game_job_claim(tc):
    def handle_genmove_ex(args):
        tc.assertIn('claim', args)
        return "claim"
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'gomill-genmove_ex', handle_genmove_ex)
    fx.add_handler('w', 'gomill-genmove_ex', handle_genmove_ex)
    fx.job.player_w.allow_claim = True
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "W+")
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')

def test_game_job_handicap(tc):
    def handle_fixed_handicap(args):
        return "D4 K10 D10"
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'fixed_handicap', handle_fixed_handicap)
    fx.add_handler('w', 'fixed_handicap', handle_fixed_handicap)
    fx.job.board_size = 13
    fx.job.handicap = 3
    fx.job.handicap_is_free = False
    fx.job.internal_scorer_handicap_compensation = 'full'
    result = fx.job.run()
    # area score 53, less 7.5 komi, less 3 handicap compensation
    tc.assertEqual(result.game_result.sgf_result, "B+42.5")

def test_game_job_zero_move_game(tc):
    fx = Game_job_fixture(tc)
    fx.force_error('b', 'genmove')
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "W+F")
    tc.assertEqual(result.log_entries, [])
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.games/gjtest.sgf')
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\n"
          "one cpu time: 546.20s\ntwo cpu time: 567.20s\n"
          "Black one\nWhite two\n\n"
          "two beat one W+F "
          "(forfeit by one: failure response from 'genmove b' to player one:\n"
          "handler forced to fail)",
        ])

def test_game_job_move_limit(tc):
    fx = Game_job_fixture(tc)
    fx.job.move_limit = 4
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "Void")
    tc.assertEqual(result.game_result.detail, "hit move limit")
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Result one vs two Void (hit move limit)
    one cpu time: 546.20s
    two cpu time: 567.20s
    Black one
    White two]
    CA[UTF-8]DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[Void]SZ[9];B[ei];
    W[gi];B[eh];C[one vs two Void (hit move limit)]W[gh])
    """))

def test_game_job_startup_gtp_commands(tc):
    clog = []
    def handle_dummy1(args):
        clog.append(("dummy1", args))
    def handle_dummy2(args):
        clog.append(("dummy2", args))
        return "ignored result"
    def handle_clear_board(args):
        clog.append(("clear_board", args))
    fx = Game_job_fixture(tc)
    fx.add_handler('w', 'dummy1', handle_dummy1)
    fx.add_handler('w', 'dummy2', handle_dummy2)
    fx.add_handler('w', 'clear_board', handle_clear_board)
    fx.job.player_w.startup_gtp_commands = [('dummy1', []),
                                            ('dummy2', ['arg'])]
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+10.5")
    tc.assertEqual(clog,
                   [('dummy1', []),
                    ('dummy2', ['arg']),
                    ('clear_board', [])])

def test_game_job_startup_gtp_commands_error(tc):
    fx = Game_job_fixture(tc)
    fx.force_error('w', 'failplease')
    fx.job.player_w.startup_gtp_commands = [('list_commands', []),
                                            ('failplease', [])]
    with tc.assertRaises(JobFailed) as ar:
        fx.job.run()
    tc.assertEqual(
        str(ar.exception),
        "aborting game due to error:\n"
        "failure response from 'failplease' to player two:\n"
        "handler forced to fail")
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)

def test_game_job_players_score(tc):
    clog = []
    def handle_final_score_b(args):
        clog.append("final_score_b")
        return "B+33"
    def handle_final_score_w(args):
        clog.append("final_score_w")
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'final_score', handle_final_score_b)
    fx.add_handler('w', 'final_score', handle_final_score_w)
    fx.job.use_internal_scorer = False
    fx.job.player_w.is_reliable_scorer = False
    result = fx.job.run()
    tc.assertEqual(result.game_result.sgf_result, "B+33")
    tc.assertEqual(clog, ["final_score_b"])

def test_game_job_cpu_time(tc):
    def handle_cpu_time(args):
        return "99.5"
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'gomill-cpu_time', handle_cpu_time)
    result = fx.job.run()
    tc.assertEqual(result.game_result.cpu_times, {'one': 99.5, 'two': 567.2})
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Result one beat two B+10.5
    one cpu time: 99.50s
    two cpu time: 567.20s
    Black one
    White two]
    CA[UTF-8]DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[B+10.5]SZ[9];
    B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];
    W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+10.5]W[tt])
    """))

def test_game_job_cpu_time_fail(tc):
    def handle_cpu_time_bad(args):
        return "nonsense"
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'gomill-cpu_time', handle_cpu_time_bad)
    result = fx.job.run()
    tc.assertEqual(result.game_result.cpu_times, {'one': None, 'two': 567.2})
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Result one beat two B+10.5
    two cpu time: 567.20s
    Black one
    White two]
    CA[UTF-8]DT[***]GM[1]GN[gameid]KM[7.5]PB[one]PW[two]RE[B+10.5]SZ[9];
    B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];
    W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+10.5]W[tt])
    """))

def test_game_job_player_descriptions(tc):
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'name', lambda args: "blackname")
    fx.add_handler('w', 'gomill-describe_engine', lambda args: "foo\nbar")
    result = fx.job.run()
    tc.assertEqual(result.engine_descriptions['b'].name, "blackname")
    tc.assertEqual(result.engine_descriptions['w'].description, "foo\nbar")
    tc.assertMultiLineEqual(fx.job._get_sgf_written(), dedent("""\
    (;FF[4]AP[gomill:VER]
    C[Game id gameid
    Date ***
    Result one beat two B+10.5
    one cpu time: 546.20s
    two cpu time: 567.20s
    Black one blackname
    White two foo
    bar]
    CA[UTF-8]DT[***]GM[1]GN[gameid]KM[7.5]PB[blackname]PW[two]RE[B+10.5]
    SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];
    B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+10.5]W[tt])
    """))

def test_game_job_explain_last_move(tc):
    counter = [0]
    def handle_explain_last_move(args):
        counter[0] += 1
        return "EX%d" % counter[0]
    fx = Game_job_fixture(tc)
    fx.add_handler('w', 'gomill-explain_last_move', handle_explain_last_move)
    result = fx.job.run()
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\nResult one beat two B+10.5\n"
          "one cpu time: 546.20s\ntwo cpu time: 567.20s\n"
          "Black one\nWhite two",
        "b E1: --",
        "w G1: EX1",
        "b E2: --",
        "w G2: EX2",
        "b E3: --",
        "w G3: EX3",
        "b E4: --",
        "w G4: EX4",
        "b E5: --",
        "w G5: EX5",
        "b E6: --",
        "w G6: EX6",
        "b E7: --",
        "w G7: EX7",
        "b E8: --",
        "w G8: EX8",
        "b E9: --",
        "w G9: EX9",
        "b pass: --",
        "w pass: EX10\n\none beat two B+10.5",
        ])

def test_game_job_explain_final_move(tc):
    counter = [0]
    def handle_explain_last_move(args):
        counter[0] += 1
        return "EX%d" % counter[0]
    fx = Game_job_fixture(tc)
    fx.add_handler('w', 'genmove', lambda args:"resign")
    fx.add_handler('w', 'gomill-explain_last_move', handle_explain_last_move)
    fx.add_handler('b', 'gomill-explain_last_move', handle_explain_last_move)
    result = fx.job.run()
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\n"
          "Result one beat two B+R\n"
          "one cpu time: 546.20s\ntwo cpu time: 567.20s\n"
          "Black one\nWhite two",
        "b E1: EX1\n\n"
          "final message from w: <<<\nEX2\n>>>\n\n"
          "one beat two B+R",
        ])

def test_game_job_explain_final_move_zero_move_game(tc):
    counter = [0]
    def handle_explain_last_move(args):
        counter[0] += 1
        return "EX%d" % counter[0]
    fx = Game_job_fixture(tc)
    fx.add_handler('b', 'genmove', lambda args:"resign")
    fx.add_handler('b', 'gomill-explain_last_move', handle_explain_last_move)
    result = fx.job.run()
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\n"
          "one cpu time: 546.20s\ntwo cpu time: 567.20s\n"
          "Black one\nWhite two\n\n"
          "final message from b: <<<\nEX1\n>>>\n\n"
          "two beat one W+R",
        ])

def test_game_job_captured_stderr(tc):
    def make_chatty(channel):
        channel.chatty = True
    fx = Game_job_fixture(tc)
    fx.job.player_b.stderr_to = 'capture'
    fx.init_player('w', make_chatty)
    result = fx.job.run()
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\nResult one beat two B+10.5\n"
          "one cpu time: 546.20s\ntwo cpu time: 567.20s\n"
          "Black one\nWhite two",
        "b E1: --",
        "w G1: asked for move: 1",
        "b E2: --",
        "w G2: asked for move: 2",
        "b E3: --",
        "w G3: asked for move: 3",
        "b E4: --",
        "w G4: asked for move: 4",
        "b E5: --",
        "w G5: asked for move: 5",
        "b E6: --",
        "w G6: asked for move: 6",
        "b E7: --",
        "w G7: asked for move: 7",
        "b E8: --",
        "w G8: asked for move: 8",
        "b E9: --",
        "w G9: asked for move: 9",
        "b pass: --",
        "w pass: asked for move: 10\n\none beat two B+10.5\n\n"
          "exit message from w: <<<\nclosing\n>>>"
        ])

def test_game_job_captured_stderr_from_early_failure(tc):
    fx = Game_job_fixture(tc)
    fx.job.player_w.stderr_to = 'capture'
    fx.job.player_w.cmd_args.append('fail=usage')
    with tc.assertRaises(JobFailed) as ar:
        fx.job.run()
    tc.assertEqual(
        str(ar.exception),
        "aborting game due to error:\n"
        "error sending first command (protocol_version) to player two:\n"
        "engine has closed the command channel")
    tc.assertEqual(fx.job._sgf_pathname_written, '/sgf/test.void/gjtest.sgf')
    tc.assertEqual(fx.job._mkdir_pathname, '/sgf/test.void')
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: "
          "Game id gameid\nDate ***\n"
          "Black one\nWhite two\n\n"
          "exit message from w: <<<\nUsage: message\n\nclosing\n>>>\n\n"
          "aborting game due to error:\n"
          "error sending first command (protocol_version) to player two:\n"
          "engine has closed the command channel"
        ])

def test_game_job_unhandled_error(tc):
    # Check that we close the channels if there's an unhandled error
    fx = Game_job_fixture(tc)
    fx.job.handicap = 2.5
    with tc.assertRaises(TypeError):
        fx.job.run()
    tc.assertTrue(fx.get_channel('one').is_closed)
    tc.assertTrue(fx.get_channel('two').is_closed)


### check_player

class Player_check_fixture(gtp_engine_fixtures.Mock_subprocess_fixture):
    """Fixture setting up a Player_check.

    Acts as a Mock_subprocess_fixture.

    attributes:
      player -- game_jobs.Player
      check  -- game_jobs.Player_check

    """
    def __init__(self, tc):
        gtp_engine_fixtures.Mock_subprocess_fixture.__init__(self, tc)
        self.player = game_jobs.Player()
        self.player.code = 'test'
        self.player.cmd_args = ['test', 'id=test']
        self.check = game_jobs.Player_check()
        self.check.player = self.player
        self.check.board_size = 9
        self.check.komi = 7.0

def test_check_player(tc):
    fx = Player_check_fixture(tc)
    tc.assertEqual(game_jobs.check_player(fx.check), [])
    channel = fx.get_channel('test')
    tc.assertIsNone(channel.requested_stderr)
    tc.assertIsNone(channel.requested_cwd)
    tc.assertIn('PATH', channel.requested_env)
    tc.assertEqual(channel.requested_env['GOMILL_GAME_ID'], 'startup-check')

def test_check_player_discard_stderr(tc):
    fx = Player_check_fixture(tc)
    tc.assertEqual(game_jobs.check_player(fx.check, discard_stderr=True), [])
    channel = fx.get_channel('test')
    tc.assertIsInstance(channel.requested_stderr, file)
    tc.assertEqual(channel.requested_stderr.name, os.devnull)

def test_check_player_boardsize_fails(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    fx = Player_check_fixture(tc)
    fx.register_engine('no_boardsize', engine)
    fx.player.cmd_args.append('engine=no_boardsize')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(fx.check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'boardsize 9' to test:\n"
                   "unknown command")

def test_check_player_startup_gtp_commands(tc):
    fx = Player_check_fixture(tc)
    fx.player.startup_gtp_commands = [('list_commands', []),
                                      ('nonexistent', ['command'])]
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(fx.check)
    tc.assertEqual(str(ar.exception),
                   "failure response from 'nonexistent command' to test:\n"
                   "unknown command")

def test_check_player_nonexistent_cwd(tc):
    fx = Player_check_fixture(tc)
    fx.player.cwd = "/nonexistent/directory"
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(fx.check)
    tc.assertEqual(str(ar.exception),
                   "bad working directory: /nonexistent/directory")

def test_check_player_cwd(tc):
    fx = Player_check_fixture(tc)
    fx.player.cwd = "/"
    tc.assertEqual(game_jobs.check_player(fx.check), [])
    channel = fx.get_channel('test')
    tc.assertEqual(channel.requested_cwd, "/")

def test_check_player_env(tc):
    fx = Player_check_fixture(tc)
    fx.player.environ = {'GOMILL_TEST' : 'gomill'}
    tc.assertEqual(game_jobs.check_player(fx.check), [])
    channel = fx.get_channel('test')
    tc.assertEqual(channel.requested_env['GOMILL_TEST'], 'gomill')
    tc.assertNotIn('GOMILL_SLOT', channel.requested_env)
    # Check environment was merged, not replaced
    tc.assertEqual(channel.requested_env['GOMILL_GAME_ID'], 'startup-check')
    tc.assertIn('PATH', channel.requested_env)

def test_check_player_exec_failure(tc):
    fx = Player_check_fixture(tc)
    fx.player.cmd_args.append('fail=startup')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(fx.check)
    tc.assertEqual(str(ar.exception),
                   "error starting subprocess for test:\n"
                   "exec forced to fail")

def test_check_player_channel_error(tc):
    def fail_first_command(channel):
        channel.fail_next_command = True
    fx = Player_check_fixture(tc)
    fx.register_init_callback('fail_first_command', fail_first_command)
    fx.player.cmd_args.append('init=fail_first_command')
    with tc.assertRaises(game_jobs.CheckFailed) as ar:
        game_jobs.check_player(fx.check)
    tc.assertEqual(str(ar.exception),
                   "transport error sending first command (protocol_version) "
                   "to test:\n"
                   "forced failure for send_command_line")

def test_check_player_channel_error_on_close(tc):
    def fail_close(channel):
        channel.fail_close = True
    fx = Player_check_fixture(tc)
    fx.register_init_callback('fail_close', fail_close)
    fx.player.cmd_args.append('init=fail_close')
    tc.assertEqual(game_jobs.check_player(fx.check),
                   ["error closing test:\nforced failure for close"])

