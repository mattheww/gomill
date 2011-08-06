"""Tests for gtp_controller.py"""

from __future__ import with_statement

import os

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse, Gtp_controller)

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests.test_framework import SupporterError
from gomill_tests.gtp_controller_test_support import Preprogrammed_gtp_channel


def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))



### Channel-level

def test_linebased_channel(tc):
    channel = Preprogrammed_gtp_channel("=\n\n=\n\n")
    tc.assertEqual(channel.get_command_stream(), "")
    channel.send_command("play", ["b", "a3"])
    tc.assertEqual(channel.get_command_stream(), "play b a3\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_command_stream(), "play b a3\nquit\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_linebased_channel_responses(tc):
    channel = Preprogrammed_gtp_channel(
        "= 2\n\n"
        # failure response
        "? unknown command\n\n"
        # final response with no newlines
        "= ok")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.send_command("xyzzy", ["1", "2"])
    tc.assertEqual(channel.get_response(), (True, "unknown command"))
    channel.send_command("quit", ["1", "2"])
    tc.assertEqual(channel.get_response(), (False, "ok"))

def test_linebased_channel_response_cleaning(tc):
    channel = Preprogrammed_gtp_channel(
        # empty response
        "=\n\n"
        # whitespace-only response
        "= \n\n"
        # ignores CRs (GTP spec)
        "= 1abc\rde\r\n\r\n"
        # ignores extra blank lines (GTP spec)
        "= 2abcde\n\n\n\n"
        # strips control characters (GTP spec)
        "= 3a\x7fbc\x00d\x07e\n\x01\n"
        # converts tabs to spaces (GTP spec)
        "= 4abc\tde\n\n"
        # strips leading whitespace (channel docs)
        "=  \t   5abcde\n\n"
        # strips trailing whitepace (channel docs)
        "= 6abcde  \t  \n\n"
        # doesn't strip whitespace in the middle of a multiline response
        "= 7aaa  \n  bbb\tccc\nddd  \t  \n\n"
        # passes high characters through
        "= 8ab\xc3\xa7de\n\n"
        # all this at once, in a failure response
        "?    a\raa  \r\n  b\rbb\tcc\x01c\nddd  \t  \n\n"
        )
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertEqual(channel.get_response(), (False, "1abcde"))
    tc.assertEqual(channel.get_response(), (False, "2abcde"))
    tc.assertEqual(channel.get_response(), (False, "3abcde"))
    tc.assertEqual(channel.get_response(), (False, "4abc de"))
    tc.assertEqual(channel.get_response(), (False, "5abcde"))
    tc.assertEqual(channel.get_response(), (False, "6abcde"))
    tc.assertEqual(channel.get_response(), (False, "7aaa  \n  bbb ccc\nddd"))
    tc.assertEqual(channel.get_response(), (False, "8ab\xc3\xa7de"))
    tc.assertEqual(channel.get_response(), (True, "aaa  \n  bbb ccc\nddd"))

def test_linebased_channel_invalid_responses(tc):
    channel = Preprogrammed_gtp_channel(
        # good response first, to get past the "isn't speaking GTP" checking
        "=\n\n"
        "ERROR\n\n"
        "# comments not allowed in responses\n\n"
        )
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpProtocolError, "^no success/failure indication from engine: "
                          "first line is `ERROR`$",
        channel.get_response)
    tc.assertRaisesRegexp(
        GtpProtocolError, "^no success/failure indication from engine: "
                          "first line is `#",
        channel.get_response)

def test_linebased_channel_without_response(tc):
    channel = Preprogrammed_gtp_channel("")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_usage_message_response(tc):
    channel = Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "^engine isn't speaking GTP: first byte is 'U'$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_interactive_response(tc):
    channel = Preprogrammed_gtp_channel("prompt> \n", hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "^engine isn't speaking GTP", channel.get_response)
    channel.close()

def test_linebased_channel_hang(tc):
    # Correct behaviour for a GTP controller here is to wait for a newline.
    # (Would be nice to have a timeout.)
    # This serves as a check that the hangs_before_eof modelling is working.
    channel = Preprogrammed_gtp_channel("=prompt> ", hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        SupporterError, "this would hang", channel.get_response)
    channel.close()

def test_linebased_channel_with_gmp_response(tc):
    channel = Preprogrammed_gtp_channel("\x01\xa1\xa0\x80",
                                        hangs_before_eof=True)
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "appears to be speaking GMP", channel.get_response)
    channel.close()

