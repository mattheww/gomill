"""Go Text Protocol support (controller side).

Based on GTP 'draft version 2' (see <http://www.lysator.liu.se/~gunnar/gtp/>).

"""

import errno
import os
import re
import signal
import subprocess

from gomill.gomill_common import *


class GtpControllerError(StandardError):
    """Error trying to talk to a GTP engine.

    This is the base class for GtpProtocolError, GtpTransportError,
    GtpChannelClosed, and GtpEngineError.

    """

class GtpProtocolError(GtpControllerError):
    """Engine returned an ill-formed response."""

class GtpTransportError(GtpControllerError):
    """Error communicating with the engine."""

class GtpChannelClosed(GtpControllerError):
    """The (command or response) channel to the engine has been closed."""

class GtpEngineError(GtpControllerError):
    """Error response from the engine."""


_gtp_word_characters_re = re.compile(r"\A[\x21-\x7e\x80-\xff]+\Z")
_remove_response_controls_re = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

def is_well_formed_gtp_word(s):
    """Check whether 's' is well-formed as a single GTP word.

    In particular, this rejects unicode objects and strings contaning spaces.

    """
    if not isinstance(s, str):
        return False
    if not _gtp_word_characters_re.search(s):
        return False
    return True

class Gtp_channel(object):
    """A communication channel to a GTP engine.

    public attributes:
      resource_usage

    resource_usage describes the engine's resource usage (see
    resource.getrusage() for the format). It is None if not available. In
    practice, it's only available for subprocess-based channels, and only after
    they've been closed.

    """
    def __init__(self):
        self.resource_usage = None
        self.log_dest = None
        self.log_prefix = None

    def enable_logging(self, log_dest, prefix=""):
        """Log all messages sent and received over the channel.

        log_dest -- writable file-like object (eg an open file)
        prefix   -- short string to prepend to logged lines

        """
        self.log_dest = log_dest
        self.log_prefix = prefix

    def _log(self, marker, message):
        """Log a message.

        marker  -- string that goes before the log prefix
        message -- string to log

        Swallows all errors.

        """
        try:
            self.log_dest.write(marker + self.log_prefix + message + "\n")
            self.log_dest.flush()
        except StandardError:
            pass

    def send_command(self, command, arguments):
        """Send a GTP command over the channel.

        command   -- string
        arguments -- list of strings

        May raise GtpChannelClosed or GtpTransportError.

        Raises ValueError if the command or an argument contains a character
        forbidden in GTP.

        """
        if not is_well_formed_gtp_word(command):
            raise ValueError("bad command")
        for argument in arguments:
            if not is_well_formed_gtp_word(argument):
                raise ValueError("bad argument")
        if self.log_dest is not None:
            self._log(">>", command + ("".join(" " + a for a in arguments)))
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

        May raise GtpChannelClosed or GtpTransportError.

        May raise GtpProtocolError (eg if the error status can't be read from
        the engine's response).

        """
        result = self.get_response_impl()
        if self.log_dest is not None:
            is_error, response = result
            if is_error:
                response = "? " + response
            else:
                response = "= " + response
            self._log("<<", response.rstrip())
        return result

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
        Gtp_channel.__init__(self)
        self.engine = engine
        self.outstanding_commands = []
        self.session_is_ended = False

    def send_command_impl(self, command, arguments):
        if self.session_is_ended:
            raise GtpChannelClosed("engine has ended the session")
        self.outstanding_commands.append((command, arguments))

    def get_response_impl(self):
        if self.session_is_ended:
            raise GtpChannelClosed("engine has ended the session")
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

    def __init__(self):
        Gtp_channel.__init__(self)
        self.is_first_response = True

    # Not using command ids; I don't see the need unless we see problems in
    # practice with engines getting out of sync.

    def send_command_impl(self, command, arguments):
        words = [command] + arguments
        self.send_command_line(" ".join(words) + "\n")

    def get_response_impl(self):
        """Obtain response according to GTP protocol.

        If we receive EOF before any data, we raise GtpChannelClosed.

        Otherwise if we receive EOF, we use the data received anyway.

        The first time this is called, we check the first byte without reading
        the whole line, and raise GtpProtocolError if it isn't plausibly the
        start of a GTP response (strictly, if it's a control character we should
        just discard it, but I think it's more useful to reject them here).

        """
        lines = []
        seen_data = False
        peeked_byte = None
        if self.is_first_response:
            self.is_first_response = False
            # We read one byte first so that we don't hang if the engine never
            # sends a newline (eg, it's speaking GMP).
            try:
                peeked_byte = self.get_response_byte()
            except NotImplementedError:
                pass
            else:
                if peeked_byte == "":
                    raise GtpChannelClosed(
                        "engine has closed the response channel")
                if peeked_byte == "\x01":
                    raise GtpProtocolError(
                        "engine appears to be speaking GMP, not GTP!")
                # These are the characters which could legitimately start a GTP
                # response. In principle, we should be discarding other controls
                # rather than treating them as errors, but it's more useful to
                # report a protocol error.
                if peeked_byte not in (' ', '\t', '\r', '\n', '#', '=', '?'):
                    raise GtpProtocolError(
                        "engine isn't speaking GTP: "
                        "first byte is %s" % repr(peeked_byte))
                if peeked_byte == "\n":
                    peeked_byte = None
        while True:
            s = self.get_response_line()
            if peeked_byte:
                s = peeked_byte + s
                peeked_byte = None
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
            # Means 'EOF and empty response'
            raise GtpChannelClosed("engine has closed the response channel")
        first_line = lines[0]
        # It's certain that first line isn't empty
        if first_line[0] == "?":
            is_error = True
        elif first_line[0] == "=":
            is_error = False
        else:
            raise GtpProtocolError(
                "no success/failure indication from engine: "
                "first line is `%s`" % first_line.rstrip())
        lines[0] = first_line[1:].lstrip(" \t")
        response = "".join(lines).rstrip()
        response = _remove_response_controls_re.sub("", response)
        response = response.replace("\t", " ")
        return is_error, response


    # For subclasses to override:

    def send_command_line(self, command):
        """Send a line of text over the channel.

        command -- string terminated by a newline.

        May raise GtpChannelClosed or GtpTransportError

        """
        raise NotImplementedError

    def get_response_line(self):
        """Read a line of text from the channel.

        May raise GtpTransportError

        The result ends in a newline unless end-of-file was seen (ie, the same
        protocol to indicate end-of-file as Python's readline()).

        This blocks until a line is available, or end-of-file is reached.

        """
        raise NotImplementedError

    def get_response_byte(self):
        """Read a single byte from the channel.

        May raise GtpTransportError

        This blocks until a byte is available, or end-of-file is reached.

        Subclasses don't have to implement this.

        """
        raise NotImplementedError


def permit_sigpipe():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

class Subprocess_gtp_channel(Linebased_gtp_channel):
    """A GTP channel to a subprocess.

    Instantiate with
      command -- list of strings (as for subprocess.Popen)
      stderr  -- destination for standard error output (optional)
      cwd     -- working directory to change to (optional)
      env     -- new environment (optional)
    Instantiation will raise GtpTransportError if the process can't be started.

    This starts the subprocess and speaks GTP over its standard input and
    output.

    By default, the subprocess's standard error is left as the standard error of
    the calling process. The 'stderr' parameter is interpreted as for
    subprocess.Popen (but don't set it to STDOUT or PIPE).

    The 'cwd' and 'env' parameters are interpreted as for subprocess.Popen.

    """
    def __init__(self, command, stderr=None, cwd=None, env=None):
        Linebased_gtp_channel.__init__(self)
        try:
            p = subprocess.Popen(
                command,
                preexec_fn=permit_sigpipe, close_fds=True,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr, cwd=cwd, env=env)
        except EnvironmentError, e:
            raise GtpTransportError(str(e))
        self.subprocess = p
        self.command_pipe = p.stdin
        self.response_pipe = p.stdout

    def send_command_line(self, command):
        try:
            self.command_pipe.write(command)
            self.command_pipe.flush()
        except EnvironmentError, e:
            if e.errno == errno.EPIPE:
                raise GtpChannelClosed("engine has closed the command channel")
            else:
                raise GtpTransportError(str(e))

    def get_response_line(self):
        try:
            return self.response_pipe.readline()
        except EnvironmentError, e:
            raise GtpTransportError(str(e))

    def get_response_byte(self):
        try:
            return self.response_pipe.read(1)
        except EnvironmentError, e:
            raise GtpTransportError(str(e))

    def close(self):
        # Ideally would give up waiting after a while and forcibly terminate the
        # subprocess.
        try:
            self.command_pipe.close()
            self.response_pipe.close()
            # We don't care about the exit status, but we do want to be sure it
            # isn't still running.
            pid, exit_status, rusage = os.wait4(self.subprocess.pid, 0)
        except EnvironmentError, e:
            raise GtpTransportError(str(e))
        self.resource_usage = rusage


class Gtp_controller_protocol(object):
    """Implementation of the controller side of the GTP protocol.

    This communicates with a single engine. It's a higher level interface than
    Gtp_channel, including helper functions for the protocol-level GTP commands.

    Public attributes:
      channel     -- the underlying Gtp_channel (None if it's closed).
      name        -- the channel name (used in error messages)
      quit_needed -- bool controlling safe_close() behaviour

    It's ok to access the underlying channel directly (eg, to enable logging).

    Instantiate with channel and name.

    """
    def __init__(self, channel, name):
        self.channel = channel
        self.name = str(name)
        self.known_commands = {}
        self.log_dest = None
        self.gtp_translations = {}
        self.is_first_command = True
        self.quit_needed = True

    def do_command(self, command, *arguments):
        """Send a command to the engine and return the response.

        command    -- string (command name)
        arguments  -- strings or unicode objects

        Arguments may not contain spaces. If a command is documented as
        expecting a list of vertices, each vertex must be passed as a separate
        argument.

        Arguments may be unicode objects, in which case they will be sent as
        utf-8.

        Returns the result text from the engine as a string with no trailing
        whitespace. It may contain newlines, but there are no empty lines
        except perhaps the first. There is no leading whitespace on the first
        line. (It doesn't include the leading =[id] bit.)

        If the engine returns an error response, raises GtpEngineError with the
        error message as exception parameter.

        This will wait indefinitely for the engine to produce the response.

        Raises GtpChannelClosed if the engine has apparently closed its
        connection.

        Raises GtpProtocolError if the engine's response is too mangled to be
        returned.

        Raises GtpTransportError if there was an error from the communication
        layer between the controller and the engine (which may well mean that
        the engine has gone away).

        """
        if self.channel is None:
            raise StandardError("channel is closed")
        def fix_argument(argument):
            if isinstance(argument, unicode):
                return argument.encode("utf-8")
            else:
                return argument
        fixed_command = fix_argument(command)
        fixed_arguments = map(fix_argument, arguments)
        fixed_command = self.gtp_translations.get(fixed_command, fixed_command)
        def format_command():
            desc = "%s" % (" ".join([fixed_command] + fixed_arguments))
            if self.is_first_command:
                return "first command (%s)" % desc
            else:
                return "'%s'" % desc
        try:
            self.channel.send_command(fixed_command, fixed_arguments)
        except GtpChannelClosed, e:
            self.quit_needed = False
            raise GtpChannelClosed(
                "error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        except GtpTransportError, e:
            self.quit_needed = False
            raise GtpTransportError(
                "transport error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        except GtpProtocolError, e:
            self.quit_needed = False
            raise GtpProtocolError(
                "GTP protocol error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        try:
            is_error, response = self.channel.get_response()
        except GtpChannelClosed, e:
            self.quit_needed = False
            raise GtpChannelClosed(
                "error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        except GtpTransportError, e:
            self.quit_needed = False
            raise GtpTransportError(
                "transport error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        except GtpProtocolError, e:
            self.quit_needed = False
            raise GtpProtocolError(
                "GTP protocol error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        self.is_first_command = False
        if is_error:
            raise GtpEngineError(
                "error response from %s to %s:\n%s" %
                (format_command(), self.name, response))
        return response

    def known_command(self, command):
        """Check whether 'command' is known by the engine.

        This sends 'known_command' the first time it's asked, then caches the
        result.

        If known_command fails, returns False.

        May propagate GtpProtocolError, GtpChannelClosed, or GtpTransportError
        (see do_command).

        """
        result = self.known_commands.get(command)
        if result is not None:
            return result
        try:
            response = self.do_command("known_command", command)
        except GtpEngineError:
            known = False
        else:
            known = (response == 'true')
        self.known_commands[command] = known
        return known

    def check_protocol_version(self):
        """Check the engine's declared protocol version.

        Raises GtpProtocolError if the engine declares a version other than 2.
        Otherwise does nothing.

        If the engine returns a GTP error response (in particular, if
        protocol_version isn't implemented), this does nothing.

        May propagate GtpProtocolError, GtpChannelClosed, or GtpTransportError
        (see do_command).

        """
        try:
            protocol_version = self.do_command("protocol_version")
        except GtpEngineError:
            return
        if protocol_version != "2":
            raise GtpProtocolError(
                "%s reports GTP protocol version %s" %
                (self.name, protocol_version))

    def close_channel(self, send_quit=True):
        """Close the communication channel to the engine.

        send_quit  -- bool (default True)

        May raise GtpTransportError or GtpProtocolError

        Returns the channel's resource usage (see resource.getrusage() for the
        format), or None if not available.

        If send_quit is true, sends the 'quit' command and waits for a response
        (ignoring GtpChannelClosed) before closing the channel. Some engines (eg
        Mogo) don't behave well if we just close their input, so it's usually
        best to do this.

        """
        if send_quit:
            try:
                self.do_command("quit")
            except (GtpEngineError, GtpChannelClosed):
                pass
        try:
            self.channel.close()
        except GtpTransportError, e:
            raise GtpTransportError(
                "error closing %s:\n%s" % (self.name, e))
        result = self.channel.resource_usage
        self.channel = None
        return result

    def safe_close(self):
        """Close the communication channel to the engine.

        This is safe to call even if the channel is already closed, or has had
        protocol or transport errors.

        This will not propagate any exceptions.

        Returns a string containing any error messages.


        Normally this will send 'quit' to the engine, but it will not do so if
        the controller has previously seen a GtpControllerError,
        GtpTransportError, or GtpCnannelClosed exception from the channel.

        You can control this behaviour explicitly by setting the quit_needed
        attribute before calling safe_close().

        """
        errors = []
        if self.channel is None:
            return errors
        if self.quit_needed:
            try:
                self.do_command("quit")
            except GtpControllerError, e:
                errors.append(str(e))
        try:
            self.channel.close()
        except GtpTransportError, e:
            errors.append("error closing %s:\n%s" % (self.name, e))
        self.channel = None
        return "\n".join(errors)


    def set_gtp_translations(self, translations):
        """Set GTP command translations.

        translations -- map public command name -> underlying command name

        In future calls to do_command, a request to send 'public command name'
        will be sent to the underlying channel as the corresponding 'underlying
        command name'.

        """
        self.gtp_translations = translations
