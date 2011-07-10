"""Tests for sgf_parser.py."""

from gomill_tests import gomill_test_support

from gomill import sgf_parser

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_is_valid_property_identifier(tc):
    ivpi = sgf_parser.is_valid_property_identifier
    tc.assertIs(ivpi("B"), True)
    tc.assertIs(ivpi("PB"), True)
    tc.assertIs(ivpi("ABCDEFGH"), True)
    tc.assertIs(ivpi("ABCDEFGHI"), False)
    tc.assertIs(ivpi(""), False)
    tc.assertIs(ivpi("b"), False)
    tc.assertIs(ivpi("Player"), False)
    tc.assertIs(ivpi("P2"), False)
    tc.assertIs(ivpi(" PB"), False)
    tc.assertIs(ivpi("PB "), False)
    tc.assertIs(ivpi("P B"), False)
    tc.assertIs(ivpi("PB\x00"), False)

def test_is_valid_property_value(tc):
    ivpv = sgf_parser.is_valid_property_value
    tc.assertIs(ivpv(""), True)
    tc.assertIs(ivpv("hello world"), True)
    tc.assertIs(ivpv("hello\nworld"), True)
    tc.assertIs(ivpv("hello \x00 world"), True)
    tc.assertIs(ivpv("hello \xa3 world"), True)
    tc.assertIs(ivpv("hello \xc2\xa3 world"), True)
    tc.assertIs(ivpv("hello \\-) world"), True)
    tc.assertIs(ivpv("hello (;[) world"), True)
    tc.assertIs(ivpv("[hello world]"), False)
    tc.assertIs(ivpv("hello ] world"), False)
    tc.assertIs(ivpv("hello \\] world"), True)
    tc.assertIs(ivpv("hello world \\"), False)
    tc.assertIs(ivpv("hello world \\\\"), True)
    tc.assertIs(ivpv("x" * 70000), True)

def test_tokeniser(tc):
    tokenise = sgf_parser.tokenise

    tc.assertEqual(tokenise(r"(;B[ah][])")[0],
                   [('D', '('),
                    ('D', ';'),
                    ('I', 'B'),
                    ('V', 'ah'),
                    ('V', ''),
                    ('D', ')')])

    def check_complete(s, *args):
        tokens, tail_index = tokenise(s, *args)
        tc.assertEqual(tail_index, len(s))
        return len(tokens)

    def check_incomplete(s, *args):
        tokens, tail_index = tokenise(s, *args)
        return len(tokens), tail_index

    # check surrounding junk
    tc.assertEqual(check_complete(""), 0)
    tc.assertEqual(check_complete("junk (;B[ah])"), 5)
    tc.assertEqual(check_incomplete("junk"), (0, 0))
    tc.assertEqual(check_incomplete("junk (B[ah])"), (0, 0))
    tc.assertEqual(check_incomplete("(;B[ah]) junk"), (5, 8))

    # check paren-balance count
    tc.assertEqual(check_incomplete("(; ))(([ag]B C[ah])"), (3, 4))
    tc.assertEqual(check_incomplete("(;( )) (;)"), (5, 6))
    tc.assertEqual(check_incomplete("(;(()())) (;)"), (9, 9))

    # check start_position
    tc.assertEqual(check_complete("(; ))(;B[ah])", 4), 5)
    tc.assertEqual(check_complete("(; ))junk (;B[ah])", 4), 5)

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

def test_parser_structure(tc):
    parse_sgf_game = sgf_parser.parse_sgf_game

    def shape(s):
        parsed_game = parse_sgf_game(s)
        return len(parsed_game.sequence), len(parsed_game.children)

    tc.assertEqual(shape("(;C[abc]KO[];B[bc])"), (2, 0))
    tc.assertEqual(shape("initial junk (;C[abc]KO[];B[bc])"), (2, 0))
    tc.assertEqual(shape("(;C[abc]KO[];B[bc]) final junk"), (2, 0))
    tc.assertEqual(shape("(;C[abc]KO[];B[bc]) (;B[ag])"), (2, 0))

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

    tc.assertEqual(shape("(;C[abc]AB[ab][bc];B[bc])"), (2, 0))
    tc.assertEqual(shape("(;C[abc] AB[ab]\n[bc]\t;B[bc])"), (2, 0))
    tc.assertEqual(shape("(;C[abc]KO[];;B[bc])"), (3, 0))
    tc.assertEqual(shape("(;)"), (1, 0))

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

