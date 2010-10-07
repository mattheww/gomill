"""Support code for gtp_controller_tests.

This is also used by gtp_engine_fixtures (and so by gtp proxy tests).

"""

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

from gomill_tests import test_support
from gomill_tests.test_framework import SupporterError


class Preprogrammed_gtp_channel(gtp_controller.Subprocess_gtp_channel):
    """A Linebased_gtp_channel with hardwired response stream.

    Instantiate with a string containing the complete response stream.

    This sends the contents of the response stream, irrespective of what
    commands are received.

    Pass hangs_before_eof True to simulate an engine that doesn't close its
    response pipe when the preprogrammed response data runs out.

    The command stream is available from get_command_stream().

    """
    def __init__(self, response, hangs_before_eof=False):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.command_pipe = test_support.Mock_writing_pipe()
        self.response_pipe = test_support.Mock_reading_pipe(response)
        self.response_pipe.hangs_before_eof = hangs_before_eof

    def close(self):
        self.command_pipe.close()
        self.response_pipe.close()

    def get_command_stream(self):
        """Return the complete contents of the command stream sent so far."""
        return self.command_pipe.getvalue()

    def break_command_stream(self):
        """Break the simulated pipe for the command stream."""
        self.command_pipe.simulate_broken_pipe()

    def break_response_stream(self):
        """Break the simulated pipe for the response stream."""
        self.response_pipe.simulate_broken_pipe()


class Testing_gtp_channel(gtp_controller.Linebased_gtp_channel):
    """Linebased GTP channel that runs an internal Gtp_engine.

    Instantiate with a Gtp_engine_protocol object.

    This is used for testing how controllers handle GtpChannelError.

    Public attributes:
      engine    -- the engine it was instantiated with
      is_closed -- bool (closed() has been called without a forced error)

    This raises an error if sent two commands without requesting a response in
    between, or if asked for a response when no command was sent since the last
    response. (GTP permits stacking up commands, but Gtp_controller should never
    do it, so we want to report it).

    Unlike Internal_gtp_channel, this runs the command as the point when it is
    sent.

    If you send a command after the engine has exited, this raises
    GtpChannelClosed. Set the attribute engine_exit_breaks_commands to False to
    disable this behaviour (it will ignore the command and respond with EOF
    instead).

    You can force errors by setting the following attributes:
      fail_next_command   -- bool (send_command_line raises GtpTransportError)
      fail_command        -- string (like fail_next_command, if command line
                             starts with this string)
      fail_next_response  -- bool (get_response_line raises GtpTransportError)
      force_next_response -- string (get_response_line uses this string)
      fail_close          -- bool (close raises GtpTransportError)

    """
    def __init__(self, engine):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.engine = engine
        self.stored_response = ""
        self.session_is_ended = False
        self.is_closed = False
        self.engine_exit_breaks_commands = True
        self.fail_next_command = False
        self.fail_next_response = False
        self.force_next_response = None
        self.fail_close = False
        self.fail_command = None

    def send_command_line(self, command):
        if self.is_closed:
            raise SupporterError("channel is closed")
        if self.stored_response != "":
            raise SupporterError("two commands in a row")
        if self.session_is_ended:
            if self.engine_exit_breaks_commands:
                raise GtpChannelClosed("engine has closed the command channel")
            return
        if self.fail_next_command:
            self.fail_next_command = False
            raise GtpTransportError("forced failure for send_command_line")
        if self.fail_command and command.startswith(self.fail_command):
            self.fail_command = None
            raise GtpTransportError("forced failure for send_command_line")
        cmd_list = command.strip().split(" ")
        is_error, response, end_session = \
            self.engine.run_command(cmd_list[0], cmd_list[1:])
        if end_session:
            self.session_is_ended = True
        self.stored_response = ("? " if is_error else "= ") + response + "\n\n"

    def get_response_line(self):
        if self.is_closed:
            raise SupporterError("channel is closed")
        if self.stored_response == "":
            if self.session_is_ended:
                return ""
            raise SupporterError("response request without command")
        if self.fail_next_response:
            self.fail_next_response = False
            raise GtpTransportError("forced failure for get_response_line")
        if self.force_next_response is not None:
            self.stored_response = self.force_next_response
            self.force_next_response = None
        line, self.stored_response = self.stored_response.split("\n", 1)
        return line + "\n"

    def close(self):
        if self.fail_close:
            raise GtpTransportError("forced failure for close")
        self.is_closed = True

