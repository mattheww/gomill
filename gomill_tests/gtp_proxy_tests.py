"""Tests for gtp_proxy.py"""

from __future__ import with_statement

import os

from gomill import gtp_controller
from gomill import gtp_proxy
from gomill.gtp_engine import GtpError, GtpFatalError
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse, Gtp_controller)
from gomill.gtp_proxy import BackEndError

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests import gtp_engine_test_support
from gomill_tests.gtp_engine_test_support import check_engine

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def _make_proxy():
    channel = gtp_engine_fixtures.get_test_channel()
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_controller(controller)
    # Make the commands from the underlying Recording_gtp_engine_protocol
    # available to tests
    proxy._commands_handled = controller.channel.engine.commands_handled
    return proxy

def test_proxy(tc):
    proxy = _make_proxy()
    check_engine(tc, proxy.engine, 'test', ['ab', 'cd'], "args: ab cd")
    proxy.close()
    tc.assertEqual(
        proxy._commands_handled,
        [('list_commands', []), ('test', ['ab', 'cd']), ('quit', [])])
    tc.assertTrue(proxy.controller.channel.is_closed)

def test_close_after_quit(tc):
    proxy = _make_proxy()
    check_engine(tc, proxy.engine, 'quit', [], "", expect_end=True)
    proxy.close()
    tc.assertEqual(
        proxy._commands_handled,
        [('list_commands', []), ('quit', [])])
    tc.assertTrue(proxy.controller.channel.is_closed)

def test_list_commands(tc):
    proxy = _make_proxy()
    tc.assertListEqual(
        proxy.engine.list_commands(),
        ['error', 'fatal', 'gomill-passthrough', 'known_command',
         'list_commands', 'multiline', 'protocol_version', 'quit', 'test'])
    proxy.close()

def test_back_end_has_command(tc):
    proxy = _make_proxy()
    tc.assertTrue(proxy.back_end_has_command('test'))
    tc.assertFalse(proxy.back_end_has_command('xyzzy'))
    tc.assertFalse(proxy.back_end_has_command('gomill-passthrough'))

def test_passthrough(tc):
    proxy = _make_proxy()
    check_engine(tc, proxy.engine,
                 'known_command', ['gomill-passthrough'], "true")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', ['test', 'ab', 'cd'], "args: ab cd")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', ['known_command', 'gomill-passthrough'],
                 "false")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', [],
                 "invalid arguments", expect_failure=True)
    tc.assertEqual(
        proxy._commands_handled,
        [('list_commands', []), ('test', ['ab', 'cd']),
         ('known_command', ['gomill-passthrough'])])

def test_pass_command(tc):
    proxy = _make_proxy()
    tc.assertEqual(proxy.pass_command("test", ["ab", "cd"]), "args: ab cd")
    with tc.assertRaises(BadGtpResponse) as ar:
        proxy.pass_command("error", [])
    tc.assertEqual(ar.exception.gtp_error_message, "normal error")
    tc.assertEqual(str(ar.exception),
                   "failure response from 'error' to testbackend:\n"
                   "normal error")

def test_pass_command_with_channel_error(tc):
    proxy = _make_proxy()
    proxy.controller.channel.fail_next_command = True
    with tc.assertRaises(BackEndError) as ar:
        proxy.pass_command("test", [])
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'test' to testbackend:\n"
                   "forced failure for send_command_line")
    tc.assertIsInstance(ar.exception.cause, GtpTransportError)
    proxy.close()
    tc.assertEqual(proxy._commands_handled, [('list_commands', [])])

def test_handle_command(tc):
    def handle_xyzzy(args):
        if args and args[0] == "error":
            return proxy.handle_command("error", [])
        else:
            return proxy.handle_command("test", ["nothing", "happens"])
    proxy = _make_proxy()
    proxy.engine.add_command("xyzzy", handle_xyzzy)
    check_engine(tc, proxy.engine, 'xyzzy', [], "args: nothing happens")
    check_engine(tc, proxy.engine, 'xyzzy', ['error'],
                 "normal error", expect_failure=True)

