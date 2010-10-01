"""Tests for gtp_proxy.py"""

from __future__ import with_statement

from gomill import gtp_controller
from gomill import gtp_proxy
from gomill.gtp_engine import GtpError, GtpFatalError
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse, Gtp_controller)
from gomill.gtp_proxy import BackEndError

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests import gtp_engine_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Proxy_fixture(test_framework.Fixture):
    """Fixture managing a Gtp_proxy with the test engine as its back-end.

    attributes:
      proxy             -- Gtp_proxy
      controller        -- Gtp_controller
      channel           -- Testing_gtp_channel (like get_test_channel())
      engine            -- the proxy engine
      underlying_engine -- the underlying test engine (like get_test_engine())
      commands_handled  -- from the underlying Test_gtp_engine_protocol

    """
    def __init__(self, tc):
        self.tc = tc
        self.channel = gtp_engine_fixtures.get_test_channel()
        self.underlying_engine = self.channel.engine
        self.controller = gtp_controller.Gtp_controller(
            self.channel, 'testbackend')
        self.proxy = gtp_proxy.Gtp_proxy()
        self.proxy.set_back_end_controller(self.controller)
        self.engine = self.proxy.engine
        self.commands_handled = self.underlying_engine.commands_handled

    def check_command(self, *args, **kwargs):
        """Send a command to the proxy engine and check its response.

        (This is testing the proxy engine, not the underlying engine.)

        parameters as for gtp_engine_test_support.check_engine()

        """
        gtp_engine_test_support.check_engine(
            self.tc, self.engine, *args, **kwargs)


def test_proxy(tc):
    fx = Proxy_fixture(tc)
    fx.check_command('test', ['ab', 'cd'], "args: ab cd")
    fx.proxy.close()
    tc.assertEqual(
        fx.commands_handled,
        [('list_commands', []), ('test', ['ab', 'cd']), ('quit', [])])
    tc.assertTrue(fx.controller.channel.is_closed)

def test_close_after_quit(tc):
    fx = Proxy_fixture(tc)
    fx.check_command('quit', [], "", expect_end=True)
    fx.proxy.close()
    tc.assertEqual(
        fx.commands_handled,
        [('list_commands', []), ('quit', [])])
    tc.assertTrue(fx.channel.is_closed)

def test_list_commands(tc):
    fx = Proxy_fixture(tc)
    tc.assertListEqual(
        fx.engine.list_commands(),
        ['error', 'fatal', 'gomill-passthrough', 'known_command',
         'list_commands', 'multiline', 'protocol_version', 'quit', 'test'])
    fx.proxy.close()

def test_back_end_has_command(tc):
    fx = Proxy_fixture(tc)
    tc.assertTrue(fx.proxy.back_end_has_command('test'))
    tc.assertFalse(fx.proxy.back_end_has_command('xyzzy'))
    tc.assertFalse(fx.proxy.back_end_has_command('gomill-passthrough'))

def test_passthrough(tc):
    fx = Proxy_fixture(tc)
    fx.check_command('known_command', ['gomill-passthrough'], "true")
    fx.check_command('gomill-passthrough', ['test', 'ab', 'cd'], "args: ab cd")
    fx.check_command(
        'gomill-passthrough', ['known_command', 'gomill-passthrough'], "false")
    fx.check_command('gomill-passthrough', [],
                     "invalid arguments", expect_failure=True)
    tc.assertEqual(
        fx.commands_handled,
        [('list_commands', []), ('test', ['ab', 'cd']),
         ('known_command', ['gomill-passthrough'])])

def test_pass_command(tc):
    fx = Proxy_fixture(tc)
    tc.assertEqual(fx.proxy.pass_command("test", ["ab", "cd"]), "args: ab cd")
    with tc.assertRaises(BadGtpResponse) as ar:
        fx.proxy.pass_command("error", [])
    tc.assertEqual(ar.exception.gtp_error_message, "normal error")
    tc.assertEqual(str(ar.exception),
                   "failure response from 'error' to testbackend:\n"
                   "normal error")