def test_linebased_channel_with_broken_command_pipe(tc):
    channel = Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    channel.break_command_stream()
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the command channel$",
        channel.send_command, "protocol_version", [])
    channel.close()

def test_linebased_channel_with_broken_response_pipe(tc):
    channel = Preprogrammed_gtp_channel("= 2\n\n? unreached\n\n")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.break_response_stream()
    channel.send_command("list_commands", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()

def test_channel_command_validation(tc):
    channel = Preprogrammed_gtp_channel("\n\n")
    # empty command
    tc.assertRaises(ValueError, channel.send_command, "", [])
    # space in command
    tc.assertRaises(ValueError, channel.send_command, "play b a3", [])
    # space after command
    tc.assertRaises(ValueError, channel.send_command, "play ", ["b", "a3"])
    # control character in command
    tc.assertRaises(ValueError, channel.send_command, "pla\x01y", ["b", "a3"])
    # unicode command
    tc.assertRaises(ValueError, channel.send_command, u"protocol_version", [])
    # space in argument
    tc.assertRaises(ValueError, channel.send_command, "play", ["b a3"])
    # unicode argument
    tc.assertRaises(ValueError, channel.send_command, "play ", [u"b", "a3"])
    # high characters
    channel.send_command("pl\xc3\xa1y", ["b", "\xc3\xa13"])
    tc.assertEqual(channel.get_command_stream(), "pl\xc3\xa1y b \xc3\xa13\n")


### Validating Testing_gtp_channel

def test_testing_gtp_channel(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.send_command("play", ["b", "a3"])
    tc.assertEqual(channel.get_response(), (True, "unknown command"))
    channel.send_command("test", [])
    tc.assertEqual(channel.get_response(), (False, "test response"))
    channel.send_command("multiline", [])
    tc.assertEqual(channel.get_response(),
                   (False, "first line  \n  second line\nthird line"))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_response(), (False, ""))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the command channel",
        channel.send_command, "quit", [])
    channel.close()

