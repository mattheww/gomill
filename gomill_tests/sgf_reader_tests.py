"""Tests for sgf_reader.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import ascii_boards
from gomill import sgf_parser
from gomill import sgf_reader

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_value_as_text(tc):
    value_as_text = sgf_reader.value_as_text
    tc.assertEqual(value_as_text("abc "), "abc ")
    tc.assertEqual(value_as_text("ab c"), "ab c")
    tc.assertEqual(value_as_text("ab\tc"), "ab c")
    tc.assertEqual(value_as_text("ab \tc"), "ab  c")
    tc.assertEqual(value_as_text("ab\nc"), "ab\nc")
    tc.assertEqual(value_as_text("ab\\\nc"), "abc")
    tc.assertEqual(value_as_text("ab\\\\\nc"), "ab\\\nc")
    tc.assertEqual(value_as_text("ab\xa0c"), "ab\xa0c")

    tc.assertEqual(value_as_text("ab\rc"), "ab\nc")
    tc.assertEqual(value_as_text("ab\r\nc"), "ab\nc")
    tc.assertEqual(value_as_text("ab\n\rc"), "ab\nc")
    tc.assertEqual(value_as_text("ab\r\n\r\nc"), "ab\n\nc")
    tc.assertEqual(value_as_text("ab\r\n\r\n\rc"), "ab\n\n\nc")
    tc.assertEqual(value_as_text("ab\\\r\nc"), "abc")
    tc.assertEqual(value_as_text("ab\\\n\nc"), "ab\nc")

    tc.assertEqual(value_as_text("ab\\\tc"), "ab c")

    # These can't actually appear as SGF PropValues; anything sane will do
    tc.assertEqual(value_as_text("abc\\"), "abc")
    tc.assertEqual(value_as_text("abc]"), "abc]")

def test_value_as_simpletext(tc):
    value_as_simpletext = sgf_reader.value_as_simpletext
    tc.assertEqual(value_as_simpletext("abc "), "abc ")
    tc.assertEqual(value_as_simpletext("ab c"), "ab c")
    tc.assertEqual(value_as_simpletext("ab\tc"), "ab c")
    tc.assertEqual(value_as_simpletext("ab \tc"), "ab  c")
    tc.assertEqual(value_as_simpletext("ab\nc"), "ab c")
    tc.assertEqual(value_as_simpletext("ab\\\nc"), "abc")
    tc.assertEqual(value_as_simpletext("ab\\\\\nc"), "ab\\ c")
    tc.assertEqual(value_as_simpletext("ab\xa0c"), "ab\xa0c")

    tc.assertEqual(value_as_simpletext("ab\rc"), "ab c")
    tc.assertEqual(value_as_simpletext("ab\r\nc"), "ab c")
    tc.assertEqual(value_as_simpletext("ab\n\rc"), "ab c")
    tc.assertEqual(value_as_simpletext("ab\r\n\r\nc"), "ab  c")
    tc.assertEqual(value_as_simpletext("ab\r\n\r\n\rc"), "ab   c")
    tc.assertEqual(value_as_simpletext("ab\\\r\nc"), "abc")
    tc.assertEqual(value_as_simpletext("ab\\\n\nc"), "ab c")

    tc.assertEqual(value_as_simpletext("ab\\\tc"), "ab c")

    # These can't actually appear as SGF PropValues; anything sane will do
    tc.assertEqual(value_as_simpletext("abc\\"), "abc")
    tc.assertEqual(value_as_simpletext("abc]"), "abc]")

def test_interpret_compose(tc):
    ic = sgf_reader.interpret_compose
    tc.assertEqual(ic("word"), ("word", None))
    tc.assertEqual(ic("word:"), ("word", ""))
    tc.assertEqual(ic("word:?"), ("word", "?"))
    tc.assertEqual(ic("word:123"), ("word", "123"))
    tc.assertEqual(ic("word:123:456"), ("word", "123:456"))
    tc.assertEqual(ic(":123"), ("", "123"))
    tc.assertEqual(ic(r"word\:more"), (r"word\:more", None))
    tc.assertEqual(ic(r"word\:more:?"), (r"word\:more", "?"))
    tc.assertEqual(ic(r"word\\:more:?"), ("word\\\\", "more:?"))
    tc.assertEqual(ic(r"word\\\:more:?"), (r"word\\\:more", "?"))
    tc.assertEqual(ic("word\\\nmore:123"), ("word\\\nmore", "123"))

def test_tokeniser(tc):
    tokenise = sgf_parser.tokenise

    tc.assertEqual(tokenise(r"(;B[ah][])")[0],
                   [('D', '('),
                    ('D', ';'),
                    ('I', 'B'),
                    ('V', 'ah'),
                    ('V', ''),
                    ('D', ')')])

    def check_complete(s):
        tokens, tail_index = tokenise(s)
        tc.assertEqual(tail_index, len(s))
        return len(tokens)

    def check_incomplete(s):
        tokens, tail_index = tokenise(s)
        return len(tokens), tail_index

    tc.assertEqual(check_complete(""), 0)
    tc.assertEqual(check_complete("junk (;B[ah])"), 5)
    tc.assertEqual(check_incomplete("junk"), (0, 0))
    tc.assertEqual(check_incomplete("junk (B[ah])"), (0, 0))
    tc.assertEqual(check_incomplete("(;B[ah]) junk"), (5, 8))
    tc.assertEqual(check_complete("(;))(([ag]B C[ah])"), 11)

    tc.assertEqual(check_complete("(;XX[abc][def]KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("( ;XX[abc][def]KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("(; XX[abc][def]KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX [abc][def]KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc] [def]KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def] KO[];B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def]KO [];B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def]KO[] ;B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def]KO[]; B[bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def]KO[];B [bc])"), 11)
    tc.assertEqual(check_complete("(;XX[abc][def]KO[];B[bc] )"), 11)

    tc.assertEqual(check_complete("( ;\nB\t[ah]\f[ef]\v)"), 6)
    tc.assertEqual(check_complete("(;[Random :\nstu@ff][ef]"), 4)
    tc.assertEqual(check_complete("(;[ah)])"), 4)

    tc.assertEqual(check_incomplete("(;B[ag"), (3, 3))
    tc.assertEqual(check_incomplete("(;B[ag)"), (3, 3))
    tc.assertEqual(check_incomplete("(;AddBlack[ag])"), (3, 3))
    tc.assertEqual(check_incomplete("(;+B[ag])"), (2, 2))
    tc.assertEqual(check_incomplete("(;B+[ag])"), (3, 3))
    tc.assertEqual(check_incomplete("(;B[ag]+)"), (4, 7))

    tc.assertEqual(check_complete(r"(;[ab \] cd][ef]"), 4)
    tc.assertEqual(check_complete(r"(;[ab \] cd\\][ef]"), 4)
    tc.assertEqual(check_complete(r"(;[ab \] cd\\\\][ef]"), 4)
    tc.assertEqual(check_complete(r"(;[ab \] \\\] cd][ef]"), 4)
    tc.assertEqual(check_incomplete(r"(;B[ag\])"), (3, 3))
    tc.assertEqual(check_incomplete(r"(;B[ag\\\])"), (3, 3))

def test_parser(tc):
    parse_sgf_game = sgf_parser.parse_sgf_game

    # FIXME: Rewrite to use only the parser-level API
    def parse_len(s):
        sgf = sgf_reader.sgf_game_from_string(s)
        return len(sgf.get_main_sequence())

    tc.assertEqual(parse_len("(;C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(parse_len("initial junk (;C[abc]KO[];B[bc])"), 2)
    tc.assertEqual(parse_len("(;C[abc]KO[];B[bc]) final junk"), 2)
    tc.assertEqual(parse_len("(;C[abc]KO[];B[bc]) (;B[ag])"), 2)

    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"junk")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"()")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"(B[ag])")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"B[ag]")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_game, r"[ag]")

    tc.assertEqual(parse_len("(;C[abc]AB[ab][bc];B[bc])"), 2)
    tc.assertEqual(parse_len("(;C[abc] AB[ab]\n[bc]\t;B[bc])"), 2)
    tc.assertEqual(parse_len("(;C[abc]AB[ab](;B[bc]))"), 2)
    tc.assertEqual(parse_len("(;C[abc]KO[];;B[bc])"), 3)
    tc.assertEqual(parse_len("(;)"), 1)

    tc.assertRaisesRegexp(ValueError, "property with no values",
                          parse_sgf_game, r"(;B)")
    tc.assertRaisesRegexp(ValueError, "unexpected value",
                          parse_sgf_game, r"(;[ag])")
    tc.assertRaisesRegexp(ValueError, "unexpected value",
                          parse_sgf_game, r"(;[ag][ah])")
    tc.assertRaisesRegexp(ValueError, "unexpected value",
                          parse_sgf_game, r"(;[B][ag])")
    tc.assertRaisesRegexp(ValueError, "unexpected end of SGF data",
                          parse_sgf_game, r"(;B[ag]")
    tc.assertRaisesRegexp(ValueError, "unexpected end of SGF data",
                          parse_sgf_game, r"(;B[ag][)]")
    tc.assertRaisesRegexp(ValueError, "property with no values",
                          parse_sgf_game, r"(;B;W[ah])")
    tc.assertRaisesRegexp(ValueError, "unexpected value",
                          parse_sgf_game, r"(;B[ag](;[ah]))")
    tc.assertRaisesRegexp(ValueError, "property with no values",
                          parse_sgf_game, r"(;B W[ag])")

    tc.assertRaisesRegexp(ValueError, "property value outside a node",
                          parse_sgf_game, "(;B[ag];(W[ah];B[ai]))")
    tc.assertRaisesRegexp(ValueError, "property value outside a node",
                          parse_sgf_game, "(;B[ag](;W[ah];)B[ai])")

    tc.assertEqual(parse_len("(;C[abc]AB[ab](;B[bc])(;B[bd]))"), 2)
    tc.assertEqual(parse_len("(;C[abc]AB[ab](;B[bc])))"), 2)

    tc.assertRaisesRegexp(ValueError, "unexpected end of SGF data",
                          parse_sgf_game, "(;B[ag];W[ah](;B[ai])")
    tc.assertRaisesRegexp(ValueError, "empty sequence",
                          parse_sgf_game, "(;B[ag];())")
    tc.assertRaisesRegexp(ValueError, "empty sequence",
                          parse_sgf_game, "(;B[ag]())")
    tc.assertRaisesRegexp(ValueError, "empty sequence",
                          parse_sgf_game, "(;B[ag]((;W[ah])(;W[ai]))")
    tc.assertRaisesRegexp(ValueError, "unexpected node",
                          parse_sgf_game, "(;B[ag];W[ah](;B[ai]);W[bd])")

def test_text_values(tc):
    def check(s):
        sgf = sgf_reader.sgf_game_from_string(s)
        return sgf.get_root_node().get("C")
    # Round-trip check of Text values through tokeniser, parser, and
    # value_as_text().
    tc.assertEqual(check(r"(;C[abc]KO[])"), r"abc")
    tc.assertEqual(check(r"(;C[a\\bc]KO[])"), r"a\bc")
    tc.assertEqual(check(r"(;C[a\\bc\]KO[])"), r"a\bc]KO[")
    tc.assertEqual(check(r"(;C[abc\\]KO[])"), r"abc" + "\\")
    tc.assertEqual(check(r"(;C[abc\\\]KO[])"), r"abc\]KO[")
    tc.assertEqual(check(r"(;C[abc\\\\]KO[])"), r"abc" + "\\\\")
    tc.assertEqual(check(r"(;C[abc\\\\\]KO[])"), r"abc\\]KO[")
    tc.assertEqual(check(r"(;C[xxx :\) yyy]KO[])"), r"xxx :) yyy")
    tc.assertEqual(check("(;C[ab\\\nc])"), "abc")
    tc.assertEqual(check("(;C[ab\nc])"), "ab\nc")


SAMPLE_SGF = """\
(;AP[testsuite:0]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc];B[dg];W[ef]C[comment
on two lines];B[];W[tt]C[Final comment])
"""

def test_node(tc):
    sgf = sgf_reader.sgf_game_from_string(
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
    tc.assertRaises(KeyError, node0.get_raw, 'XX')

def test_property_combination(tc):
    sgf = sgf_reader.sgf_game_from_string("(;XX[1]YY[2]XX[3]YY[4])")
    node0 = sgf.get_root_node()
    tc.assertEqual(node0.get_list("XX"), ["1", "3"])
    tc.assertEqual(node0.get_list("YY"), ["2", "4"])

def test_node_string(tc):
    sgf = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    node = sgf.get_root_node()
    tc.assertMultiLineEqual(str(node), dedent("""\
    AB[ai][bh][ee]
    AP[testsuite:0]
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

