"""Go Text Protocol support (controller side).

Based on GTP 'draft version 2' (see <http://www.lysator.liu.se/~gunnar/gtp/>).

"""

import errno
import os
import re
import signal
import subprocess

from gomill.gomill_common import *


class GtpChannelError(StandardError):
    """Low-level error trying to talk to a GTP engine.

    This is the base class for GtpProtocolError, GtpTransportError,
    and GtpChannelClosed. It may also be raised directly.

    """

class GtpProtocolError(GtpChannelError):
    """A GTP engine returned an ill-formed response."""

class GtpTransportError(GtpChannelError):
    """An error from the transport underlying the GTP channel."""

class GtpChannelClosed(GtpChannelError):
    """The (command or response) channel to a GTP engine has been closed."""


class BadGtpResponse(StandardError):
    """Unacceptable response from a GTP engine.

    This is usually used to indicate a GTP failure ('?') response.

    Some higher-level functions use this exception to indicate a GTP success
    ('=') response which they couldn't interpret.

    """


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

        May raise GtpChannelError.

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

        Returns a pair (is_failure, response)

        'is_failure' is a bool indicating whether the engine returned a success
        or a failure response.

        For a success response, 'response' is the result from the engine; for a
        failure response it's the error message from the engine.

        'response' is a string with no trailing whitespace. It may contain
        newlines, but there are no empty lines except perhaps the first. There
        is no leading whitespace on the first line.

        May raise GtpChannelError. In particular, raises GtpProtocolError if the
        success/failure indicator can't be read from the engine's response.

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
        """Close the command and response channels.

        Channel implementations may use this to clean up resources associated
        with the engine (eg, to terminate a subprocess).

        Raises GtpTransportError if a serious error is detected while doing this
        (this is unlikely in practice).

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
            raise GtpChannelError("no outstanding commands")
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

        If we receive EOF otherwise, we use the data received anyway.

        The first time this is called, we check the first byte without reading
        the whole line, and raise GtpProtocolError if it isn't plausibly the
        start of a GTP response (strictly, if it's a control character we should
        just discard it, but I think it's more useful to reject them here; in
        particular, this lets us detect GMP).

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

    Closing the channel waits for the subprocess to exit.

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
        # Errors from closing pipes or wait4() are unlikely, but possible.

        # Ideally would give up waiting after a while and forcibly terminate the
        # subprocess.
        errors = []
        try:
            self.command_pipe.close()
        except EnvironmentError, e:
            errors.append("error closing command pipe:\n%s" % e)
        try:
            self.response_pipe.close()
        except EnvironmentError, e:
            errors.append("error closing response pipe:\n%s" % e)
            errors.append(str(e))
        try:
            # We don't care about the exit status, but we do want to be sure it
            # isn't still running.
            # Even if there were errors closing the pipes, it's most likely that
            # the subprocesses has exited.
            pid, exit_status, rusage = os.wait4(self.subprocess.pid, 0)
            self.resource_usage = rusage
        except EnvironmentError, e:
            errors.append(str(e))
        if errors:
            raise GtpTransportError("\n".join(errors))


class Gtp_controller(object):
    """Implementation of the controller side of the GTP protocol.

    This communicates with a single engine. It's a higher level interface than
    Gtp_channel, including helper functions for the protocol-level GTP commands.

    Public attributes:
      channel           -- the underlying Gtp_channel
      name              -- the channel name (used in error messages)
      channel_is_closed -- bool
      channel_is_bad    -- bool

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
        self.errors_seen = []
        self.channel_is_closed = False
        self.channel_is_bad = False

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
        line. (The result text doesn't include the leading =[id] bit.)

        If the engine returns a failure response, raises BadGtpResponse with the
        error message as exception parameter.

        This will wait indefinitely for the engine to produce the response.


        Raises GtpChannelClosed if the engine has apparently closed its
        connection.

        Raises GtpProtocolError if the engine's response is too mangled to be
        returned.

        Raises GtpTransportError if there was an error from the communication
        layer between the controller and the engine (which may well mean that
        the engine has gone away).

        If any of these GtpChannelError variants is raised, this also marks the
        channel as 'bad'.

        """
        if self.channel_is_closed:
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
            self.channel_is_bad = True
            raise GtpChannelClosed(
                "error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        except GtpTransportError, e:
            self.quit_needed = False
            self.channel_is_bad = True
            raise GtpTransportError(
                "transport error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        except GtpProtocolError, e:
            self.quit_needed = False
            self.channel_is_bad = True
            raise GtpProtocolError(
                "GTP protocol error sending %s to %s:\n%s" %
                (format_command(), self.name, e))
        try:
            is_failure, response = self.channel.get_response()
        except GtpChannelClosed, e:
            self.quit_needed = False
            self.channel_is_bad = True
            raise GtpChannelClosed(
                "error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        except GtpTransportError, e:
            self.quit_needed = False
            self.channel_is_bad = True
            raise GtpTransportError(
                "transport error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        except GtpProtocolError, e:
            self.quit_needed = False
            self.channel_is_bad = True
            raise GtpProtocolError(
                "GTP protocol error reading response to %s from %s:\n%s" %
                (format_command(), self.name, e))
        self.is_first_command = False
        if is_failure:
            raise BadGtpResponse(
                "failure response from %s to %s:\n%s" %
                (format_command(), self.name, response))
        return response

    def known_command(self, command):
        """Check whether 'command' is known by the engine.

        This sends 'known_command' the first time it's asked, then caches the
        result.

        If known_command fails, returns False.

        May propagate GtpChannelError (see do_command).

        """
        result = self.known_commands.get(command)
        if result is not None:
            return result
        try:
            response = self.do_command("known_command", command)
        except BadGtpResponse:
            known = False
        else:
            known = (response == 'true')
        self.known_commands[command] = known
        return known

    def check_protocol_version(self):
        """Check the engine's declared protocol version.

        Raises BadGtpResponse if the engine declares a version other than 2.
        Otherwise does nothing.

        If the engine returns a GTP failure response (in particular, if
        protocol_version isn't implemented), this does nothing.

        May propagate GtpChannelError (see do_command).

        """
        try:
            protocol_version = self.do_command("protocol_version")
        except BadGtpResponse:
            return
        if protocol_version != "2":
            raise BadGtpResponse(
                "%s reports GTP protocol version %s" %
                (self.name, protocol_version))

    def close(self):
        """Close the communication channel to the engine.

        May propagate GtpTransportError.

        Some engines (eg Mogo) don't behave well if we just close their input
        without sending 'quit', so it's usually best to send 'quit' first (eg,
        by using safe_close() instead of close()).

        """
        try:
            self.channel.close()
        except GtpTransportError, e:
            raise GtpTransportError(
                "error closing %s:\n%s" % (self.name, e))
        self.channel_is_closed = True

    def safe_do_command(self, command, *arguments):
        """Variant of do_command which sets low-level exceptions aside.

        If the channel is closed or marked bad, this does not attempt to send
        the command, and returns None.

        If GtpChannelError is raised while running the command, it is not
        propagated, but the error message is recorded; use
        retrieve_error_messages to retrieve these. In this case the function
        returns None.

        BadGtpResponse is raised in the same way as for do_command.

        """
        if self.channel_is_bad or self.channel_is_closed:
            return None
        try:
            return self.do_command(command, *arguments)
        except BadGtpResponse, e:
            raise
        except GtpChannelError, e:
            self.errors_seen.append(str(e))
            return None

    def safe_known_command(self, command):
        """Variant of known_command which sets low-level exceptions aside.

        If result is already cached, returns it.

        Otherwise, if the channel is closed or marked bad, returns False.

        Otherwise acts like known_command above, using safe_do_command to send
        the command to the engine.

        """
        result = self.known_commands.get(command)
        if result is not None:
            return result
        try:
            response = self.safe_do_command("known_command", command)
        except BadGtpResponse:
            known = False
        else:
            known = (response == 'true')
        self.known_commands[command] = known
        return known

    def safe_close(self):
        """Close the communication channel to the engine, avoiding exceptions.

        This is safe to call even if the channel is already closed, or has had
        protocol or transport errors.

        This will not propagate any exceptions; it will set them aside like
        safe_do_command.


        This will send 'quit' to the engine if the channel is not marked as bad.
        Any failure response will be set aside.

        """
        if self.channel_is_closed:
            return
        if not self.channel_is_bad:
            try:
                self.safe_do_command("quit")
            except BadGtpResponse, e:
                self.errors_seen.append(str(e))
        try:
            self.channel.close()
        except GtpTransportError, e:
            self.errors_seen.append("error closing %s:\n%s" % (self.name, e))
        self.channel_is_closed = True

    def retrieve_error_messages(self):
        """Return error messages which have been set aside by 'safe' commands.

        Returns a list of strings (empty if there are no such messages).

        """
        return self.errors_seen[:]


    def set_gtp_translations(self, translations):
        """Set GTP command translations.

        translations -- map public command name -> underlying command name

        In future calls to do_command, a request to send 'public command name'
        will be sent to the underlying channel as the corresponding 'underlying
        command name'.

        """
        self.gtp_translations = translations
