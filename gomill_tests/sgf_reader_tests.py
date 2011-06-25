"""Tests for sgf_reader.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import sgf_reader

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

SAMPLE_SGF = """\
(;AP[testsuite]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc];B[dg];W[ef]C[comment
on two lines];B[];W[tt]C[Final comment])
"""

def test_basic_reader(tc):
    sgf = sgf_reader.read_sgf(SAMPLE_SGF)
    tc.assertEqual(sgf.get_size(), 9)
    tc.assertEqual(sgf.get_komi(), 7.5)
    tc.assertIs(sgf.get_handicap(), None)
    tc.assertEqual(sgf.get_player('b'), "Black engine")
    tc.assertEqual(sgf.get_player('w'), "White engine")
    tc.assertEqual(sgf.get_winner(), 'w')
    tc.assertEqual(sgf.root.get('AP'), "testsuite")
    nodes = sgf.get_main_sequence()
    tc.assertEqual(len(nodes), 5)
    tc.assertEqual(nodes[2].get('C'), "comment\non two lines")
    tc.assertEqual(nodes[4].get('C'), "Final comment")

def test_node_string(tc):
    sgf = sgf_reader.read_sgf(SAMPLE_SGF)
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
    sgf = sgf_reader.read_sgf(SAMPLE_SGF)
    nodes = sgf.get_main_sequence()
    tc.assertEqual(nodes[0].get_move(), (None, None))
    tc.assertEqual(nodes[1].get_move(), ('b', (2, 3)))
    tc.assertEqual(nodes[2].get_move(), ('w', (3, 4)))
    tc.assertEqual(nodes[3].get_move(), ('b', None))
    tc.assertEqual(nodes[4].get_move(), ('w', None))

def test_malformed(tc):
    def read(s):
        sgf_reader.read_sgf(s)
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

def test_parsing(tc):
    def check(s):
        sgf = sgf_reader.read_sgf(s)
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

def test_value_escaping(tc):
    def check(s):
        sgf = sgf_reader.read_sgf(s)
        return sgf.root.get("C")
    tc.assertEqual(check(r"(;C[abc]KO[])"), r"abc")
    tc.assertEqual(check(r"(;C[a\\bc]KO[])"), r"a\bc")
    tc.assertEqual(check(r"(;C[a\\bc\]KO[])"), r"a\bc]KO[")
    tc.assertEqual(check(r"(;C[abc\\]KO[])"), r"abc" + "\\")
    tc.assertEqual(check(r"(;C[xxx :\) yyy]KO[])"), r"xxx :) yyy")

def test_string_handling(tc):
    def check(s):
        sgf = sgf_reader.read_sgf(s)
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