def test_node_get(tc):
    sgf = sgf_reader.sgf_game_from_string(dedent(r"""
    (;AP[testsuite:0]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
    PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc]BM[2]
    EV[Test
    event]
    C[123:\)
    abc];
    B[dg]KO[]AR[ab:cd][de:fg]FG[515:first move]
    LB[ac:lbl][bc:lbl2])
    """))
    root = sgf.get_root_node()
    node1 = sgf.get_main_sequence()[1]
    tc.assertRaises(KeyError, root.get, 'XX')
    tc.assertEqual(root.get('C'), "123:)\nabc")          # Text
    tc.assertEqual(root.get('EV'), "Test event")         # Simpletext
    tc.assertEqual(root.get('BM'), 2)                    # Double
    tc.assertIs(node1.get('KO'), True)                   # None
    tc.assertEqual(root.get('KM'), 7.5)                  # Real
    tc.assertEqual(root.get('GM'), 1)                    # Number
    tc.assertEqual(root.get('PL'), 'b')                  # Color
    tc.assertEqual(node1.get('B'), (2, 3))               # Point
    tc.assertEqual(root.get('AB'),
                   set([(0, 0), (1, 1), (4, 4)]))        # List of Point
    tc.assertEqual(root.get('AP'), ("testsuite", "0"))   # Application
    tc.assertEqual(node1.get('AR'),
                   [((7, 0), (5, 2)), ((4, 3), (2, 5))]) # Arrow
    tc.assertEqual(node1.get('FG'), (515, "first move")) # Figure
    tc.assertEqual(node1.get('LB'),
                   [((6, 0), "lbl"), ((6, 1), "lbl2")])  # Label

