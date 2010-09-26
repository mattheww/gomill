from cStringIO import StringIO

from gomill import gtp_controller
from gomill.gtp_controller import (
    GtpChannelError, GtpProtocolError, GtpTransportError, GtpChannelClosed,
    BadGtpResponse)

class Preprogrammed_gtp_channel(gtp_controller.Linebased_gtp_channel):
    """A Linebased_gtp_channel with preprogrammed response stream.

    Instantiate with a string containing the complete response stream.

    This will send the contents of the response stream, irrespective of what
    commands are received.

    The command stream is available from get_command_stream().

    """
    def __init__(self, response):
        gtp_controller.Linebased_gtp_channel.__init__(self)
        self.command_pipe = StringIO()
        self.response_pipe = StringIO(response)
        #raise GtpChannelError(s)


    # These send and get methods should resemble those from
    # Subprocess_gtp_channel as much as possible.

    def send_command_line(self, command):
        try:
            self.command_pipe.write(command)
            self.command_pipe.flush()
        except Exception, e:
            if "I/O operation on closed file" in str(e):
                raise GtpChannelClosed("engine has closed the command channel")
            else:
                raise GtpTransportError(str(e))

    def get_response_line(self):
        try:
            return self.response_pipe.readline()
        except StandardError, e:
            raise GtpTransportError(str(e))

    def get_response_byte(self):
        try:
            return self.response_pipe.read(1)
        except StandardError, e:
            raise GtpTransportError(str(e))

    def close(self):
        self.command_pipe.close()
        self.response_pipe.close()
        #self.resource_usage = rusage
        #raise GtpTransportError("\n".join(errors))

    def get_command_stream(self):
        """Return the complete contents of the command stream sent so far."""
        return self.command_pipe.getvalue()

    def close_command_stream(self):
        """Forcibly close the command stream."""
        self.command_pipe.close()
