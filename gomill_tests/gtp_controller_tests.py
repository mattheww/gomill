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


class Mock_gtp_channel(gtp_controller.Linebased_gtp_channel):
    """A Linebased_gtp_channel with preprogrammed responses."""
    def __init__(self, responses):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.last_command_line = None
        self.response_lines = []
        for s in responses:
            self.response_lines.append(s+"\n")
            self.response_lines.append("\n")
        #raise GtpChannelError(s)

    def send_command_line(self, command):
        self.last_command_line = command
        #raise GtpChannelClosed("engine has closed the command channel")
        #raise GtpTransportError(str(e))

    def get_response_line(self):
        if self.last_command_line is None:
            raise StandardError("no command sent; this will hang")
        return self.response_lines.pop(0)
        #raise GtpTransportError(str(e))

    def get_response_byte(self):
        if self.last_command_line is None:
            raise StandardError("no command sent; this will hang")
        s = self.response_lines.pop(0)
        result = s[0]
        if len(s) > 1:
            self.response_lines[:0] = [s[1:]]
        return result
        #raise GtpTransportError(str(e))

    def close(self):
        pass
        #self.resource_usage = rusage
        #raise GtpTransportError("\n".join(errors))

def test_linebased_channel(tc):
    channel = Mock_gtp_channel(["=", "="])
    tc.assertEqual(channel.last_command_line, None)
    channel.send_command("play", ["b", "a3"])
    tc.assertEqual(channel.last_command_line, "play b a3\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.send_command("quit", [])
    tc.assertEqual(channel.last_command_line, "quit\n")
    tc.assertEqual(channel.get_response(), (False, ""))
    channel.close()
