import errno
import fcntl
import os
import select
import subprocess

from gomill.gtp_controller import *

def _make_eagains():
    result = set()
    for s in ('EAGAIN', 'EWOULDBLOCK'):
        try:
            result.add(getattr(errno, s))
        except AttributeError:
            pass
    if not result:
        raise ValueError
    return result
EAGAINs = _make_eagains()

def set_nonblocking(fd):
    """Set a file descriptor to nonblocking mode."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

_readsize = 16384
_max_diagnostic_buffer_size = 102400

def _handle_gang_event(gang):
    to_poll = sum((c.fds_to_poll for c in gang), [])
    try:
        r, _, _ = select.select(to_poll, [], [])
    except select.error, e:
        raise GtpTransportError(str(e))
    for c in gang:
        if c.diagnostic_fd in r:
            c._handle_diagnostic_data()
        if c.response_fd in r:
            c._handle_response_data()


def _make_noncapturing_subprocess(command, stderr, **kwargs):
    stdout_r, stdout_w = os.pipe()
    try:
        p = subprocess.Popen(
            command,
            preexec_fn=permit_sigpipe, close_fds=True,
            stdin=subprocess.PIPE,
            stdout=stdout_w, stderr=stderr,
            **kwargs)
    except:
        os.close(stdout_r)
        raise
    finally:
        os.close(stdout_w)
    set_nonblocking(stdout_r)
    return p, stdout_r, None

def _make_capturing_subprocess(command, **kwargs):
    stdout_r, stdout_w = os.pipe()
    stderr_r, stderr_w = os.pipe()
    try:
        p = subprocess.Popen(
            command,
            preexec_fn=permit_sigpipe, close_fds=True,
            stdin=subprocess.PIPE,
            stdout=stdout_w, stderr=stderr_w,
            **kwargs)
    except:
        os.close(stdout_r)
        os.close(stderr_r)
        raise
    finally:
        os.close(stdout_w)
        os.close(stderr_w)
    set_nonblocking(stdout_r)
    set_nonblocking(stderr_r)
    return p, stdout_r, stderr_r

class Subprocess_gtp_channel(Linebased_gtp_channel):
    """A GTP channel to a subprocess.

    Instantiate with
      command -- list of strings (as for subprocess.Popen)
      gang    -- set of nonblocking Subprocess_gtp_channels FIXME (optional)
      stderr  -- destination for standard error output (optional)
      cwd     -- working directory to change to (optional)
      env     -- new environment (optional)
    Instantiation will raise GtpChannelError if the process can't be started.

    This starts the subprocess and speaks GTP over its standard input and
    output.

    By default, the subprocess's standard error is left as the standard error
    of the calling process. The 'stderr' parameter is interpreted as for
    subprocess.Popen (but don't set it to STDOUT or PIPE). It can also be
    "capture", in which case it is made available using retrieve_diagnostics().

    The 'cwd' and 'env' parameters are interpreted as for subprocess.Popen.

    Closing the channel waits for the subprocess to exit.

    FIXME: explain about gangs.

    """
    def __init__(self, command, gang=None, stderr=None, cwd=None, env=None):
        Linebased_gtp_channel.__init__(self)
        try:
            (self.subprocess, self.response_fd, self.diagnostic_fd) = \
                self._make_subprocess(command, stderr, cwd=cwd, env=env)
        except EnvironmentError, e:
            raise GtpChannelError(str(e))
        self.command_pipe = self.subprocess.stdin
        self.response_data = ""
        self.seen_eof = False
        self.seen_error = None
        self.diagnostic_data = []
        self.diagnostic_size = 0
        self.max_diagnostic_buffer_size = _max_diagnostic_buffer_size
        self.fds_to_poll = [self.response_fd]
        if self.diagnostic_fd is not None:
            self.fds_to_poll.append(self.diagnostic_fd)
        if gang is None:
            gang = set()
        gang.add(self)
        self.gang = gang

    def _make_subprocess(self, command, stderr, **kwargs):
        if stderr == 'capture':
            return _make_capturing_subprocess(command, **kwargs)
        else:
            if isinstance(stderr, basestring):
                raise ValueError
            if isinstance(stderr, (int, long)) and stderr < 0:
                raise ValueError
            return _make_noncapturing_subprocess(command, stderr, **kwargs)

    def send_command_line(self, command):
        try:
            self.command_pipe.write(command)
            self.command_pipe.flush()
        except EnvironmentError, e:
            if e.errno == errno.EPIPE:
                raise GtpChannelClosed("engine has closed the command channel")
            else:
                raise GtpTransportError(str(e))

    def _handle_response_data(self):
        while True:
            try:
                s = os.read(self.response_fd, _readsize)
            except EnvironmentError, e:
                if e.errno in EAGAINs:
                    break
                self.seen_error = e
                self.fds_to_poll.remove(self.response_fd)
                break
            if s:
                self.response_data += s
            else:
                self.seen_eof = True
                self.fds_to_poll.remove(self.response_fd)
                break

    def _handle_diagnostic_data(self):
        while True:
            try:
                s = os.read(self.diagnostic_fd, _readsize)
            except EnvironmentError, e:
                if e.errno in EAGAINs:
                    break
                self.diagnostic_data.append(
                    "\n[error reading from stderr: %s]" % e)
                self.fds_to_poll.remove(self.diagnostic_fd)
                break
            if s:
                if self.diagnostic_size == -1:
                    continue
                overflow = (self.diagnostic_size + len(s) -
                            self.max_diagnostic_buffer_size)
                if overflow > 0:
                    self.diagnostic_data.append(s[:-overflow])
                    self.diagnostic_data.append("\n[[truncated]]")
                    self.diagnostic_size = -1
                else:
                    self.diagnostic_data.append(s)
                    self.diagnostic_size += len(s)
            else:
                self.fds_to_poll.remove(self.diagnostic_fd)
                break

    def get_response_line(self):
        while True:
            i = self.response_data.find("\n")
            if i != -1:
                line = self.response_data[:i+1]
                self.response_data = self.response_data[i+1:]
                return line
            if self.seen_eof:
                line = self.response_data
                self.response_data = ""
                return line
            if self.seen_error is not None:
                raise GtpTransportError(self.seen_error)
            _handle_gang_event(self.gang)

    def get_response_byte(self):
        while True:
            if self.response_data:
                byte = self.response_data[0]
                self.response_data = self.response_data[1:]
                return byte
            if self.seen_eof:
                return ""
            if self.seen_error is not None:
                raise GtpTransportError(self.seen_error)
            _handle_gang_event(self.gang)

    def close(self):
        # Errors from closing pipes or wait4() are unlikely, but possible.

        # Ideally would give up waiting after a while and forcibly terminate the
        # subprocess.
        self.gang.remove(self)
        errors = []
        try:
            self.command_pipe.close()
        except EnvironmentError, e:
            errors.append("error closing command pipe:\n%s" % e)
        try:
            os.close(self.response_fd)
        except EnvironmentError, e:
            errors.append("error closing response pipe:\n%s" % e)
        if self.diagnostic_fd is not None:
            try:
                os.close(self.diagnostic_fd)
            except EnvironmentError, e:
                errors.append("error closing stderr pipe:\n%s" % e)
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

    def retrieve_diagnostics(self):
        """Retrieve diagnostics captured from standard error.

        Returns a nonempty 8-bit string (representing raw bytes) or None.

        If stderr is not 'capture', always returns None.

        This returns stderr output captured after the last call to
        retrieve_diagnostics(), up until the last time get_response() returned.

        (Strictly, up until the last time get_response() on any channel in the
        gang finished a read of its response pipe.)

        Truncates the data if there was more than _max_diagnostic_buffer_size.

        """
        if self.diagnostic_fd is None:
            return None
        result = "".join(self.diagnostic_data)
        self.diagnostic_data = []
        self.diagnostic_size = 0
        return result or None

