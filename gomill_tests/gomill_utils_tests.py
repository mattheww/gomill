"""Tests for gomill_utils.py."""

from gomill_tests import gomill_test_support

from gomill import gomill_utils

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_format_float(tc):
    ff = gomill_utils.format_float
    tc.assertEqual(ff(1), "1")
    tc.assertEqual(ff(1.0), "1")
    tc.assertEqual(ff(1.5), "1.5")

def test_format_percent(tc):
    pct = gomill_utils.format_percent
    tc.assertEqual(pct(1, 1), "100.00%")
    tc.assertEqual(pct(1, 2), "50.00%")
    tc.assertEqual(pct(1.0, 2.0), "50.00%")
    tc.assertEqual(pct(1, 3), "33.33%")
    tc.assertEqual(pct(0, 3), "0.00%")
    tc.assertEqual(pct(2, 0), "??")
    tc.assertEqual(pct(0, 0), "--")

def test_sanitise_utf8(tc):
    su = gomill_utils.sanitise_utf8
    tc.assertIsNone(su(None))
    tc.assertEqual(su(""), "")
    tc.assertEqual(su("hello world"), "hello world")
    s = u"test \N{POUND SIGN}".encode("utf-8")
    tc.assertIs(su(s), s)
    tc.assertEqual(su(u"test \N{POUND SIGN}".encode("latin1")), "test ?")