def test_parser_tree_structure(tc):
    parse_sgf_game = sgf_parser.parse_sgf_game

    def shape(s):
        parsed_game = parse_sgf_game(s)
        return len(parsed_game.sequence), len(parsed_game.children)

    tc.assertEqual(shape("(;C[abc]AB[ab](;B[bc]))"), (1, 1))
    tc.assertEqual(shape("(;C[abc]AB[ab](;B[bc])))"), (1, 1))
    tc.assertEqual(shape("(;C[abc]AB[ab](;B[bc])(;B[bd]))"), (1, 2))

    def shapetree(s):
        def _shapetree(parsed_game):
            return (
                len(parsed_game.sequence),
                [_shapetree(pg) for pg in parsed_game.children])
        return _shapetree(parse_sgf_game(s))

    tc.assertEqual(shapetree("(;C[abc]AB[ab](;B[bc])))"),
                   (1, [(1, [])])
                   )
    tc.assertEqual(shapetree("(;C[abc]AB[ab](;B[bc]))))"),
                   (1, [(1, [])])
                   )
    tc.assertEqual(shapetree("(;C[abc]AB[ab](;B[bc])(;B[bd])))"),
                   (1, [(1, []), (1, [])])
                   )
    tc.assertEqual(shapetree("""
        (;C[abc]AB[ab];C[];C[]
          (;B[bc])
          (;B[bd];W[ca] (;B[da])(;B[db];W[ea]) )
        )"""),
        (3, [
            (1, []),
            (2, [(1, []), (2, [])])
        ])
    )

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
    tc.assertRaisesRegexp(ValueError, "property value outside a node",
                          parse_sgf_game, "(;B[ag];(W[ah];B[ai]))")
    tc.assertRaisesRegexp(ValueError, "property value outside a node",
                          parse_sgf_game, "(;B[ag](;W[ah];)B[ai])")
    tc.assertRaisesRegexp(ValueError, "property value outside a node",
                          parse_sgf_game, "(;B[ag](;W[ah])(B[ai]))")

def test_parser_properties(tc):
    parse_sgf_game = sgf_parser.parse_sgf_game

    def props(s):
        parsed_game = parse_sgf_game(s)
        return parsed_game.sequence

    tc.assertEqual(props("(;C[abc]KO[]AB[ai][bh][ee];B[ bc])"),
                   [{'C': ['abc'], 'KO': [''], 'AB': ['ai', 'bh', 'ee']},
                    {'B': [' bc']}])

    tc.assertEqual(props(r"(;C[ab \] \) cd\\])"),
                   [{'C': [r"ab \] \) cd\\"]}])

    tc.assertEqual(props("(;XX[1]YY[2]XX[3]YY[4])"),
                   [{'XX': ['1', '3'], 'YY' : ['2', '4']}])

def test_parse_sgf_collection(tc):
    parse_sgf_collection = sgf_parser.parse_sgf_collection

    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_collection, r"")
    tc.assertRaisesRegexp(ValueError, "no SGF data found",
                          parse_sgf_collection, r"()")

    games = parse_sgf_collection("(;C[abc]AB[ab];X[];X[](;B[bc]))")
    tc.assertEqual(len(games), 1)
    tc.assertEqual(len(games[0].sequence), 3)

    games = parse_sgf_collection("(;X[1];X[2];X[3](;B[bc])) (;Y[1];Y[2])")
    tc.assertEqual(len(games), 2)
    tc.assertEqual(len(games[0].sequence), 3)
    tc.assertEqual(len(games[1].sequence), 2)

    games = parse_sgf_collection(
        "dummy (;X[1];X[2];X[3](;B[bc])) junk (;Y[1];Y[2]) Nonsense")
    tc.assertEqual(len(games), 2)
    tc.assertEqual(len(games[0].sequence), 3)
    tc.assertEqual(len(games[1].sequence), 2)

    games = parse_sgf_collection(
        "(( (;X[1];X[2];X[3](;B[bc])) ();) (;Y[1];Y[2]) )(Nonsense")
    tc.assertEqual(len(games), 2)
    tc.assertEqual(len(games[0].sequence), 3)
    tc.assertEqual(len(games[1].sequence), 2)

    with tc.assertRaises(ValueError) as ar:
        parse_sgf_collection(
            "(( (;X[1];X[2];X[3](;B[bc])) ();) (;Y[1];Y[2]")
    tc.assertEqual(str(ar.exception),
                   "error parsing game 1: unexpected end of SGF data")