def test_testing_gtp_channel_alt(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.engine_exit_breaks_commands = False
    channel.send_command("test", [])
    tc.assertEqual(channel.get_response(), (False, "test response"))
    channel.send_command("quit", [])
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.send_command("test", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_testing_gtp_channel_fatal_errors(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.send_command("fatal", [])
    tc.assertEqual(channel.get_response(), (True, "fatal error"))
    tc.assertRaisesRegexp(
        GtpChannelClosed, "engine has closed the response channel",
        channel.get_response)
    channel.close()

def test_testing_gtp_channel_sequencing(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    tc.assertRaisesRegexp(
        SupporterError, "response request without command",
        channel.get_response)
    channel.send_command("test", [])
    tc.assertRaisesRegexp(
        SupporterError, "two commands in a row",
        channel.send_command, "test", [])

def test_testing_gtp_force_error(tc):
    engine = gtp_engine_fixtures.get_test_engine()
    channel = gtp_controller_test_support.Testing_gtp_channel(engine)
    channel.fail_next_command = True
    tc.assertRaisesRegexp(
        GtpTransportError, "forced failure for send_command_line",
        channel.send_command, "test", [])
    channel.send_command("test", [])
    channel.fail_next_response = True
    tc.assertRaisesRegexp(
        GtpTransportError, "forced failure for get_response_line",
        channel.get_response)
    channel.force_next_response = "# error\n\n"
    tc.assertRaisesRegexp(
        GtpProtocolError,
        "no success/failure indication from engine: first line is `# error`",
        channel.get_response)
    channel.fail_close = True
    tc.assertRaisesRegexp(
        GtpTransportError, "forced failure for close",
        channel.close)


### Controller-level

def test_controller(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.name, 'player test')
    tc.assertIs(controller.channel, channel)
    tc.assertFalse(controller.channel_is_bad)

    tc.assertEqual(controller.do_command("test", "ab", "cd"), "args: ab cd")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("error")
    tc.assertEqual(ar.exception.gtp_error_message, "normal error")
    tc.assertEqual(ar.exception.gtp_command, "error")
    tc.assertSequenceEqual(ar.exception.gtp_arguments, [])
    tc.assertEqual(str(ar.exception),
                   "failure response from 'error' to player test:\n"
                   "normal error")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("fatal")
    tc.assertFalse(controller.channel_is_bad)

    with tc.assertRaises(GtpChannelClosed) as ar:
        controller.do_command("test")
    tc.assertEqual(str(ar.exception),
                   "error sending 'test' to player test:\n"
                   "engine has closed the command channel")
    tc.assertTrue(controller.channel_is_bad)
    controller.close()
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_alt_exit(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine_exit_breaks_commands = False
    controller = Gtp_controller(channel, 'player test')
    controller.do_command("quit")
    tc.assertFalse(controller.channel_is_bad)
    with tc.assertRaises(GtpChannelClosed) as ar:
        controller.do_command("test")
    tc.assertEqual(str(ar.exception),
                   "error reading response to 'test' from player test:\n"
                   "engine has closed the response channel")
    tc.assertTrue(controller.channel_is_bad)
    controller.close()
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_first_command_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("error")
    tc.assertEqual(
        str(ar.exception),
        "failure response from first command (error) to player test:\n"
        "normal error")
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_command_transport_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertFalse(controller.channel_is_bad)
    channel.fail_next_command = True
    with tc.assertRaises(GtpTransportError) as ar:
        controller.do_command("test")
    tc.assertEqual(
        str(ar.exception),
        "transport error sending 'test' to player test:\n"
        "forced failure for send_command_line")
    tc.assertTrue(controller.channel_is_bad)
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_response_transport_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertFalse(controller.channel_is_bad)
    channel.fail_next_response = True
    with tc.assertRaises(GtpTransportError) as ar:
        controller.do_command("test")
    tc.assertEqual(
        str(ar.exception),
        "transport error reading response to first command (test) "
        "from player test:\n"
        "forced failure for get_response_line")
    tc.assertTrue(controller.channel_is_bad)
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_response_protocol_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertFalse(controller.channel_is_bad)
    channel.force_next_response = "# error\n\n"
    with tc.assertRaises(GtpProtocolError) as ar:
        controller.do_command("test")
    tc.assertEqual(
        str(ar.exception),
        "GTP protocol error reading response to 'test' from player test:\n"
        "no success/failure indication from engine: first line is `# error`")
    tc.assertTrue(controller.channel_is_bad)
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_close(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertFalse(controller.channel_is_closed)
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertFalse(controller.channel_is_closed)
    tc.assertFalse(controller.channel.is_closed)
    controller.close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertTrue(controller.channel.is_closed)
    tc.assertRaisesRegexp(StandardError, "^channel is closed$",
                          controller.do_command, "test")
    tc.assertRaisesRegexp(StandardError, "^channel is closed$",
                          controller.close)
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_close_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    channel.fail_close = True
    with tc.assertRaises(GtpTransportError) as ar:
        controller.close()
    tc.assertEqual(
        str(ar.exception),
        "error closing player test:\n"
        "forced failure for close")
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_safe_close(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertFalse(controller.channel_is_closed)
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertFalse(controller.channel_is_closed)
    tc.assertFalse(controller.channel.is_closed)
    controller.safe_close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertTrue(controller.channel.is_closed)
    tc.assertListEqual(channel.engine.commands_handled,
                       [('test', []), ('quit', [])])
    # safe to call twice
    controller.safe_close()
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_safe_close_after_error(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertFalse(controller.channel_is_bad)
    channel.force_next_response = "# error\n\n"
    with tc.assertRaises(GtpProtocolError) as ar:
        controller.do_command("test")
    tc.assertTrue(controller.channel_is_bad)
    # doesn't send quit when channel_is_bad
    controller.safe_close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertTrue(controller.channel.is_closed)
    tc.assertListEqual(channel.engine.commands_handled,
                       [('test', []), ('test', [])])
    tc.assertListEqual(controller.retrieve_error_messages(), [])

def test_controller_safe_close_with_error_from_quit(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    channel.force_next_response = "# error\n\n"
    controller.safe_close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertTrue(controller.channel.is_closed)
    tc.assertListEqual(channel.engine.commands_handled,
                       [('quit', [])])
    tc.assertListEqual(
        controller.retrieve_error_messages(),
        ["GTP protocol error reading response to first command (quit) "
         "from player test:\n"
         "no success/failure indication from engine: first line is `# error`"])

def test_controller_safe_close_with_failure_response_from_quit(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    channel.engine.force_error("quit")
    controller.safe_close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertTrue(controller.channel.is_closed)
    tc.assertListEqual(channel.engine.commands_handled,
                       [('quit', [])])
    error_messages = controller.retrieve_error_messages()
    tc.assertEqual(len(error_messages), 1)
    tc.assertEqual(
        error_messages[0],
        "failure response from first command (quit) to player test:\n"
        "handler forced to fail")

def test_controller_safe_close_with_error_from_close(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    channel.fail_close = True
    controller.safe_close()
    tc.assertTrue(controller.channel_is_closed)
    tc.assertListEqual(channel.engine.commands_handled,
                       [('quit', [])])
    tc.assertListEqual(
        controller.retrieve_error_messages(),
        ["error closing player test:\n"
         "forced failure for close"])

def test_safe_do_command(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    tc.assertEqual(controller.safe_do_command("test", "ab"), "args: ab")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.safe_do_command("error")
    tc.assertFalse(controller.channel_is_bad)
    channel.fail_next_response = True
    tc.assertIsNone(controller.safe_do_command("test"))
    tc.assertTrue(controller.channel_is_bad)
    tc.assertIsNone(controller.safe_do_command("test"))
    tc.assertListEqual(
        controller.retrieve_error_messages(),
        ["transport error reading response to 'test' from player test:\n"
         "forced failure for get_response_line"])
    controller.safe_close()
    # check that third 'test' wasn't sent, and nor was 'quit'
    tc.assertListEqual(channel.engine.commands_handled,
                       [('test', ['ab']), ('error', []), ('test', [])])

def test_safe_do_command_closed_channel(tc):
    # check it's ok to call safe_do_command() on a closed channel
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    controller.safe_close()
    tc.assertIsNone(controller.safe_do_command("test"))
    tc.assertListEqual(channel.engine.commands_handled,
                       [('quit', [])])
    tc.assertListEqual(controller.retrieve_error_messages(), [])


def test_known_command(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'kc test')
    tc.assertTrue(controller.known_command("test"))
    tc.assertFalse(controller.known_command("nonesuch"))
    tc.assertTrue(controller.known_command("test"))
    tc.assertFalse(controller.known_command("nonesuch"))

def test_known_command_2(tc):
    # Checking that known_command caches its responses
    # and that it treats an error or unknown value the same as 'false'.
    channel = Preprogrammed_gtp_channel(
        "= true\n\n= absolutely not\n\n? error\n\n# unreached\n\n")
    controller = Gtp_controller(channel, 'kc2 test')
    tc.assertTrue(controller.known_command("one"))
    tc.assertFalse(controller.known_command("two"))
    tc.assertFalse(controller.known_command("three"))
    tc.assertTrue(controller.known_command("one"))
    tc.assertFalse(controller.known_command("two"))
    tc.assertEqual(
        channel.get_command_stream(),
        "known_command one\nknown_command two\nknown_command three\n")

def test_check_protocol_version(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'pv test')
    controller.check_protocol_version()

def test_check_protocol_version_2(tc):
    channel = Preprogrammed_gtp_channel("= 1\n\n? error\n\n# unreached\n\n")
    controller = Gtp_controller(channel, 'pv2 test')
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.check_protocol_version()
    tc.assertEqual(str(ar.exception), "pv2 test reports GTP protocol version 1")
    tc.assertEqual(ar.exception.gtp_error_message, None)
    # check error is not treated as a check failure
    controller.check_protocol_version()

def test_list_commands(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'lc test')
    channel.engine.add_command("xyzzy", None)
    channel.engine.add_command("pl ugh", None)
    tc.assertListEqual(
        controller.list_commands(),
        ['error', 'fatal', 'known_command', 'list_commands',
         'multiline', 'protocol_version', 'quit', 'test', 'xyzzy'])

def test_gtp_aliases(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'alias test')
    controller.set_gtp_aliases({
        'aliased'  : 'test',
        'aliased2' : 'nonesuch',
        })
    tc.assertIs(controller.known_command("test"), True)
    tc.assertIs(controller.known_command("aliased"), True)
    tc.assertIs(controller.known_command("nonesuch"), False)
    tc.assertIs(controller.known_command("test"), True)
    tc.assertIs(controller.known_command("aliased"), True)
    tc.assertIs(controller.known_command("nonesuch"), False)
    tc.assertEqual(controller.do_command("test"), "test response")
    tc.assertEqual(controller.do_command("aliased"), "test response")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.do_command("aliased2")
    tc.assertEqual(ar.exception.gtp_error_message, "unknown command")
    tc.assertEqual(ar.exception.gtp_command, "nonesuch")

def test_gtp_aliases_safe(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'alias test')
    controller.set_gtp_aliases({
        'aliased'  : 'test',
        'aliased2' : 'nonesuch',
        })
    tc.assertIs(controller.safe_known_command("test"), True)
    tc.assertIs(controller.safe_known_command("aliased"), True)
    tc.assertIs(controller.safe_known_command("nonesuch"), False)
    tc.assertIs(controller.safe_known_command("test"), True)
    tc.assertIs(controller.safe_known_command("aliased"), True)
    tc.assertIs(controller.safe_known_command("nonesuch"), False)
    tc.assertEqual(controller.safe_do_command("test"), "test response")
    tc.assertEqual(controller.safe_do_command("aliased"), "test response")
    with tc.assertRaises(BadGtpResponse) as ar:
        controller.safe_do_command("aliased2")
    tc.assertEqual(ar.exception.gtp_error_message, "unknown command")
    tc.assertEqual(ar.exception.gtp_command, "nonesuch")


def test_fix_version(tc):
    fv = gtp_controller._fix_version
    tc.assertEqual(fv("foo", "bar"), "bar")
    tc.assertEqual(fv("foo", "FOO bar"), "bar")
    tc.assertEqual(fv("foo", "asd " * 16), "asd " * 16)
    tc.assertEqual(fv("foo", "asd " * 17), "asd")
    tc.assertEqual(
        fv("MoGo", "MoGo release 1. Please read http://www.lri.fr/~gelly/MoGo.htm for more information. That is NOT an official developpement MoGo version, but it is a public release. Its strength highly depends on your hardware and the time settings."),
        "release 1")
    tc.assertEqual(
        fv("Pachi UCT Engine", "8.99 (Hakugen-devel): I'm playing UCT. When I'm losing, I will resign, if I think I win, I play until you pass. Anyone can send me 'winrate' in private chat to get my assessment of the position."),
        "8.99 (Hakugen-devel)")

def test_describe_engine(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "unknown")
    tc.assertEqual(long_s, "unknown")

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine")
    tc.assertEqual(long_s, "test engine")

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:1.2.3")
    tc.assertEqual(long_s, "test engine:1.2.3")

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    channel.engine.add_command(
        'gomill-describe_engine',
        lambda args:"test engine (v1.2.3):\n  pl\xc3\xa1yer \xa3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:1.2.3")
    tc.assertEqual(long_s, "test engine (v1.2.3):\n  pl\xc3\xa1yer ?")

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"test engine v1.2.3")
    controller = Gtp_controller(channel, 'player test')
    short_s, long_s = gtp_controller.describe_engine(controller)
    tc.assertEqual(short_s, "test engine:v1.2.3")
    tc.assertEqual(long_s, "test engine:v1.2.3")


### Subprocess-specific

def test_subprocess_channel(tc):
    # This tests that Subprocess_gtp_channel really launches a subprocess.
    # It also checks that the 'stderr', 'env' and 'cwd' parameters work.
    # This test relies on there being a 'python' executable on the PATH
    # (doesn't have to be the same version as is running the testsuite).
    fx = gtp_engine_fixtures.State_reporter_fixture(tc)
    rd, wr = os.pipe()
    try:
        channel = gtp_controller.Subprocess_gtp_channel(
            fx.cmd,
            stderr=wr,
            env={'GOMILL_TEST' : "from_gtp_controller_tests"},
            cwd="/")
        tc.assertEqual(os.read(rd, 256), "subprocess_state_reporter: testing\n")
    finally:
        os.close(wr)
        os.close(rd)
    tc.assertIsNone(channel.exit_status)
    tc.assertIsNone(channel.resource_usage)
    channel.send_command("tell", [])
    tc.assertEqual(channel.get_response(),
                   (False, "cwd: /\nGOMILL_TEST:from_gtp_controller_tests"))
    channel.close()
    tc.assertEqual(channel.exit_status, 0)
    rusage = channel.resource_usage
    tc.assertTrue(hasattr(rusage, 'ru_utime'))
    tc.assertTrue(hasattr(rusage, 'ru_stime'))

def test_subprocess_channel_nonexistent_program(tc):
    with tc.assertRaises(GtpChannelError) as ar:
        gtp_controller.Subprocess_gtp_channel(["/nonexistent/program"])
    tc.assertIn("[Errno 2] No such file or directory", str(ar.exception))

def test_subprocess_channel_with_controller(tc):
    # Also tests that leaving 'env' and 'cwd' unset works
    fx = gtp_engine_fixtures.State_reporter_fixture(tc)
    channel = gtp_controller.Subprocess_gtp_channel(fx.cmd, stderr=fx.devnull)
    controller = Gtp_controller(channel, 'subprocess test')
    tc.assertEqual(controller.do_command("tell"),
                   "cwd: %s\nGOMILL_TEST:None" % os.getcwd())
    controller.close()
    tc.assertEqual(channel.exit_status, 0)
    rusage = channel.resource_usage
    tc.assertTrue(hasattr(rusage, 'ru_utime'))

