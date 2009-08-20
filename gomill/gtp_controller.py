"""Go Text Protocol support (controller side).

Based on GTP 'draft version 2' (see <http://www.lysator.liu.se/~gunnar/gtp/>).

"""

import os
import re
import signal
import subprocess

from gomill.gtp import interpret_boolean


class GtpProtocolError(StandardError):
    """Engine returned an ill-formed response."""

class GtpTransportError(StandardError):
    """Error communicating with the engine."""

class GtpEngineError(StandardError):
    """Error response from the engine."""


_command_characters_re = re.compile(r"\A[\x21-\x7e\x80-\xff]+\Z")
_remove_response_controls_re = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

class Gtp_channel(object):
    """A communication channel to a GTP engine.

    public attributes:
      resource_usage

    resource_usage describes the engine's resource usage (see
    resource.getrusage() for the format). It is None if not available. In
    practice, it's only available for subprocess-based channels, and only after
    they've been closed.

    """

    def send_command(self, command, arguments):
        """Send a GTP command over the channel.

        command   -- string
        arguments -- list of strings

        May raise GtpTransportError

        """
        if not _command_characters_re.search(command):
            raise ValueError("bad character in command")
        for argument in arguments:
            if not _command_characters_re.search(argument):
                raise ValueError("bad character in argument")
        self.send_command_impl(command, arguments)

    def get_response(self):
        """Read a GTP response from the channel.

        Waits indefinitely for the response.

        Returns a pair (is_error_response, response)

        'is_error_response' is a bool indicating whether the engine returned a
        success or an error response.

        For a success response, 'response' is the result from the engine; for an
        error response it's the error message from the engine.

        'response' is a string with no trailing whitespace. It may contain
        newlines, but there are no empty lines except perhaps the first. There
        is no leading whitespace on the first line.

        May raise GtpTransportError

        May raise GtpProtocolError (eg if the error status can't be read from
        the engine's response).

        """
        return self.get_response_impl()

    # For subclasses to override:

    def close(self):
        """Close the channel.

        Channel implementations may use this to clean up resources associated
        with the engine (eg, to terminate a subprocess).

        May raise GtpTransportError if a serious error is detected while doing
        this.

        """
        pass

    def send_command_impl(self, command, arguments):
        raise NotImplementedError

    def get_response_impl(self):
        raise NotImplementedError


class Internal_gtp_channel(Gtp_channel):
    """A GTP channel connected to an in-process Python GTP engine.

    Instantiate with a Gtp_engine_protocol object.

    This waits to invoke the engine's handler for each command until the
    correponding response is requested.

    """
    def __init__(self, engine):
        self.engine = engine
        self.outstanding_commands = []
        self.session_is_ended = False
        self.resource_usage = None

    def send_command_impl(self, command, arguments):
        if self.session_is_ended:
            raise GtpTransportError("engine has ended the session")
        self.outstanding_commands.append((command, arguments))

    def get_response_impl(self):
        if self.session_is_ended:
            raise GtpTransportError("engine has ended the session")
        try:
            command, arguments = self.outstanding_commands.pop(0)
        except IndexError:
            raise GtpTransportError("no outstanding commands")
        is_error, response, end_session = \
            self.engine.run_command(command, arguments)
        if end_session:
            self.session_is_ended = True
        return is_error, response


class Linebased_gtp_channel(Gtp_channel):
    """Generic Gtp_channel based on line-by-line communication."""

    # Not using command ids; I don't see the need unless we see problems in
    # practice with engines getting out of sync.

    def send_command_impl(self, command, arguments):
        words = [command] + arguments
        self.send_command_line(" ".join(words) + "\n")

    def get_response_impl(self):
        """Obtain response according to GTP protocol.

        If we receive EOF before any data, we raise GtpTransportError (the
        engine has probably gone away).

        Otherwise if we receive EOF, we use the data received anyway.

        """
        lines = []
        seen_data = False
        while True:
            s = self.get_response_line()
            # << Empty lines and lines with only whitespace sent by the engine
            #    and occuring outside a response must be ignored by the
            #    controller >>
            if not seen_data:
                if s.strip() == "":
                    if s.endswith("\n"):
                        continue
                    else:
                        break
                else:
                    seen_data = True
            if s == "\n":
                break
            lines.append(s)
            if not s.endswith("\n"):
                break
        if not lines:
            raise GtpTransportError("EOF and empty response")
        first_line = lines[0]
        # It's certain that first line isn't empty
        if first_line[0] == "?":
            is_error = True
        elif first_line[0] == "=":
            is_error = False
        else:
            raise GtpProtocolError(
                "no success/failure indication from engine: "
                "first line is `%s`" % first_line)
        lines[0] = first_line[1:].lstrip()
        response = "".join(lines).rstrip()
        response = _remove_response_controls_re.sub("", response)
        response = response.replace("\t", " ")
        return is_error, response


    # For subclasses to override:

    def send_command_line(self, command):
        """Send a line of text over the channel.

        command -- string terminated by a newline.

        May raise GtpTransportError

        """
        raise NotImplementedError

    def get_response_line(self):
        """Read a line of text from the channel.

        May raise GtpTransportError

        The result ends in a newline unless end-of-file was seen (ie, the same
        protocol to indicate end-of-file as Python's readline()).

        """
        raise NotImplementedError


