"""Go Text Protocol support (controller side).

Based on GTP 'draft version 2' (see <http://www.lysator.liu.se/~gunnar/gtp/>).

"""

import errno
import os
import re
import signal
import subprocess

from gomill.utils import *
from gomill.common import *


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

    Additional attributes:
      gtp_command       -- string (or None)
      gtp_arguments     -- sequence of strings (or None)
      gtp_error_message -- string (or None)

    """
    def __init__(self, args,
                 gtp_command=None, gtp_arguments=None, gtp_error_message=None):
        StandardError.__init__(self, args)
        self.gtp_command = gtp_command
        self.gtp_arguments = gtp_arguments
        self.gtp_error_message = gtp_error_message


_gtp_word_characters_re = re.compile(r"\A[\x21-\x7e\x80-\xff]+\Z")
_remove_response_controls_re = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

def is_well_formed_gtp_word(s):
    """Check whether 's' is well-formed as a single GTP word.

    In particular, this rejects unicode objects and strings containing spaces.

    """
    if not isinstance(s, str):
        return False
    if not _gtp_word_characters_re.search(s):
        return False
    return True

class Gtp_channel(object):
    """A communication channel to a GTP engine.

    public attributes:
      exit_status
      resource_usage

    exit_status describes the engine's exit status as an integer. It is None if
    not available. The integer is in the form returned by os.wait() (in
    particular, zero for successful exit, nonzero for unsuccessful).

    resource_usage describes the engine's resource usage (see
    resource.getrusage() for the format). It is None if not available.

    In practice these attributes are only available for subprocess-based
    channels, and only after they've been closed.

    """
    def __init__(self):
        self.exit_status = None
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
        except Exception:
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
            self._log(">> ", command + ("".join(" " + a for a in arguments)))
        self.send_command_impl(command, arguments)

    def get_response(self):
        """Read a GTP response from the channel.

        Waits indefinitely for the response.

        Returns a pair (is_failure, response)

        'is_failure' is a bool indicating whether the engine returned a success
        or a failure response.

        For a success response, 'response' is the result from the engine; for a
        failure response it's the error message from the engine.

        This cleans the response according to the GTP spec, and also removes
        leading and trailing whitespace.

        This means that 'response' is an 8-bit string with no trailing
        whitespace. It may contain newlines, but there are no empty lines except
        perhaps the first. There is no leading whitespace on the first line.
        There are no other control characters. It may include 'high' characters,
        in whatever encoding the engine was using.

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
            self._log("<< ", response.rstrip())
        return result

    # For subclasses to override:

    def close(self):
        """Close the command and response channels.

        Channel implementations may use this to clean up resources associated
        with the engine (eg, to terminate a subprocess).

        Raises GtpTransportError if a serious error is detected while doing this
        (this is unlikely in practice).

        When it is meaningful (eg, for subprocess channels) this waits for the
        engine to exit. Nonzero exit status is not considered a serious error.

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
            # << All other [than HT, CR, LF] control characters must be
            # discarded on input >>
            # << Any occurence of a CR character must be discarded on input >>
            s = _remove_response_controls_re.sub("", s)
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

        This blocks until a byte is available, or end-of-file is reached (in
        which case it returns an empty string).

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
    Instantiation will raise GtpChannelError if the process can't be started.

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
            raise GtpChannelError(str(e))
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
            # We don't really care about the exit status, but we do want to be
            # sure it isn't still running.
            # Even if there were errors closing the pipes, it's most likely that
            # the subprocesses has exited.
            pid, exit_status, rusage = os.wait4(self.subprocess.pid, 0)
            self.exit_status = exit_status
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
      name              -- short ascii string (used in error messages)
      channel_is_closed -- bool
      channel_is_bad    -- bool

    Instantiate with channel and name.

    It's ok to access the underlying channel directly (eg, to enable logging).

    """
    def __init__(self, channel, name):
        self.channel = channel
        self.name = str(name)
        self.known_commands = {}
        self.log_dest = None
        self.gtp_aliases = {}
        self.is_first_command = True
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


        Returns the result text from the engine as an 8-bit string with no
        trailing whitespace. It may contain newlines, but there are no empty
        lines except perhaps the first. There is no leading whitespace on the
        first line. There are no other control characters. It may include 'high'
        characters, in whatever encoding the engine was using. (The result text
        doesn't include the leading =[id] bit.)

        If the engine returns a failure response, raises BadGtpResponse (use the
        gtp_error_message attribute to retrieve the text of the response).

        This will wait indefinitely for the engine to produce the response.


        Raises GtpChannelClosed if the engine has apparently closed its
        connection.

        Raises GtpProtocolError if the engine's response is too mangled to be
        returned.

        Raises GtpTransportError if there was an error from the communication
        layer between the controller and the engine (which may well mean that
        the engine has gone away).

        If any of these GtpChannelError variants is raised, this also marks the
        channel as 'bad' (this has no effect on future do_command() calls, but
        see safe_do_command() below).


        This applies gtp_aliases (see below). Error messages (including
        BadGtpResponse.gtp_command) will refer to the underlying command, not
        the alias.

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
        translated_command = self.gtp_aliases.get(fixed_command, fixed_command)
        is_first_command = self.is_first_command
        self.is_first_command = False

        def format_command():
            desc = "%s" % (" ".join([translated_command] + fixed_arguments))
            if is_first_command:
                return "first command (%s)" % desc
            else:
                return "'%s'" % desc

        try:
            is_sending = True
            self.channel.send_command(translated_command, fixed_arguments)
            is_sending = False
            is_failure, response = self.channel.get_response()
        except GtpChannelError, e:
            self.channel_is_bad = True
            if isinstance(e, GtpTransportError):
                error_label = "transport error"
            elif isinstance(e, GtpProtocolError):
                error_label = "GTP protocol error"
            else:
                error_label = "error"
            if is_sending:
                msg = "%s sending %s to %s:\n%s"
            else:
                msg = "%s reading response to %s from %s:\n%s"
            e.args = (msg % (error_label, format_command(), self.name, e),)
            raise
        if is_failure:
            raise BadGtpResponse(
                "failure response from %s to %s:\n%s" %
                (format_command(), self.name, response),
                gtp_command=translated_command, gtp_arguments=fixed_arguments,
                gtp_error_message=response)
        return response

    def _known_command(self, command, do_command):
        """Common implementation for known_command and safe_known_command."""
        result = self.known_commands.get(command)
        if result is not None:
            return result
        translated_command = self.gtp_aliases.get(command, command)
        try:
            response = do_command("known_command", translated_command)
        except BadGtpResponse:
            known = False
        else:
            known = (response == 'true')
        self.known_commands[command] = known
        return known

    def known_command(self, command):
        """Check whether 'command' is known by the engine.

        This sends 'known_command' the first time it's asked, then caches the
        result.

        If known_command fails, returns False.

        May propagate GtpChannelError (see do_command).

        This does the right thing if gtp aliases have been set (but it doesn't
        invalidate the cache if they're changed).

        """
        return self._known_command(command, self.do_command)

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
        # Engines returning "2.0" have been seen in the wild.
        # See https://github.com/mattheww/gomill/issues/5
        try:
            if float(protocol_version) == 2.0:
                return
        except ValueError:
            pass
        raise BadGtpResponse(
            "%s reports GTP protocol version %s" %
            (self.name, protocol_version))

    def list_commands(self):
        """Return the engine's declared command list.

        Returns a list of nonempty strings without leading or trailing
        whitespace. Filters out strings which wouldn't be accepted as commands.

        May propagate GtpChannelError or BadGtpResponse

        """
        response = self.do_command('list_commands')
        stripped = [s for s in
                    (t.strip() for t in response.split("\n"))]
        return [s for s in stripped if is_well_formed_gtp_word(s)]

    def close(self):
        """Close the communication channel to the engine.

        May propagate GtpTransportError.

        Unless you have a good reason, you should send 'quit' before closing the
        connection (eg, by using safe_close() instead of close()).

        When it is meaningful (eg, for subprocess channels) this waits for the
        engine to exit. Nonzero exit status is not considered an error.

        """
        if self.channel_is_closed:
            raise StandardError("channel is closed")
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
        return self._known_command(command, self.safe_do_command)

    def safe_close(self):
        """Close the communication channel to the engine, avoiding exceptions.

        This is safe to call even if the channel is already closed, or has had
        protocol or transport errors.

        This will not propagate any exceptions; it will set them aside like
        safe_do_command.

        When it is meaningful (eg, for subprocess channels) this waits for the
        engine to exit. Nonzero exit status is not reported as an error.


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


    def set_gtp_aliases(self, aliases):
        """Set GTP command aliases.

        aliases -- map public command name -> underlying command name

        In future calls to do_command, a request to send 'public command name'
        will be sent to the underlying channel as the corresponding 'underlying
        command name'.

        """
        self.gtp_aliases = aliases


class Engine_description(object):
    """Data from GTP engine-description commands.

    Public attributes:
      raw_name      -- result of GTP 'name' (raw bytes)
      raw_version   -- result of GTP 'version' (raw bytes)
      name          -- result of GTP 'name' (utf-8)
      version       -- result of GTP 'version' (utf-8)
      clean_version -- version with verbosity removed (utf-8)
      description   -- result of GTP 'gomill-describe_engine' (utf-8)

    If a GTP command fails or is not implemented, the corresponding attributes
    have value None.

    The non-raw attributes are never empty strings; None is substituted.

    Some engines unfortunately include usage instructions in the version string
    (apparently for the sake of kgsGTP); we attempt to remove this and put the
    result in clean_version.

    Engine_descriptions are suitable for pickling.

    """
    def __init__(self, raw_name, raw_version, raw_description):
        self.raw_name = raw_name
        if raw_name:
            self.name = sanitise_utf8(raw_name)
        else:
            self.name = None

        self.raw_version = raw_version
        if raw_version:
            self.version = sanitise_utf8(raw_version)
            self.clean_version = self._fix_version(self.name, self.version)
        else:
            self.version = None
            self.clean_version = None

        if raw_description:
            self.description = sanitise_utf8(raw_description)
        else:
            self.description = None

    @staticmethod
    def _fix_version(name, version):
        if name is not None and version.lower().startswith(name.lower()):
            version = version[len(name):].lstrip()
        # Some engines unfortunately include usage instructions in the version
        # string (apparently for the sake of kgsGTP); try to clean this up.
        if len(version) > 64:
            # MoGo
            a, b, c = version.partition(". Please read http:")
            if b:
                return a
            # Pachi
            a, b, c = version.partition(": I'm playing")
            if b:
                return a
            # Other
            return version.split()[0]
        return version

    @classmethod
    def from_controller(cls, controller):
        """Return a new Engine_description, querying a controller for the data.

        May propagate GtpChannelError.

        """
        try:
            gtp_name = controller.do_command("name")
        except BadGtpResponse:
            gtp_name = None
        try:
            gtp_version = controller.do_command("version")
        except BadGtpResponse:
            gtp_version = None
        gtp_gde = None
        if controller.known_command("gomill-describe_engine"):
            try:
                gtp_gde = controller.do_command("gomill-describe_engine")
            except BadGtpResponse:
                pass
        return cls(gtp_name, gtp_version, gtp_gde)

    def get_short_description(self):
        """Return short description of the engine.

        This is typically a single line.

        Returns None if name is None.

        """
        if self.name is None:
            return None
        if self.clean_version is None or len(self.clean_version) > 32:
            return self.name
        return self.name + ":" + self.clean_version

    def get_long_description(self):
        """Return the fullest available description of the engine.

        This may have multiple lines.

        Returns None if name, version, and description are all None.

        """
        if self.description is not None:
            return self.description
        if self.name is None:
            if self.clean_version is None:
                return None
            else:
                return "version " + self.clean_version
        else:
            if self.clean_version is None:
                return self.name
            else:
                return self.name + ":" + self.clean_version

class Game_controller(object):
    """Manage a pair of GTP controllers representing game players.

    Instantiate with the player codes for black and white.

    The player codes are short ascii strings, used to name the players in error
    messages and anywhere else the Game_controller's client wants. The two
    codes must be different (otherwise ValueError is raised).


    Order of operations:
      gc = Game_controller(...)
      gc.set_player_subprocess('b', ...) or set_player_controller('b', ...)
      gc.set_player_subprocess('w', ...) or set_player_controller('w', ...)
      Any combination of:
        gc.send_command(...)
        gc.maybe_send_command(...)
        gc.known_command(...)
        higher-level helpers
      gc.close_players()
      gc.describe_late_errors()
      gc.get_resource_usage_cpu_times()

    Public attributes for reading:
      players             -- map colour -> player code
      engine_descriptions -- map colour -> Engine_description


    Methods which send commands to engines will normally propagate
    GtpChannelError if there is trouble communicating with the engine.

    But some commands are run 'cautiously'. In this case, such errors are set
    aside (retrieve a description with describe_late_errors()).

    The game controller can be placed into 'cautious mode', which means all
    commands are sent cautiously. See the documentation for individual methods
    to see how low-level errors are then indicated.

    """
    def __init__(self, player_b_code, player_w_code):
        if player_b_code == player_w_code:
            raise ValueError("player codes must be distinct")
        self.players = {'b' : player_b_code, 'w' : player_w_code}
        self.controllers = {}
        self.late_errors = []
        self.engine_descriptions = {'b' : None, 'w' : None}
        self.in_cautious_mode = False

    ## Configuration API

    def set_player_controller(self, colour, controller,
                              check_protocol_version=True):
        """Specify a player using a Gtp_controller.

        controller             -- Gtp_controller
        check_protocol_version -- bool (default True)

        By convention, the controller's name should be 'player <player code>'.

        If check_protocol_version is true, rejects an engine that declares a
        GTP protocol version <> 2 (raises BadGtpResponse).

        Sets the engine_descriptions entry for the player, using GTP commands
        (see Engine_description).

        Propagates GtpChannelError if there's a low-level error checking the
        protocol version or from the engine-description commands.

        """
        self.controllers[colour] = controller
        if check_protocol_version:
            controller.check_protocol_version()
        self.engine_descriptions[colour] = \
            Engine_description.from_controller(controller)

    def set_player_subprocess(self, colour, command,
                              check_protocol_version=True, **kwargs):
        """Specify the a player as a subprocess.

        command                -- list of strings (as for subprocess.Popen)
        check_protocol_version -- bool (default True)

        Any additional keyword arguments are passed to the
        Subprocess_gtp_channel constructor.

        Creates a Gtp_controller, named 'player <player code>'.

        If check_protocol_version is true, rejects an engine that declares a
        GTP protocol version <> 2 (raises BadGtpResponse).

        Sets the engine_descriptions entry for the player, using GTP commands
        (see Engine_description).

        Propagates GtpChannelError if there's a low-level error creating the
        subprocess, checking the protocol version, or from the
        engine-description commands.

        """
        player_code = self.players[colour]
        try:
            channel = Subprocess_gtp_channel(command, **kwargs)
        except GtpChannelError, e:
            raise GtpChannelError(
                "error starting subprocess for player %s:\n%s" %
                (player_code, e))
        controller = Gtp_controller(channel, "player %s" % player_code)
        self.set_player_controller(colour, controller, check_protocol_version)


    ## Generic GTP controller API

    def set_cautious_mode(self, b):
        """Turn cautious mode on or off.

        b -- bool

        """
        self.in_cautious_mode = bool(b)

    def get_controller(self, colour):
        """Return the underlying Gtp_controller for the specified player.

        Raises KeyError if the player has not been set.

        """
        return self.controllers[colour]

    def send_command(self, colour, command, *arguments):
        """Send the specified GTP command to one of the players.

        colour    -- player to talk to ('b' or 'w')
        command   -- gtp command name (string)
        arguments -- gtp arguments (as for do_command)

        Returns the response as a string.

        Raises BadGtpResponse if the engine returns a failure response.

        Also raises BadGtpResponse if the game controller is in cautious mode
        and a low-level error occurs (you can distinguish this case because the
        gtp_* attributes are None). The exception does not contain a
        description of the low-level error (but describe_late_errors() will).

        """
        controller = self.controllers[colour]
        if self.in_cautious_mode:
            response = controller.safe_do_command(command, *arguments)
            if response is None:
                raise BadGtpResponse(
                    "late low-level error from player %s" %
                    self.players[colour])
            return response
        else:
            return controller.do_command(command, *arguments)

    def maybe_send_command(self, colour, command, *arguments):
        """Send the specified GTP command, if supported.

        Variant of send_command(): if the command isn't supported by the
        engine, or gives a failure response, returns None.

        If the game controller is in cautious mode and a low-level error
        occurs, returns None.

        """
        controller = self.controllers[colour]
        if self.in_cautious_mode:
            known_command = controller.safe_known_command
            do_command = controller.safe_do_command
        else:
            known_command = controller.known_command
            do_command = controller.do_command
        if known_command(command):
            try:
                result = do_command(command, *arguments)
            except BadGtpResponse:
                result = None
        else:
            result = None
        return result

    def known_command(self, colour, command):
        """Check whether the specified GTP command is supported.

        If the game controller is in cautious mode and a low-level error
        occurs, returns False.

        """
        controller = self.controllers[colour]
        if self.in_cautious_mode:
            return controller.safe_known_command(command)
        else:
            return controller.known_command(command)

    def close_players(self):
        """Close both controllers (if they're open).

        Sends "quit"; always communicates cautiously.

        """
        for colour in ("b", "w"):
            controller = self.controllers.get(colour)
            if controller is None:
                continue
            controller.safe_close()
            self.late_errors += controller.retrieve_error_messages()

    def describe_late_errors(self):
        """Retrieve the late error messages.

        Returns a string, or None if there were no late errors.

        This is only available after close_players() has been called.

        The late errors are low-level errors which occurred while communicating
        'cautiously' and so were set aside.

        In particular, they include any errors from closing (including failure
        responses from the final 'quit' command).

        """
        if not self.late_errors:
            return None
        return "\n".join(self.late_errors)

    def get_resource_usage_cpu_times(self):
        """Return the measured CPU times of the engines.

        Returns a dict colour -> cpu_time

        cpu_time is a float, or None if the information isn't available.

        CPU time will not be available until the controller has been closed.

        It's safe to call this even if one or both of the engines was never
        successfully started.

        """
        result = {'b' : None, 'w' : None}
        for colour in 'b', 'w':
            try:
                controller = self.controllers[colour]
            except KeyError:
                continue
            ru = controller.channel.resource_usage
            if ru is not None:
                result[colour] = ru.ru_utime + ru.ru_stime
        return result


    ## Higher-level GTP helpers

    def get_gtp_cpu_times(self):
        """Ask the engines for the CPU time they've used.

        This uses the gomill-cpu_time extension command, when available.

        Returns a pair (cpu_times, errors)
          cpu_times -- (partial) dict colour -> float (representing seconds)
          errors    -- set of colours

        If an engine doesn't claim to support gomill-cpu_time, it won't appear
        in either 'cpu_times' or 'errors'.

        If an engine claims to support it, but gives an invalid or error
        response (including a low-level error when in cautious mode), it will
        appear in 'errors'.

        """
        result = {}
        errors = set()
        for colour in 'b', 'w':
            if self.known_command(colour, 'gomill-cpu_time'):
                try:
                    s = self.maybe_send_command(colour, 'gomill-cpu_time')
                    result[colour] = float(s)
                except (ValueError, TypeError):
                    errors.add(colour)
        return result, errors


