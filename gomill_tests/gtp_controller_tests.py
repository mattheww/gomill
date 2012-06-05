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
    fv = gtp_controller.Engine_description._fix_version
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

def test_engine_description(tc):
    ed = gtp_controller.Engine_description(None, None, None)
    tc.assertIsNone(ed.raw_name)
    tc.assertIsNone(ed.raw_version)
    tc.assertIsNone(ed.name)
    tc.assertIsNone(ed.version)
    tc.assertIsNone(ed.clean_version)
    tc.assertIsNone(ed.description)
    tc.assertIsNone(ed.get_short_description())
    tc.assertIsNone(ed.get_long_description())

    ed = gtp_controller.Engine_description("", "", "")
    tc.assertEqual(ed.raw_name, "")
    tc.assertEqual(ed.raw_version, "")
    tc.assertIsNone(ed.name)
    tc.assertIsNone(ed.version)
    tc.assertIsNone(ed.clean_version)
    tc.assertIsNone(ed.description)
    tc.assertIsNone(ed.get_short_description())
    tc.assertIsNone(ed.get_long_description())

    ed = gtp_controller.Engine_description("name", "version", "description")
    tc.assertEqual(ed.raw_name, "name")
    tc.assertEqual(ed.raw_version, "version")
    tc.assertEqual(ed.name, "name")
    tc.assertEqual(ed.version, "version")
    tc.assertEqual(ed.clean_version, "version")
    tc.assertEqual(ed.description, "description")
    tc.assertEqual(ed.get_short_description(), "name:version")
    tc.assertEqual(ed.get_long_description(), "description")

    bad = u"\N{POUND SIGN}".encode("latin1")
    ed = gtp_controller.Engine_description(
        "name"+bad, "version"+bad, "description"+bad)
    tc.assertEqual(ed.raw_name, "name"+bad)
    tc.assertEqual(ed.raw_version, "version"+bad)
    tc.assertEqual(ed.name, "name?")
    tc.assertEqual(ed.version, "version?")
    tc.assertEqual(ed.clean_version, "version?")
    tc.assertEqual(ed.description, "description?")

    # check version cleaning happens
    ed = gtp_controller.Engine_description("name", "name version", None)
    tc.assertEqual(ed.raw_version, "name version")
    tc.assertEqual(ed.version, "name version")
    tc.assertEqual(ed.clean_version, "version")
    tc.assertEqual(ed.get_short_description(), "name:version")

    ed = gtp_controller.Engine_description("name", "version", None)
    tc.assertEqual(ed.get_short_description(), "name:version")
    tc.assertEqual(ed.get_long_description(), "name:version")

    ed = gtp_controller.Engine_description(
        "name", "ratherlongversionover32characters", None)
    tc.assertEqual(ed.get_short_description(), "name")
    tc.assertEqual(ed.get_long_description(),
                   "name:ratherlongversionover32characters")

    ed = gtp_controller.Engine_description(None, "123", None)
    tc.assertIsNone(ed.get_short_description())
    tc.assertEqual(ed.get_long_description(), "version 123")

def test_engine_description_from_channel(tc):
    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player test')
    ed = gtp_controller.Engine_description.from_controller(controller)
    tc.assertIsNone(ed.raw_name)
    tc.assertIsNone(ed.raw_version)
    tc.assertIsNone(ed.description)

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    controller = Gtp_controller(channel, 'player test')
    ed = gtp_controller.Engine_description.from_controller(controller)
    tc.assertEqual(ed.raw_name, "test engine")
    tc.assertEqual(ed.raw_version, "1.2.3")
    tc.assertIsNone(ed.description)

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.add_command('name', lambda args:"test engine")
    channel.engine.add_command('version', lambda args:"1.2.3")
    channel.engine.add_command('gomill-describe_engine', lambda args:"foo\nbar")
    controller = Gtp_controller(channel, 'player test')
    ed = gtp_controller.Engine_description.from_controller(controller)
    tc.assertEqual(ed.raw_name, "test engine")
    tc.assertEqual(ed.raw_version, "1.2.3")
    tc.assertEqual(ed.description, "foo\nbar")

    channel = gtp_engine_fixtures.get_test_channel()
    channel.engine.force_error('name')
    channel.engine.force_error('version')
    channel.engine.force_error('gomill-describe_engine')
    controller = Gtp_controller(channel, 'player test')
    ed = gtp_controller.Engine_description.from_controller(controller)
    tc.assertIsNone(ed.raw_name)
    tc.assertIsNone(ed.raw_version)
    tc.assertIsNone(ed.description)


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


