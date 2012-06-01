import fcntl
import os
import select
import subprocess

from gomill.gtp_controller import *

def set_nonblocking(fd):
    """Set a file descriptor to nonblocking mode."""
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)

def _popen(command, **kwargs):
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

_readsize = 4096

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
    def __init__(self, command, cwd=None, env=None):
        Linebased_gtp_channel.__init__(self)
        try:
            self.subprocess, self.response_fd, self.error_fd = \
                _popen(command, cwd=cwd, env=env)
        except EnvironmentError, e:
            raise GtpChannelError(str(e))
        self.command_pipe = self.subprocess.stdin
        self.response_data = ""
        self.seen_eof = False
        self.error_data = []
        self.pipes_to_poll = [self.response_fd, self.error_fd]

    def send_command_line(self, command):
        try:
            self.command_pipe.write(command)
            self.command_pipe.flush()
        except EnvironmentError, e:
            if e.errno == errno.EPIPE:
                raise GtpChannelClosed("engine has closed the command channel")
            else:
                raise GtpTransportError(str(e))

    def _handle_event(self):
        r, _, _ = select.select(self.pipes_to_poll, [], [])
        if self.error_fd in r:
            self._handle_error_data()
        elif self.response_fd in r:
            self._handle_response_data()

    def _handle_response_data(self):
        s = os.read(self.response_fd, _readsize)
        if s:
            self.response_data += s
        else:
            self.seen_eof = True
            self.pipes_to_poll.remove(self.response_fd)

    def _handle_error_data(self):
        s = os.read(self.error_fd, _readsize)
        if s:
            self.error_data.append(s)
        else:
            self.pipes_to_poll.remove(self.error_fd)

    def get_response_line(self):
        while True:
            i = self.response_data.find("\n")
            if i != -1:
                line = self.response_data[:i+1]
                self.response_data = self.response_data[i+1:]
                return line
            if self.seen_eof:
                return self.response_data
            try:
                self._handle_event()
            except EnvironmentError, e:
                raise GtpTransportError(str(e))

    def get_response_byte(self):
        while True:
            if self.response_data:
                byte = self.response_data[0]
                self.response_data = self.response_data[1:]
                return byte
            if self.seen_eof:
                return ""
            try:
                self._handle_event()
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
            os.close(self.response_fd)
        except EnvironmentError, e:
            errors.append("error closing response pipe:\n%s" % e)
            errors.append(str(e))
        try:
            os.close(self.error_fd)
        except EnvironmentError, e:
            errors.append("error closing stderr pipe:\n%s" % e)
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

    def retrieve_diagnostics(self):
        """FIXME

        FIXME: Explain that this is up-to-date as of the last call to
        get_reponse_...().

        """
        result = "".join(self.error_data)
        self.error_data = []
        return result