def permit_sigpipe():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

class Subprocess_gtp_channel(Linebased_gtp_channel):
    """A GTP channel to a subprocess.

    Instantiate with
      command -- list of strings (as for subprocess.Popen)

    This starts the subprocess and speaks GTP over its standard input and
    output.

    The subprocess's standard error is left as the standard error of the calling
    process.

    """
    def __init__(self, command):
        try:
            p = subprocess.Popen(command,
                                 preexec_fn=permit_sigpipe, close_fds=True,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except EnvironmentError, e:
            raise GtpTransportError(str(e))
        self.subprocess = p
        self.command_pipe = p.stdin
        self.response_pipe = p.stdout
        self.resource_usage = None

    def send_command_line(self, command):
        try:
            self.command_pipe.write(command)
            self.command_pipe.flush()
        except EnvironmentError, e:
            raise GtpTransportError(str(e))

    def get_response_line(self):
        try:
            return self.response_pipe.readline()
        except EnvironmentError, e:
            raise GtpTransportError(str(e))

    def close(self):
        # Ideally would give up waiting after a while and forcibly terminate the
        # subprocess.
        try:
            self.command_pipe.close()
            # We don't care about the exit status, but we do want to be sure it
            # isn't still running.
            pid, exit_status, rusage = os.wait4(self.subprocess.pid, 0)
        except EnvironmentError, e:
            raise GtpTransportError(str(e))
        self.resource_usage = rusage


class Gtp_controller_protocol(object):
    """Implementation of the controller side of the GTP protocol.

    One controller can be in communication with an arbitrary number of engines,
    each with its own communication channel.

    """
    def __init__(self):
        self.channels = {}
        self.known_commands = {}

    def add_channel(self, channel_id, channel):
        """Register a communication channel.

        channel_id -- string
        channel    -- Gtp_channel

        """
        if channel_id in self.channels:
            raise ValueError("channel %s already registered" % channel_id)
        self.channels[channel_id] = channel

    def do_command(self, channel_id, command, *arguments):
        """Send a command over a channel and return the response.

        channel_id -- string
        command    -- string (command name)
        arguments  -- strings

        Returns the result text from the engine as a string with no leading or
        trailing whitespace. (This doesn't include the leading =[id] bit.)

        If the engine returns an error response, raises GtpEngineError with the
        error message as exception parameter.

        This will wait indefinitely for the channel to produce the response.

        Raises GtpProtocolError if the engine's response is too mangled to be
        returned.

        Raises GtpTransportError if there was an error from the communication
        layer between the controller and the engine (which may well mean that
        the engine has gone away).

        """
        channel = self.channels[channel_id]
        channel.send_command(command, list(arguments))
        is_error, response = channel.get_response()
        if is_error:
            raise GtpEngineError(response)
        return response

    def known_command(self, channel_id, command):
        """Check whether 'command' is known for a channel.

        This sends 'known_command' the first time it's asked, then caches the
        result.

        If known_command fails, returns False.

        """
        result = self.known_commands.get((channel_id, command))
        if result is not None:
            return result
        try:
            response = self.do_command(channel_id, "known_command", command)
        except GtpEngineError:
            known = False
        else:
            known = interpret_boolean(response)
        self.known_commands[channel_id, command] = known
        return known

    def close_channel(self, channel_id):
        """Close and deregister the specified channel.

        channel_id -- string

        May raise GtpTransportError

        Returns the channel's resource usage (see resource.getrusage() for the
        format), or None if not available.

        """
        channel = self.channels.pop(channel_id)
        channel.close()
        return channel.resource_usage

    def has_channel(self, channel_id):
        """Check whether a channel id is currently registered.

        channel_id -- string

        """
        return channel_id in self.channels

