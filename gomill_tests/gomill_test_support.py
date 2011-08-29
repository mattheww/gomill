"""Gomill-specific test support code."""

import re

from gomill import __version__
from gomill_tests.test_framework import unittest2
from gomill_tests import test_framework

from gomill.common import *
from gomill import ascii_boards
from gomill import boards

# This makes TestResult ignore lines from this module in tracebacks
__unittest = True

def compare_boards(b1, b2):
    """Check whether two boards have the same position.

    returns a pair (position_is_the_same, message)

    """
    if b1.side != b2.side:
        raise ValueError("size is different: %s, %s" % (b1.side, b2.side))
    differences = []
    for row, col in b1.board_points:
        if b1.get(row, col) != b2.get(row, col):
            differences.append((row, col))
    if not differences:
        return True, None
    msg = "boards differ at %s" % " ".join(map(format_vertex, differences))
    try:
        msg += "\n%s\n%s" % (
            ascii_boards.render_board(b1), ascii_boards.render_board(b2))
    except Exception:
        pass
    return False, msg

def compare_diagrams(d1, d2):
    """Compare two ascii board diagrams.

    returns a pair (strings_are_equal, message)

    (assertMultiLineEqual tends to look nasty for these, so we just show them
    both in full)

    """
    if d1 == d2:
        return True, None
    return False, "diagrams differ:\n%s\n\n%s" % (d1, d2)

def scrub_sgf(s):
    """Normalise sgf string for convenience of testing.

    Replaces dates with '***', and 'gomill:<__version__>' with 'gomill:VER'.

    Be careful: gomill version length can affect line wrapping. Either
    serialise with wrap=None or remove newlines before comparing.

    """
    s = re.sub(r"(?m)(?<=^Date ).*$", "***", s)
    s = re.sub(r"(?<=DT\[)[-0-9]+(?=\])", "***", s)
    s = re.sub(r"gomill:" + re.escape(__version__), "gomill:VER", s)
    return s


traceback_line_re = re.compile(
    r"  .*/([a-z0-9_]+)\.pyc?:[0-9]+ \(([a-z0-9_]+)\)")

class Gomill_testcase_mixin(object):
    """TestCase mixin adding support for gomill-specific types.

    This adds:
     assertBoardEqual
     assertEqual and assertNotEqual for Boards

    """
    def init_gomill_testcase_mixin(self):
        self.addTypeEqualityFunc(boards.Board, self.assertBoardEqual)

    def _format_message(self, msg, standardMsg):
        # This is the same as _formatMessage from python 2.7 unittest; copying
        # it because it's not part of the public API.
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg
        try:
            return '%s : %s' % (standardMsg, msg)
        except UnicodeDecodeError:
            return '%s : %s' % (unittest2.util.safe_repr(standardMsg),
                                unittest2.util.safe_repr(msg))

    def assertBoardEqual(self, b1, b2, msg=None):
        are_equal, desc = compare_boards(b1, b2)
        if not are_equal:
            self.fail(self._format_message(msg, desc+"\n"))

    def assertDiagramEqual(self, d1, d2, msg=None):
        are_equal, desc = compare_diagrams(d1, d2)
        if not are_equal:
            self.fail(self._format_message(msg, desc+"\n"))

    def assertNotEqual(self, first, second, msg=None):
        if isinstance(first, boards.Board) and isinstance(second, boards.Board):
            are_equal, _ = compare_boards(first, second)
            if not are_equal:
                return
            msg = self._format_message(msg, 'boards have the same position')
            raise self.failureException(msg)
        super(Gomill_testcase_mixin, self).assertNotEqual(first, second, msg)

    def assertTracebackStringEqual(self, seen, expected, fixups=()):
        """Compare two strings which include tracebacks.

        This is for comparing strings containing tracebacks from
        the compact_tracebacks module.

        Replaces the traceback lines describing source locations with
        '<filename>|<functionname>', for robustness.

        fixups -- list of pairs of strings
                  (additional substitutions to make in the 'seen' string)

        """
        lines = seen.split("\n")
        new_lines = []
        for l in lines:
            match = traceback_line_re.match(l)
            if match:
                l = "|".join(match.groups())
            for a, b in fixups:
                l = l.replace(a, b)
            new_lines.append(l)
        self.assertMultiLineEqual("\n".join(new_lines), expected)


class Gomill_SimpleTestCase(
    Gomill_testcase_mixin, test_framework.SimpleTestCase):
    """SimpleTestCase with the Gomill mixin."""
    def __init__(self, *args, **kwargs):
        test_framework.SimpleTestCase.__init__(self, *args, **kwargs)
        self.init_gomill_testcase_mixin()

class Gomill_ParameterisedTestCase(
    Gomill_testcase_mixin, test_framework.ParameterisedTestCase):
    """ParameterisedTestCase with the Gomill mixin."""
    def __init__(self, *args, **kwargs):
        test_framework.ParameterisedTestCase.__init__(self, *args, **kwargs)
        self.init_gomill_testcase_mixin()


def make_simple_tests(source, prefix="test_"):
    """Make test cases from a module's test_xxx functions.

    See test_framework for details.

    The test functions can use the Gomill_testcase_mixin enhancements.

    """
    return test_framework.make_simple_tests(
        source, prefix, testcase_class=Gomill_SimpleTestCase)
