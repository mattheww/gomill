"""Tests for gtp_controller.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_gmp(tc):
    channel = gtp_controller_test_support.Mock_gmp_channel()
    controller = gtp_controller.Gtp_controller(channel, "test-gmp")
    with tc.assertRaises(GtpProtocolError) as ar:
        controller.check_protocol_version()
    tc.assertIn("engine appears to be speaking GMP", str(ar.exception))


def test_linebased_channel(tc):
    channel = gtp_controller_test_support.Preprogrammed_gtp_channel(
        "=\n\n=\n\n")
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

