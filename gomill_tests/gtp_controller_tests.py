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
