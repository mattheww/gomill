"""Tests for gtp_controller.py"""

from gomill_tests import gomill_test_support
from gomill_tests.gtp_controller_test_support import Preprogrammed_gtp_channel

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


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
    channel = Preprogrammed_gtp_channel("= 2\n\n? unknown command\n\n")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.send_command("xyzzy", ["1", "2"])
    tc.assertEqual(channel.get_response(), (True, "unknown command"))

def test_linebased_channel_response_cleaning(tc):
    channel = Preprogrammed_gtp_channel(
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
        # all this at once, in a failure response
        "?    a\raa  \r\n  b\rbb\tcc\x01c\nddd  \t  \n\n"
        )
    tc.assertEqual(channel.get_response(), (False, "1abcde"))
    tc.assertEqual(channel.get_response(), (False, "2abcde"))
    tc.assertEqual(channel.get_response(), (False, "3abcde"))
    tc.assertEqual(channel.get_response(), (False, "4abc de"))
    tc.assertEqual(channel.get_response(), (False, "5abcde"))
    tc.assertEqual(channel.get_response(), (False, "6abcde"))
    tc.assertEqual(channel.get_response(), (False, "7aaa  \n  bbb ccc\nddd"))
    tc.assertEqual(channel.get_response(), (True, "aaa  \n  bbb ccc\nddd"))

def test_linebased_channel_without_response(tc):
    channel = Preprogrammed_gtp_channel("")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_usage_message(tc):
    channel = Preprogrammed_gtp_channel(
        "Usage: randomprogram [options]\n\nOptions:\n"
        "--help   show this help message and exit\n")
    channel.send_command("protocol_version", [])
    tc.assertRaisesRegexp(
        GtpProtocolError, "^engine isn't speaking GTP: first byte is 'U'$",
        channel.get_response)
    channel.close()

def test_linebased_channel_with_gmp_response(tc):
    channel = Preprogrammed_gtp_channel("\x01\xa1\xa0\x80")
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

def test_linebase_channel_with_broken_response_pipe(tc):
    channel = Preprogrammed_gtp_channel("= 2\n\n? unreached\n\n")
    channel.send_command("protocol_version", [])
    tc.assertEqual(channel.get_response(), (False, "2"))
    channel.break_response_stream()
    channel.send_command("list_commands", [])
    tc.assertRaisesRegexp(
        GtpChannelClosed, "^engine has closed the response channel$",
        channel.get_response)
    channel.close()