### FIXME test nonblocking controller

from gomill import nonblocking_gtp_controller

def test_subprocess_channel_nb(tc):
    # This tests that Subprocess_gtp_channel really launches a subprocess.
    # It also checks that the 'stderr', 'env' and 'cwd' parameters work.
    # This test relies on there being a 'python' executable on the PATH
    # (doesn't have to be the same version as is running the testsuite).
    fx = gtp_engine_fixtures.State_reporter_fixture(tc)
    channel = nonblocking_gtp_controller.Subprocess_gtp_channel(
        fx.cmd + ["--extra-stderr"],
        stderr='capture',
        env={'GOMILL_TEST' : "from_gtp_controller_tests"},
        cwd="/")
    tc.assertIsNone(channel.exit_status)
    tc.assertIsNone(channel.resource_usage)
    channel.send_command("tell", [])
    tc.assertEqual(channel.get_response(),
                   (False, "cwd: /\nGOMILL_TEST:from_gtp_controller_tests"))
    tc.assertEqual(channel.retrieve_diagnostics(),
                   "subprocess_state_reporter: testing\n" + "blah\n" * 500)
    channel.close()
    tc.assertEqual(channel.exit_status, 0)
    rusage = channel.resource_usage
    tc.assertTrue(hasattr(rusage, 'ru_utime'))
    tc.assertTrue(hasattr(rusage, 'ru_stime'))

def test_subprocess_channel_buffer_limit(tc):
    fx = gtp_engine_fixtures.State_reporter_fixture(tc)
    channel = nonblocking_gtp_controller.Subprocess_gtp_channel(
        fx.cmd + ["--extra-stderr"],
        stderr='capture',
        cwd="/")
    channel.max_diagnostic_buffer_size = 2000
    channel.send_command("tell", [])
    tc.assertEqual(channel.get_response(), (False, "cwd: /\nGOMILL_TEST:None"))
    tc.assertMultiLineEqual(channel.retrieve_diagnostics(),
                            ("subprocess_state_reporter: testing\n" +
                             "blah\n" * 500)[:2000] + "\n[[truncated]]")
    channel.close()
    tc.assertEqual(channel.exit_status, 0)


### Game_controller

