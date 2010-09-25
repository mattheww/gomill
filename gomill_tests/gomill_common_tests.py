"""Tests for gomill_common.py."""

from gomill_tests import gomill_test_support

from gomill import gomill_common

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_opponent_of(tc):
    oo = gomill_common.opponent_of
    tc.assertEqual(oo('b'), 'w')
    tc.assertEqual(oo('w'), 'b')
    tc.assertRaises(ValueError, oo, 'x')
    tc.assertRaises(ValueError, oo, None)
    tc.assertRaises(ValueError, oo, 'B')

def test_format_vertex(tc):
    fv = gomill_common.format_vertex
    tc.assertEqual(fv(None), "pass")
    tc.assertEqual(fv((0, 0)), "A1")
    tc.assertEqual(fv((8, 8)), "J9")
    tc.assertEqual(fv((1, 5)), "F2")

def test_format_vertex_list(tc):
    fvl = gomill_common.format_vertex_list
    tc.assertEqual(fvl([]), "")
    tc.assertEqual(fvl([(0, 0)]), "A1")
    tc.assertEqual(fvl([(0, 0), (1, 5)]), "A1,F2")
    tc.assertEqual(fvl([(0, 0), None, (1, 5)]), "A1,pass,F2")

def test_sanitise_utf8(tc):
    su = gomill_common.sanitise_utf8
    tc.assertIsNone(su(None))
    tc.assertEqual(su(""), "")
    tc.assertEqual(su("hello world"), "hello world")
    s = u"test \N{POUND SIGN}".encode("utf-8")
    tc.assertIs(su(s), s)
    tc.assertEqual(su(u"test \N{POUND SIGN}".encode("latin1")), "test ?")
