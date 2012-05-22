"""Filesystem sandboxes for testcases."""

import shutil
import tempfile

# This makes TestResult ignore lines from this module in tracebacks
__unittest = True

class Sandbox_testcase_mixin(object):
    """TestCase mixin adding support for filesystem sandboxes."""
    def init_sandbox_testcase_mixin(self):
        self.__sandboxes = {}

    def sandbox(self, code=None):
        """Get a temporary filesystem directory.

        Returns the sandbox pathname.

        When called the first time, this creates the sandbox directory.

        You can call this multiple times, and it will return the same pathname
        (so tests don't need remember it locally).

        You can optionally pass a sandbox code, to get multiple independent
        sandboxes.

        All sandboxes are removed (with shutil.rmtree) at test-cleanup time.

        """
        pathname = self.__sandboxes.get(code)
        if pathname is None:
            if code:
                suffix = "-%s" % code
            else:
                suffix = ""
            pathname = tempfile.mkdtemp(prefix='test-sandbox-', suffix=suffix)
            self.__sandboxes[code] = pathname
            def cleanup():
                shutil.rmtree(pathname)
            self.addCleanup(cleanup)
        return pathname

