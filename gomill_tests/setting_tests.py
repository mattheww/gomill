"""Tests for settings.py"""

from gomill.settings import *

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_interpret_shlex_sequence(tc):
    iss = interpret_shlex_sequence
    tc.assertEqual(iss("test"), ["test"])
    tc.assertEqual(iss("test "), ["test"])
    tc.assertEqual(iss("~test"), ["~test"])
    tc.assertEqual(iss("test foo  bar"), ["test", "foo", "bar"])
    tc.assertEqual(iss("test 'foo  bar'"), ["test", "foo  bar"])
    tc.assertEqual(iss(u"test foo  bar"), ["test", "foo", "bar"])
    tc.assertEqual(iss(["test"]), ["test"])
    tc.assertEqual(iss(["test", "foo", "bar"]), ["test", "foo", "bar"])
    tc.assertEqual(iss(["test", "foo  bar"]), ["test", "foo  bar"])
    tc.assertEqual(iss(("test", "foo", "bar")), ["test", "foo", "bar"])
    tc.assertRaisesRegexp(ValueError, "^empty$", iss, "")
    tc.assertRaisesRegexp(ValueError, "^not a string or a sequence$", iss, None)
    tc.assertRaisesRegexp(ValueError, "^element not a string$",
                          iss, ["test", None])
    tc.assertRaisesRegexp(ValueError, "^element contains NUL$",
                          iss, ["test", "fo\x00"])