def test_handle_command_with_channel_error(tc):
    def handle_xyzzy(args):
        return proxy.handle_command("test", [])
    proxy = _make_proxy()
    proxy.engine.add_command("xyzzy", handle_xyzzy)
    proxy.controller.channel.fail_next_command = True
    check_engine(tc, proxy.engine, 'xyzzy', [],
                 "transport error sending 'test' to testbackend:\n"
                 "forced failure for send_command_line",
                 expect_failure=True, expect_end=True)
    proxy.close()
    tc.assertEqual(proxy._commands_handled, [('list_commands', [])])

def test_back_end_goes_away(tc):
    proxy = _make_proxy()
    tc.assertEqual(proxy.pass_command("quit", []), "")
    check_engine(tc, proxy.engine, 'test', ['ab', 'cd'],
                 "error sending 'test ab cd' to testbackend:\n"
                 "engine has closed the command channel",
                 expect_failure=True, expect_end=True)

def test_close_with_errors(tc):
    proxy = _make_proxy()
    proxy.controller.channel.fail_next_command = True
    with tc.assertRaises(BackEndError) as ar:
        proxy.close()
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'quit' to testbackend:\n"
                   "forced failure for send_command_line")
    tc.assertTrue(proxy.controller.channel.is_closed)

def test_quit_ignores_already_closed(tc):
    proxy = _make_proxy()
    tc.assertEqual(proxy.pass_command("quit", []), "")
    check_engine(tc, proxy.engine, 'quit', [], "", expect_end=True)
    proxy.close()
    tc.assertEqual(proxy._commands_handled,
                   [('list_commands', []), ('quit', [])])

def test_quit_with_failure_response(tc):
    def force_error(args):
        1 / 0
    proxy = _make_proxy()
    proxy.controller.channel.engine.add_command("quit", force_error)
    check_engine(tc, proxy.engine, 'quit', [], None,
                 expect_failure=True, expect_end=True)
    proxy.close()
    tc.assertEqual(proxy._commands_handled,
                   [('list_commands', []), ('quit', [])])

def test_quit_with_channel_error(tc):
    proxy = _make_proxy()
    proxy.controller.channel.fail_next_command = True
    check_engine(tc, proxy.engine, 'quit', [],
                 "transport error sending 'quit' to testbackend:\n"
                 "forced failure for send_command_line",
                 expect_failure=True, expect_end=True)
    proxy.close()
    tc.assertEqual(proxy._commands_handled, [('list_commands', [])])

def test_nontgtp_backend(tc):
    channel = gtp_controller_test_support.Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    with tc.assertRaises(BackEndError) as ar:
        proxy.set_back_end_controller(controller)
    tc.assertEqual(str(ar.exception),
                   "GTP protocol error reading response to first command "
                   "(list_commands) from testbackend:\n"
                   "engine isn't speaking GTP: first byte is 'U'")
    tc.assertIsInstance(ar.exception.cause, GtpProtocolError)
    proxy.close()

def test_error_from_list_commands(tc):
    def force_error(args):
        1 / 0
    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command("list_commands", force_error)
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    with tc.assertRaises(BackEndError) as ar:
        proxy.set_back_end_controller(controller)
    tc.assertIn("failure response from first command "
                "(list_commands) to testbackend:\n",
                str(ar.exception))
    tc.assertIsInstance(ar.exception.cause, BadGtpResponse)
    proxy.close()


def test_set_back_end_subprocess(tct):
    devnull = open(os.devnull, "w")
    try:
        proxy = gtp_proxy.Gtp_proxy()
        # the state-report will be taken as the response to list_commands
        proxy.set_back_end_subprocess(
            gtp_controller_test_support.state_reporter_cmd, stderr=devnull)
        proxy.expect_back_end_exit()
        proxy.close()
    finally:
        devnull.close()

def test_set_back_end_subprocess_nonexistent_program(tc):
    proxy = gtp_proxy.Gtp_proxy()
    with tc.assertRaises(BackEndError) as ar:
        proxy.set_back_end_subprocess("/nonexistent/program")
    tc.assertEqual(str(ar.exception),
                   "can't launch back end command\n"
                   "[Errno 2] No such file or directory")
    tc.assertIsInstance(ar.exception.cause, GtpChannelError)
    # check it's safe to close when the controller was never set
    proxy.close()
