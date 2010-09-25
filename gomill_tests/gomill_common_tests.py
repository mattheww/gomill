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
