"""Generic (non-gomill-specific) test support code."""

import errno
from cStringIO import StringIO

from gomill_tests.test_framework import SupporterError

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


