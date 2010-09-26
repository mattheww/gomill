import errno
from cStringIO import StringIO

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

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
            raise StandardError("read called with no data; this would hang")
        return result

    def readline(self):
        if self.is_broken:
            return ""
        result = self.source.readline()
        if self.hangs_before_eof and not result.endswith("\n"):
            raise StandardError(
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