def test_pass_command_with_channel_error(tc):
    fx = Proxy_fixture(tc)
    fx.channel.fail_next_command = True
    with tc.assertRaises(BackEndError) as ar:
        fx.proxy.pass_command("test", [])
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'test' to testbackend:\n"
                   "forced failure for send_command_line")
    tc.assertIsInstance(ar.exception.cause, GtpTransportError)
    fx.proxy.close()
    tc.assertEqual(fx.commands_handled, [('list_commands', [])])

def test_handle_command(tc):
    def handle_xyzzy(args):
        if args and args[0] == "error":
            return fx.proxy.handle_command("error", [])
        else:
            return fx.proxy.handle_command("test", ["nothing", "happens"])
    fx = Proxy_fixture(tc)
    fx.engine.add_command("xyzzy", handle_xyzzy)
    fx.check_command('xyzzy', [], "args: nothing happens")
    fx.check_command('xyzzy', ['error'],
                     "normal error", expect_failure=True)

def test_handle_command_with_channel_error(tc):
    def handle_xyzzy(args):
        return fx.proxy.handle_command("test", [])
    fx = Proxy_fixture(tc)
    fx.engine.add_command("xyzzy", handle_xyzzy)
    fx.channel.fail_next_command = True
    fx.check_command('xyzzy', [],
                     "transport error sending 'test' to testbackend:\n"
                     "forced failure for send_command_line",
                     expect_failure=True, expect_end=True)
    fx.proxy.close()
    tc.assertEqual(fx.commands_handled, [('list_commands', [])])

def test_back_end_goes_away(tc):
    fx = Proxy_fixture(tc)
    tc.assertEqual(fx.proxy.pass_command("quit", []), "")
    fx.check_command('test', ['ab', 'cd'],
                     "error sending 'test ab cd' to testbackend:\n"
                     "engine has closed the command channel",
                     expect_failure=True, expect_end=True)

def test_close_with_errors(tc):
    fx = Proxy_fixture(tc)
    fx.channel.fail_next_command = True
    with tc.assertRaises(BackEndError) as ar:
        fx.proxy.close()
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'quit' to testbackend:\n"
                   "forced failure for send_command_line")
    tc.assertTrue(fx.channel.is_closed)

def test_quit_ignores_already_closed(tc):
    fx = Proxy_fixture(tc)
    tc.assertEqual(fx.proxy.pass_command("quit", []), "")
    fx.check_command('quit', [], "", expect_end=True)
    fx.proxy.close()
    tc.assertEqual(fx.commands_handled,
                   [('list_commands', []), ('quit', [])])

def test_quit_with_failure_response(tc):
    fx = Proxy_fixture(tc)
    fx.underlying_engine.force_error("quit")
    fx.check_command('quit', [], None,
                     expect_failure=True, expect_end=True)
    fx.proxy.close()
    tc.assertEqual(fx.commands_handled,
                   [('list_commands', []), ('quit', [])])

def test_quit_with_channel_error(tc):
    fx = Proxy_fixture(tc)
    fx.channel.fail_next_command = True
    fx.check_command('quit', [],
                     "transport error sending 'quit' to testbackend:\n"
                     "forced failure for send_command_line",
                     expect_failure=True, expect_end=True)
    fx.proxy.close()
    tc.assertEqual(fx.commands_handled, [('list_commands', [])])

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
    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.force_error("list_commands")
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    with tc.assertRaises(BackEndError) as ar:
        proxy.set_back_end_controller(controller)
    tc.assertEqual(str(ar.exception),
                   "failure response from first command "
                   "(list_commands) to testbackend:\n"
                   "handler forced to fail")
    tc.assertIsInstance(ar.exception.cause, BadGtpResponse)
    proxy.close()


def test_set_back_end_subprocess(tc):
    fx = gtp_engine_fixtures.State_reporter_fixture(tc)
    proxy = gtp_proxy.Gtp_proxy()
    # the state-report will be taken as the response to list_commands
    proxy.set_back_end_subprocess(fx.cmd, stderr=fx.devnull)
    proxy.expect_back_end_exit()
    proxy.close()

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