def test_game_controller(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    channel1.engine.add_command('b_only', lambda args:"yes")

    gc = gtp_controller.Game_controller('one', 'two')
    tc.assertRaises(KeyError, gc.get_controller, 'b')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2, check_protocol_version=False)

    tc.assertIsNone(gc.engine_descriptions['b'].raw_name)
    tc.assertIsNone(gc.engine_descriptions['b'].raw_version)
    tc.assertIsNone(gc.engine_descriptions['b'].description)
    tc.assertIsNone(gc.engine_descriptions['w'].raw_name)
    tc.assertIsNone(gc.engine_descriptions['w'].raw_version)
    tc.assertIsNone(gc.engine_descriptions['w'].description)

    tc.assertEqual(gc.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIs(gc.get_controller('b'), controller1)
    tc.assertIs(gc.get_controller('w'), controller2)
    tc.assertRaises(KeyError, gc.get_controller, 'x')

    tc.assertIs(gc.known_command('b', 'b_only'), True)
    tc.assertIs(gc.known_command('w', 'b_only'), False)

    tc.assertEqual(gc.send_command('b', 'test'), "test response")
    tc.assertEqual(gc.send_command('w', 'test', 'abc', 'def'),
                   "args: abc def")

    tc.assertEqual(gc.send_command('b', 'b_only'), "yes")
    with tc.assertRaises(BadGtpResponse) as ar:
        gc.send_command('w', 'b_only')
    tc.assertEqual(ar.exception.gtp_error_message, "unknown command")
    tc.assertEqual(ar.exception.gtp_command, "b_only")

    with tc.assertRaises(BadGtpResponse) as ar:
        gc.send_command('b', 'error')
    tc.assertEqual(ar.exception.gtp_error_message, "normal error")
    tc.assertEqual(ar.exception.gtp_command, "error")

    tc.assertEqual(gc.maybe_send_command('b', 'b_only'), "yes")
    tc.assertIsNone(gc.maybe_send_command('w', 'b_only'))
    tc.assertIsNone(gc.maybe_send_command('b', 'error'))

    tc.assertIsNone(gc.describe_late_errors())
    tc.assertIs(controller1.channel_is_closed, False)
    tc.assertIs(controller2.channel_is_closed, False)
    gc.close_players()
    tc.assertIs(controller1.channel_is_closed, True)
    tc.assertIs(controller2.channel_is_closed, True)
    tc.assertIsNone(gc.describe_late_errors())

    tc.assertEqual(gc.get_resource_usage_cpu_times(), {'b' : None, 'w' : None})

    tc.assertEqual(channel1.engine.commands_handled, [
        ('protocol_version', []),
        ('name', []),
        ('version', []),
        ('known_command', ['gomill-describe_engine']),
        ('known_command', ['b_only']),
        ('test', []),
        ('b_only', []),
        ('error', []),
        ('b_only', []),
        ('known_command', ['error']),
        ('error', []),
        ('quit', []),
        ])
    tc.assertEqual(channel2.engine.commands_handled, [
        ('name', []),
        ('version', []),
        ('known_command', ['gomill-describe_engine']),
        ('known_command', ['b_only']),
        ('test', ['abc', 'def']),
        ('b_only', []),
        ('quit', []),
        ])

def test_game_controller_same_player_code(tc):
    tc.assertRaisesRegexp(ValueError, "^player codes must be distinct$",
                          gtp_controller.Game_controller, 'one', 'one')

def test_game_controller_blocking_consistency(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.Mock_nonblocking_subprocess_gtp_channel(
        ['testw', 'id=two'], gang=set())
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two', nonblocking=True)
    with tc.assertRaises(ValueError) as ar:
        gc.set_player_controller('b', controller1)
    tc.assertEqual(str(ar.exception), "channel must be nonblocking")
    with tc.assertRaises(ValueError) as ar:
        gc.set_player_controller('w', controller2)
    tc.assertEqual(str(ar.exception), "channel has the wrong gang")
    gc2 = gtp_controller.Game_controller('one', 'two')
    with tc.assertRaises(ValueError) as ar:
        gc2.set_player_controller('w', controller2)
    tc.assertEqual(str(ar.exception), "channel must be blocking")

def test_game_controller_partial_close(tc):
    # checking close() works even if one or both players didn't start

    channel = gtp_engine_fixtures.get_test_channel()
    controller = Gtp_controller(channel, 'player one')

    gc1 = gtp_controller.Game_controller('one', 'two')
    gc1.close_players()
    tc.assertIsNone(gc1.describe_late_errors())

    gc2 = gtp_controller.Game_controller('one', 'two')
    gc2.set_player_controller('w', controller)
    gc2.close_players()
    tc.assertIsNone(gc2.describe_late_errors())
    tc.assertIs(controller.channel_is_closed, True)

def test_game_controller_repeated_close(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    channel1.fail_close = True
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)
    gc.close_players()
    tc.assertEqual(gc.describe_late_errors(),
                   "error closing player one:\n"
                   "forced failure for close")
    gc.close_players()
    tc.assertEqual(gc.describe_late_errors(),
                   "error closing player one:\n"
                   "forced failure for close")

def test_game_controller_engine_descriptions(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    channel1.engine.add_command('name', lambda args:"some-name")
    channel1.engine.add_command('version', lambda args:"v123")
    channel1.engine.add_command('gomill-describe_engine',
                                lambda args:"foo\nbar")
    channel2.engine.force_error('gomill-describe_engine')
    gc = gtp_controller.Game_controller('one', 'two')

    # This isn't documented behaviour
    tc.assertEqual(gc.engine_descriptions, {'b' : None, 'w' : None})

    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)

    tc.assertEqual(gc.engine_descriptions['b'].raw_name, "some-name")
    tc.assertEqual(gc.engine_descriptions['b'].raw_version, "v123")
    tc.assertEqual(gc.engine_descriptions['b'].description, "foo\nbar")
    tc.assertIsNone(gc.engine_descriptions['w'].raw_name)
    tc.assertIsNone(gc.engine_descriptions['w'].raw_version)
    tc.assertIsNone(gc.engine_descriptions['w'].description)

def test_game_controller_protocol_version(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel1.engine.add_command('protocol_version', lambda args:"3")
    gc = gtp_controller.Game_controller('one', 'two')
    with tc.assertRaises(BadGtpResponse) as ar:
        gc.set_player_controller('b', controller1)
    tc.assertEqual(str(ar.exception),
                   "player one reports GTP protocol version 3")
    tc.assertIs(gc.get_controller('b'), controller1)

def test_game_controller_channel_errors(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)

    channel1.fail_command = "test"
    with tc.assertRaises(GtpTransportError) as ar:
        gc.send_command('b', 'test')
    tc.assertEqual(
        str(ar.exception),
        "transport error sending 'test' to player one:\n"
        "forced failure for send_command_line")

    channel2.fail_command = "list_commands"
    with tc.assertRaises(GtpTransportError) as ar:
        gc.maybe_send_command('w', 'list_commands')
    tc.assertEqual(
        str(ar.exception),
        "transport error sending 'list_commands' to player two:\n"
        "forced failure for send_command_line")

    channel2.fail_command = "known_command"
    with tc.assertRaises(GtpTransportError) as ar:
        gc.known_command('w', 'test')
    tc.assertEqual(
        str(ar.exception),
        "transport error sending 'known_command test' to player two:\n"
        "forced failure for send_command_line")

    channel1.fail_close = True
    gc.close_players()
    tc.assertEqual(gc.describe_late_errors(),
                   "error closing player one:\n"
                   "forced failure for close")

def test_game_controller_cautious_mode(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)
    tc.assertIs(gc.in_cautious_mode, False)
    gc.set_cautious_mode(True)
    tc.assertIs(gc.in_cautious_mode, True)

    channel1.fail_command = "list_commands"
    tc.assertEqual(gc.maybe_send_command('b', 'test'), "test response")
    tc.assertIsNone(gc.maybe_send_command('b', 'error'))
    tc.assertIsNone(gc.maybe_send_command('b', 'list_commands'))

    channel2.fail_command = "known_command"
    tc.assertEqual(gc.send_command('w', 'test'), "test response")
    tc.assertIs(gc.known_command('w', 'list_commands'), False)

    gc.close_players()
    tc.assertEqual(
        gc.describe_late_errors(),
        "transport error sending 'list_commands' to player one:\n"
        "forced failure for send_command_line\n"
        "transport error sending 'known_command list_commands' to player two:\n"
        "forced failure for send_command_line")

def test_game_controller_cautious_mode_send_command(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)
    gc.set_cautious_mode(True)

    channel1.fail_command = "list_commands"
    tc.assertEqual(gc.send_command('b', 'test'), "test response")
    with tc.assertRaises(BadGtpResponse) as ar:
        gc.send_command('b', 'list_commands')
    tc.assertEqual(
        str(ar.exception),
        "late low-level error from player one")
    tc.assertIsNone(ar.exception.gtp_command)
    gc.close_players()
    tc.assertEqual(
        gc.describe_late_errors(),
        "transport error sending 'list_commands' to player one:\n"
        "forced failure for send_command_line")

def test_game_controller_leave_cautious_mode(tc):
    channel1 = gtp_engine_fixtures.get_test_channel()
    controller1 = Gtp_controller(channel1, 'player one')
    channel2 = gtp_engine_fixtures.get_test_channel()
    controller2 = Gtp_controller(channel2, 'player two')
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_controller('b', controller1)
    gc.set_player_controller('w', controller2)

    channel1.fail_command = "list_commands"
    gc.set_cautious_mode(True)
    tc.assertIs(gc.in_cautious_mode, True)
    tc.assertEqual(gc.send_command('b', 'test'), "test response")
    gc.set_cautious_mode(False)
    tc.assertIs(gc.in_cautious_mode, False)
    with tc.assertRaises(GtpTransportError) as ar:
        gc.send_command('b', 'list_commands')
    tc.assertEqual(
        str(ar.exception),
        "transport error sending 'list_commands' to player one:\n"
        "forced failure for send_command_line")

def test_game_controller_get_gtp_cpu_times(tc):
    def controller1():
        channel = gtp_engine_fixtures.get_test_channel()
        return Gtp_controller(channel, 'notimplemented')
    def controller2():
        channel = gtp_engine_fixtures.get_test_channel()
        channel.engine.add_command('gomill-cpu_time', lambda args:"3.525")
        return Gtp_controller(channel, 'good')
    def controller3():
        channel = gtp_engine_fixtures.get_test_channel()
        channel.engine.add_command('gomill-cpu_time', lambda args:"invalid")
        return Gtp_controller(channel, 'bad')
    def controller4():
        channel = gtp_engine_fixtures.get_test_channel()
        channel.engine.force_error('gomill-cpu_time')
        return Gtp_controller(channel, 'error')
    def controller5():
        channel = gtp_engine_fixtures.get_test_channel()
        channel.engine.force_fatal_error('gomill-cpu_time')
        return Gtp_controller(channel, 'fatalerror')

    gc1 = gtp_controller.Game_controller('x', 'y')
    gc1.set_player_controller('b', controller1())
    gc1.set_player_controller('w', controller2())
    tc.assertEqual(gc1.get_gtp_cpu_times(), ({'w': 3.525}, set([])))

    gc2 = gtp_controller.Game_controller('x', 'y')
    gc2.set_player_controller('b', controller3())
    gc2.set_player_controller('w', controller2())
    tc.assertEqual(gc2.get_gtp_cpu_times(), ({'w': 3.525}, set(['b'])))

    gc3 = gtp_controller.Game_controller('x', 'y')
    gc3.set_player_controller('b', controller3())
    gc3.set_player_controller('w', controller4())
    tc.assertEqual(gc3.get_gtp_cpu_times(), ({}, set(['b', 'w'])))

    gc4 = gtp_controller.Game_controller('x', 'y')
    gc4.set_player_controller('b', controller2())
    gc4.set_player_controller('w', controller5())
    tc.assertEqual(gc4.get_gtp_cpu_times(), ({'b' : 3.525}, set(['w'])))
    gc4.close_players()
    tc.assertEqual(gc4.describe_late_errors(),
                   "error sending 'quit' to fatalerror:\n"
                   "engine has closed the command channel")

    gc5 = gtp_controller.Game_controller('x', 'y')
    gc5.set_player_controller('b', controller1())
    gc5.set_player_controller('w', controller2())
    gc5.set_cautious_mode(True)
    gc5.get_controller('w').channel.fail_command = 'gomill-cpu_time'
    tc.assertEqual(gc5.get_gtp_cpu_times(), ({}, set(['w'])))
    gc5.close_players()
    tc.assertEqual(gc5.describe_late_errors(),
                   "transport error sending 'gomill-cpu_time' to good:\n"
                   "forced failure for send_command_line")

    gc6 = gtp_controller.Game_controller('x', 'y')
    gc6.set_player_controller('b', controller1())
    gc6.set_player_controller('w', controller2())
    gc6.get_controller('w').channel.fail_command = 'gomill-cpu_time'
    with tc.assertRaises(GtpTransportError) as ar:
        gc6.get_gtp_cpu_times()
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'gomill-cpu_time' to good:\n"
                   "forced failure for send_command_line")
    gc6.close_players()
    tc.assertIsNone(gc6.describe_late_errors())

def test_game_controller_set_player_subprocess(tc):
    msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    engine = gtp_engine_fixtures.get_test_engine()
    engine.add_command("name", lambda args:'blackplayer')
    msf.register_engine('named', engine)
    gc = gtp_controller.Game_controller('one', 'two')
    gc.set_player_subprocess('b', ['testb', 'id=one', 'engine=named'],
                             check_protocol_version=False)
    gc.set_player_subprocess('w', ['testw', 'id=two'], env={'a':'b'})

    tc.assertEqual(gc.get_controller('b').name, "player one")
    tc.assertEqual(gc.get_controller('w').name, "player two")

    tc.assertEqual(gc.engine_descriptions['b'].raw_name, "blackplayer")
    tc.assertIsNone(gc.engine_descriptions['w'].raw_name)

    channel1 = msf.get_channel('one')
    channel2 = msf.get_channel('two')
    tc.assertIsNone(gc.gang)
    tc.assertFalse(channel1.is_nonblocking)
    tc.assertEqual(channel1.engine.commands_handled[0][0], 'name')
    tc.assertIsNone(channel1.requested_env)
    tc.assertFalse(channel2.is_nonblocking)
    tc.assertEqual(channel2.engine.commands_handled[0][0], 'protocol_version')
    tc.assertEqual(channel2.requested_env, {'a': 'b'})

    gc.close_players()
    tc.assertEqual(gc.get_resource_usage_cpu_times(),
                   {'b': 546.2, 'w': 567.2})

def test_game_controller_set_player_subprocess_error(tc):
    msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    gc = gtp_controller.Game_controller('one', 'two')
    with tc.assertRaises(GtpChannelError) as ar:
        gc.set_player_subprocess('b', ['testb', 'fail=startup'])
    tc.assertEqual(
        str(ar.exception),
        "error starting subprocess for player one:\nexec forced to fail")
    tc.assertRaises(KeyError, gc.get_controller, 'b')
    tc.assertEqual(gc.get_resource_usage_cpu_times(), {'b' : None, 'w' : None})

def test_game_controller_set_player_subprocess_stderr(tc):
    # This is mostly testing that the code for Mock_subprocess_fixture
    # and requested_stderr is working.
    fake_file = object()
    msf = gtp_engine_fixtures.Mock_subprocess_fixture(tc)
    engine = gtp_engine_fixtures.get_test_engine()
    gc = gtp_controller.Game_controller('one', 'two', nonblocking=True)
    gc.set_player_subprocess('b', ['testb', 'id=one'], stderr=fake_file)
    gc.set_player_subprocess('w', ['testw', 'id=two'], stderr="capture")
    channel1 = msf.get_channel('one')
    channel2 = msf.get_channel('two')
    tc.assertTrue(channel1.is_nonblocking)
    tc.assertIs(channel1.requested_stderr, fake_file)
    tc.assertTrue(channel2.is_nonblocking)
    tc.assertEqual(channel2.requested_stderr, "capture")
    tc.assertIs(channel1.requested_gang, gc.gang)
    tc.assertIs(channel1.requested_gang, gc.gang)
    gc.close_players()

def test_game_controller_capture_without_nonblocking(tc):
    # Note no Mock_subprocess_fixture here
    gc = gtp_controller.Game_controller('one', 'two')
    with tc.assertRaises(ValueError) as ar:
        gc.set_player_subprocess('b', ['testb', 'id=one'], stderr="capture")