def test_node_get_move(tc):
    sgf = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    nodes = sgf.get_main_sequence()
    tc.assertEqual(nodes[0].get_move(), (None, None))
    tc.assertEqual(nodes[1].get_move(), ('b', (2, 3)))
    tc.assertEqual(nodes[2].get_move(), ('w', (3, 4)))
    tc.assertEqual(nodes[3].get_move(), ('b', None))
    tc.assertEqual(nodes[4].get_move(), ('w', None))

def test_node_setup_commands(tc):
    sgf = sgf_reader.sgf_game_from_string(
        r"(;KM[6.5]SZ[9]C[sample\: comment]AB[ai][bh][ee]AE[];B[dg])")
    node0 = sgf.get_root_node()
    node1 = sgf.get_main_sequence()[1]
    tc.assertIs(node0.has_setup_commands(), True)
    tc.assertIs(node1.has_setup_commands(), False)
    tc.assertEqual(node0.get_setup_commands(),
                   (set([(0, 0), (1, 1), (4, 4)]), set(), set()))
    tc.assertEqual(node1.get_setup_commands(),
                   (set(), set(), set()))

def test_sgf_game(tc):
    sgf = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    root = sgf.get_root_node()
    nodes = sgf.get_main_sequence()
    tc.assertEqual(len(nodes), 5)
    # FIXME: find a better test?
    tc.assertIs(root.props_by_id, nodes[0].props_by_id)
    tc.assertEqual(sgf.get_size(), 9)
    tc.assertEqual(sgf.get_komi(), 7.5)
    tc.assertIs(sgf.get_handicap(), None)
    tc.assertEqual(sgf.get_player('b'), "Black engine")
    tc.assertEqual(sgf.get_player('w'), "White engine")
    tc.assertEqual(sgf.get_winner(), 'w')
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
    sgf = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    board, moves = sgf.get_setup_and_moves()
    tc.assertDiagramEqual(ascii_boards.render_board(board), _setup_expected)
    tc.assertEqual(moves,
                   [('b', (2, 3)), ('w', (3, 4)), ('b', None), ('w', None)])

# FIXME: rename
def test_tree_view(tc):
    # FIXME: Test with a branching tree!
    game = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    # FIXME: rename
    tree = game.get_root_node()
    tc.assertEqual(len(tree.children()), 1)
    tc.assertEqual(tree.children()[0].get_raw('B'), "dg")
    tc.assertFalse(tree.children() is tree.children())

    tc.assertIs(tree.children()[0], tree[0])
    tc.assertIs(tree.children()[0], tree[-1])
    tc.assertEqual(len(tree), 1)
    tc.assertEqual([node for node in tree], tree.children())
    with tc.assertRaises(IndexError):
        tree[1]
    tc.assertTrue(tree)
    leaf = tree[0][0][0][0]
    tc.assertEqual(len(leaf), 0)
    tc.assertFalse(leaf)

    # check ok when first retrieval is by index
    game2 = sgf_reader.sgf_game_from_string(SAMPLE_SGF)
    tree2 = game2.get_root_node()
    tc.assertIs(tree2[0], tree2.children()[0])

