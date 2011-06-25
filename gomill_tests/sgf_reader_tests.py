"""Tests for sgf_reader.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import ascii_boards
from gomill import sgf_reader

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_parsing(tc):
    def check(s):
        sgf = sgf_reader.parse_sgf(s)
        return len(sgf.get_main_sequence())
    tc.assertEqual(check("(;C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(check("initial junk (;C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(check("(;C[abc]KO[];B[bc]) final junk"), 2)

    tc.assertEqual(check("( ;C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(check("(; C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(check("(;C[abc] KO[];B[bc])"), 2)
    tc.assertEqual(check("(;C[abc]KO[] ;B[bc])"), 2)
    tc.assertEqual(check("(;C[abc]KO[]; B[bc])"), 2)
    tc.assertEqual(check("(;C [abc]KO[];B[bc])"), 2)

    tc.assertEqual(check("(;C[abc]AB[ab][bc];B[bc])"), 2)
    tc.assertEqual(check("(;C[abc]AB[ab] [bc];B[bc])"), 2)

    tc.assertEqual(check("(;C[abc]\nAB[ab]\t[bc];B[bc])"), 2)

    tc.assertEqual(check("(;C[abc]AB[ab][bc](;B[bc]))"), 2)

def test_malformed(tc):
    def read(s):
        sgf_reader.parse_sgf(s)
    tc.assertRaises(ValueError, read, r"")
    tc.assertRaises(ValueError, read, r"B[ag]")
    tc.assertRaises(ValueError, read, r"[ag]")
    tc.assertRaises(ValueError, read, r"(B[ag])")
    tc.assertRaises(ValueError, read, r"([ag])")
    tc.assertRaises(ValueError, read, r"([ag][ah])")
    tc.assertRaises(ValueError, read, r"(;[ag])")
    tc.assertRaises(ValueError, read, r"(;[ag][ah])")
    tc.assertRaises(ValueError, read, r"(;B[ag]([ah]))")
    tc.assertRaises(ValueError, read, r"(;B[ag]")
    tc.assertRaises(ValueError, read, r"(;B[ag)]")
    tc.assertRaises(ValueError, read, r"(;B[ag\])")
    tc.assertRaises(ValueError, read, r"(;B)")
    tc.assertRaises(ValueError, read, r"(;B;W[ah])")
    tc.assertRaises(ValueError, read, r"(;AddBlack[ag])")
    tc.assertRaises(ValueError, read, r"(;+B[ag])")
    tc.assertRaises(ValueError, read, r"(;B+[ag])")
    tc.assertRaises(ValueError, read, r"(;[B][ag])")

    # We don't reject these yet, because we don't track parens
    #tc.assertRaises(ValueError, read, r"(;B[ag];W[ah](;B[ai])")
    #tc.assertRaises(ValueError, read, r"(;)")
    #tc.assertRaises(ValueError, read, r"(;B[ag]())")

def test_value_escaping(tc):
    def check(s):
        sgf = sgf_reader.parse_sgf(s)
        return sgf.root.get("C")
    tc.assertEqual(check(r"(;C[abc]KO[])"), r"abc")
    tc.assertEqual(check(r"(;C[a\\bc]KO[])"), r"a\bc")
    tc.assertEqual(check(r"(;C[a\\bc\]KO[])"), r"a\bc]KO[")
    tc.assertEqual(check(r"(;C[abc\\]KO[])"), r"abc" + "\\")
    tc.assertEqual(check(r"(;C[xxx :\) yyy]KO[])"), r"xxx :) yyy")

def test_string_handling(tc):
    def check(s):
        sgf = sgf_reader.parse_sgf(s)
        return sgf.root.get("C")
    tc.assertEqual(check("(;C[abc ])"), "abc ")
    tc.assertEqual(check("(;C[ab c])"), "ab c")
    tc.assertEqual(check("(;C[ab\tc])"), "ab c")
    tc.assertEqual(check("(;C[ab \tc])"), "ab  c")
    tc.assertEqual(check("(;C[ab\nc])"), "ab\nc")
    tc.assertEqual(check("(;C[ab\\\nc])"), "abc")
    tc.assertEqual(check("(;C[ab\\\\\nc])"), "ab\\\nc")
    tc.assertEqual(check("(;C[ab\xa0c])"), "ab\xa0c")

    tc.assertEqual(check("(;C[ab\rc])"), "ab\nc")
    tc.assertEqual(check("(;C[ab\r\nc])"), "ab\nc")
    tc.assertEqual(check("(;C[ab\n\rc])"), "ab\nc")
    tc.assertEqual(check("(;C[ab\r\n\r\nc])"), "ab\n\nc")
    tc.assertEqual(check("(;C[ab\r\n\r\n\rc])"), "ab\n\n\nc")
    tc.assertEqual(check("(;C[ab\\\r\nc])"), "abc")
    tc.assertEqual(check("(;C[ab\\\n\nc])"), "ab\nc")

    tc.assertEqual(check("(;C[ab\\\tc])"), "ab c")



SAMPLE_SGF = """\
(;AP[testsuite]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc];B[dg];W[ef]C[comment
on two lines];B[];W[tt]C[Final comment])
"""

def test_node(tc):
    sgf = sgf_reader.parse_sgf(
        r"(;KM[6.5]C[sample\: comment]AB[ai][bh][ee]AE[];B[dg])")
    node0 = sgf.get_root_node()
    node1 = sgf.get_main_sequence()[1]
    tc.assertIs(node0.has_property('KM'), True)
    tc.assertIs(node0.has_property('XX'), False)
    tc.assertIs(node1.has_property('KM'), False)
    tc.assertEqual(node0.get_raw('C'), r"sample\: comment")
    tc.assertEqual(node0.get_raw('AB'), "ai")
    tc.assertEqual(node0.get_raw('AE'), "")
    tc.assertRaises(KeyError, node0.get_raw, 'XX')
    tc.assertEqual(node0.get_list('KM'), ['6.5'])
    tc.assertEqual(node0.get_list('AB'), ['ai', 'bh', 'ee'])
    tc.assertEqual(node0.get_list('AE'), [])
    tc.assertRaises(KeyError, node0.get_list, 'XX')
    tc.assertEqual(node0.get('C'), "sample: comment")
    tc.assertEqual(node0.get('AB'), "ai")
    tc.assertRaises(KeyError, node0.get, 'XX')

def test_node_string(tc):
    sgf = sgf_reader.parse_sgf(SAMPLE_SGF)
    node = sgf.get_root_node()
    tc.assertMultiLineEqual(str(node), dedent("""\
    AB[ai][bh][ee]
    AP[testsuite]
    AW[fd][gc]
    CA[utf-8]
    DT[2009-06-06]
    FF[4]
    GM[1]
    KM[7.5]
    PB[Black engine]
    PL[B]
    PW[White engine]
    RE[W+R]
    SZ[9]
    """))

def test_get_move(tc):
    sgf = sgf_reader.parse_sgf(SAMPLE_SGF)
    nodes = sgf.get_main_sequence()
    tc.assertEqual(nodes[0].get_move(), (None, None))
    tc.assertEqual(nodes[1].get_move(), ('b', (2, 3)))
    tc.assertEqual(nodes[2].get_move(), ('w', (3, 4)))
    tc.assertEqual(nodes[3].get_move(), ('b', None))
    tc.assertEqual(nodes[4].get_move(), ('w', None))

def test_node_setup_commands(tc):
    sgf = sgf_reader.parse_sgf(
        r"(;KM[6.5]SZ[9]C[sample\: comment]AB[ai][bh][ee]AE[];B[dg])")
    node0 = sgf.get_root_node()
    node1 = sgf.get_main_sequence()[1]
    tc.assertIs(node0.has_setup_commands(), True)
    tc.assertIs(node1.has_setup_commands(), False)
    tc.assertEqual(node0.get_setup_commands(),
                   (set([(0, 0), (1, 1), (4, 4)]), set(), set()))
    tc.assertEqual(node1.get_setup_commands(),
                   (set(), set(), set()))

def test_sgf_tree(tc):
    sgf = sgf_reader.parse_sgf(SAMPLE_SGF)
    root = sgf.get_root_node()
    nodes = sgf.get_main_sequence()
    tc.assertEqual(len(nodes), 5)
    tc.assertIs(root, nodes[0])
    tc.assertEqual(sgf.get_size(), 9)
    tc.assertEqual(sgf.get_komi(), 7.5)
    tc.assertIs(sgf.get_handicap(), None)
    tc.assertEqual(sgf.get_player('b'), "Black engine")
    tc.assertEqual(sgf.get_player('w'), "White engine")
    tc.assertEqual(sgf.get_winner(), 'w')
    tc.assertEqual(root.get('AP'), "testsuite")
    tc.assertEqual(nodes[2].get('C'), "comment\non two lines")
    tc.assertEqual(nodes[4].get('C'), "Final comment")

_setup_expected = """\
9  .  .  .  .  .  .  .  .  .
8  .  .  .  .  .  .  .  .  .
7  .  .  .  .  .  .  o  .  .
6  .  .  .  .  .  o  .  .  .
5  .  .  .  .  #  .  .  .  .
4  .  .  .  .  .  .  .  .  .
3  .  .  .  .  .  .  .  .  .
2  .  #  .  .  .  .  .  .  .
1  #  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J\
"""

def test_get_setup_and_moves(tc):
    sgf = sgf_reader.parse_sgf(SAMPLE_SGF)
    board, moves = sgf.get_setup_and_moves()
    tc.assertDiagramEqual(ascii_boards.render_board(board), _setup_expected)
    tc.assertEqual(moves,
                   [('b', (2, 3)), ('w', (3, 4)), ('b', None), ('w', None)])

