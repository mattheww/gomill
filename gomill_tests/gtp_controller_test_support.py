import errno
from cStringIO import StringIO

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)
from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError


class SupporterError(StandardError):
    """Exception raised by support objects when something goes wrong.

    This is raised to indicate things like sequencing errors detected by mock
    objects.

    """

class Mock_writing_pipe(object):
    """Mock writeable pipe object, with an interface like a cStringIO.

    If this is 'broken', it raises IOError(EPIPE) on any further writes.

    """
    def __init__(self):
        self.sink = StringIO()
        self.is_broken = False

    def write(self, s):
        if self.is_broken:
            raise IOError(errno.EPIPE, "Broken pipe")
        try:
            self.sink.write(s)
        except ValueError, e:
            raise IOError(errno.EIO, str(e))

    def flush(self):
        self.sink.flush()

    def close(self):
        self.sink.close()

    def simulate_broken_pipe(self):
        self.is_broken = True

    def getvalue(self):
        return self.sink.getvalue()


class Mock_reading_pipe(object):
    """Mock readable pipe object, with an interface like a cStringIO.

    Instantiate with the data to provide on the pipe.

    If this is 'broken', it always returns EOF from that point on.

    Set the attribute hangs_before_eof true to simulate a pipe that isn't closed
    when it runs out of data.

    """
    def __init__(self, response):
        self.source = StringIO(response)
        self.is_broken = False
        self.hangs_before_eof = False

    def read(self, n):
        if self.is_broken:
            return ""
        result = self.source.read(n)
        if self.hangs_before_eof and result == "":
            raise SupporterError("read called with no data; this would hang")
        return result

    def readline(self):
        if self.is_broken:
            return ""
        result = self.source.readline()
        if self.hangs_before_eof and not result.endswith("\n"):
            raise SupporterError(
                "readline called with no newline; this would hang")
        return result

    def close(self):
        self.source.close()

    def simulate_broken_pipe(self):
        self.is_broken = True


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
        self.command_pipe = Mock_writing_pipe()
        self.response_pipe = Mock_reading_pipe(response)
        self.response_pipe.hangs_before_eof = hangs_before_eof
        #raise GtpChannelError(s)

    def close(self):
        self.command_pipe.close()
        self.response_pipe.close()
        #self.resource_usage = rusage
        #raise GtpTransportError("\n".join(errors))

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
      fail_next_response  -- bool (get_response_line raises GtpTransportError)
      force_next_response -- string (get_response_line uses this string)

    """
    def __init__(self, engine):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.engine = engine
        self.stored_response = ""
        self.session_is_ended = False
        self.engine_exit_breaks_commands = True
        self.fail_next_command = False
        self.fail_next_response = False
        self.force_next_response = None

    def send_command_line(self, command):
        if self.stored_response != "":
            raise SupporterError("two commands in a row")
        if self.session_is_ended:
            if self.engine_exit_breaks_commands:
                raise GtpChannelClosed("engine has closed the command channel")
            return
        if self.fail_next_command:
            self.fail_next_command = False
            raise GtpTransportError("forced failure for send_command_line")
        cmd_list = command.strip().split(" ")
        is_error, response, end_session = \
            self.engine.run_command(cmd_list[0], cmd_list[1:])
        if end_session:
            self.session_is_ended = True
        self.stored_response = ("? " if is_error else "= ") + response + "\n\n"

    def get_response_line(self):
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
        # Should support triggering GtpTransportError
        # Should set resource usage
        pass


def get_test_engine():
    """Return a Gtp_engine_protocol useful for testing controllers."""

    def handle_test(args):
        return "test response"

    def handle_multiline(args):
        return "first line  \n  second line\nthird line"

    def handle_error(args):
        raise GtpError("normal error")

    def handle_fatal_error(args):
        raise GtpFatalError("fatal error")

    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('test', handle_test)
    engine.add_command('multiline', handle_multiline)
    engine.add_command('error', handle_error)
    engine.add_command('fatal', handle_fatal_error)
    return engine

def get_test_channel():
    """Return a Gtp_channel for use with the test engine."""
    engine = get_test_engine()
    return Testing_gtp_channel(engine)

