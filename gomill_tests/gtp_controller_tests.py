"""Tests for gtp_controller.py"""

from gomill_tests import gomill_test_support

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Mock_gmp_channel(gtp_controller.Linebased_gtp_channel):
    """A Linebased_gtp_channel that simulates talking to a GMP engine."""
    def __init__(self):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.closed = False
        self.bytes_sent = 0

    def send_command_line(self, command):
        pass

    def get_response_line(self):
        if self.closed:
            raise GtpTransportError("pipe is closed")
        raise StandardError("requested a full line; this will hang")

    def get_response_byte(self):
        if self.closed:
            raise GtpTransportError("pipe is closed")
        packet = "\x01\xa1\xa0\x80"
        result = packet[self.bytes_sent]
        self.bytes_sent += 1
        return result

    def close(self):
        self.closed = True

def test_gmp(tc):
    channel = Mock_gmp_channel()
    controller = gtp_controller.Gtp_controller(channel, "test-gmp")
    with tc.assertRaises(GtpProtocolError) as ar:
        controller.check_protocol_version()
    tc.assertIn("engine appears to be speaking GMP", str(ar.exception))