def test_parse_compose(tc):
    pc = sgf_parser.parse_compose
    tc.assertEqual(pc("word"), ("word", None))
    tc.assertEqual(pc("word:"), ("word", ""))
    tc.assertEqual(pc("word:?"), ("word", "?"))
    tc.assertEqual(pc("word:123"), ("word", "123"))
    tc.assertEqual(pc("word:123:456"), ("word", "123:456"))
    tc.assertEqual(pc(":123"), ("", "123"))
    tc.assertEqual(pc(r"word\:more"), (r"word\:more", None))
    tc.assertEqual(pc(r"word\:more:?"), (r"word\:more", "?"))
    tc.assertEqual(pc(r"word\\:more:?"), ("word\\\\", "more:?"))
    tc.assertEqual(pc(r"word\\\:more:?"), (r"word\\\:more", "?"))
    tc.assertEqual(pc("word\\\nmore:123"), ("word\\\nmore", "123"))

def test_text_value(tc):
    text_value = sgf_parser.text_value
    tc.assertEqual(text_value("abc "), "abc ")
    tc.assertEqual(text_value("ab c"), "ab c")
    tc.assertEqual(text_value("ab\tc"), "ab c")
    tc.assertEqual(text_value("ab \tc"), "ab  c")
    tc.assertEqual(text_value("ab\nc"), "ab\nc")
    tc.assertEqual(text_value("ab\\\nc"), "abc")
    tc.assertEqual(text_value("ab\\\\\nc"), "ab\\\nc")
    tc.assertEqual(text_value("ab\xa0c"), "ab\xa0c")

    tc.assertEqual(text_value("ab\rc"), "ab\nc")
    tc.assertEqual(text_value("ab\r\nc"), "ab\nc")
    tc.assertEqual(text_value("ab\n\rc"), "ab\nc")
    tc.assertEqual(text_value("ab\r\n\r\nc"), "ab\n\nc")
    tc.assertEqual(text_value("ab\r\n\r\n\rc"), "ab\n\n\nc")
    tc.assertEqual(text_value("ab\\\r\nc"), "abc")
    tc.assertEqual(text_value("ab\\\n\nc"), "ab\nc")

    tc.assertEqual(text_value("ab\\\tc"), "ab c")

    # These can't actually appear as SGF PropValues; anything sane will do
    tc.assertEqual(text_value("abc\\"), "abc")
    tc.assertEqual(text_value("abc]"), "abc]")

def test_simpletext_value(tc):
    simpletext_value = sgf_parser.simpletext_value
    tc.assertEqual(simpletext_value("abc "), "abc ")
    tc.assertEqual(simpletext_value("ab c"), "ab c")
    tc.assertEqual(simpletext_value("ab\tc"), "ab c")
    tc.assertEqual(simpletext_value("ab \tc"), "ab  c")
    tc.assertEqual(simpletext_value("ab\nc"), "ab c")
    tc.assertEqual(simpletext_value("ab\\\nc"), "abc")
    tc.assertEqual(simpletext_value("ab\\\\\nc"), "ab\\ c")
    tc.assertEqual(simpletext_value("ab\xa0c"), "ab\xa0c")

    tc.assertEqual(simpletext_value("ab\rc"), "ab c")
    tc.assertEqual(simpletext_value("ab\r\nc"), "ab c")
    tc.assertEqual(simpletext_value("ab\n\rc"), "ab c")
    tc.assertEqual(simpletext_value("ab\r\n\r\nc"), "ab  c")
    tc.assertEqual(simpletext_value("ab\r\n\r\n\rc"), "ab   c")
    tc.assertEqual(simpletext_value("ab\\\r\nc"), "abc")
    tc.assertEqual(simpletext_value("ab\\\n\nc"), "ab c")

    tc.assertEqual(simpletext_value("ab\\\tc"), "ab c")

    # These can't actually appear as SGF PropValues; anything sane will do
    tc.assertEqual(simpletext_value("abc\\"), "abc")
    tc.assertEqual(simpletext_value("abc]"), "abc]")

