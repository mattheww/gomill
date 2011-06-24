"""Tests for sgf_reader.py."""

from gomill_tests import gomill_test_support

from gomill import sgf_reader

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_basic_reader(tc):
    sgf = sgf_reader.read_sgf("""\
(;AP[testsuite]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc];B[cg];W[df]C[cmt]
;B[tt]C[Final comment])
""")
    tc.assertEqual(sgf.get_size(), 9)
    tc.assertEqual(sgf.get_komi(), 7.5)
    tc.assertIs(sgf.get_handicap(), None)
    tc.assertEqual(sgf.get_player('b'), "Black engine")
    tc.assertEqual(sgf.get_player('w'), "White engine")
    tc.assertEqual(sgf.get_winner(), 'w')
    tc.assertEqual(sgf.get_root_prop('AP'), "testsuite")
    tc.assertEqual(len(sgf.nodes), 4)
    tc.assertEqual(sgf.nodes[3].get('C'), "Final comment")

