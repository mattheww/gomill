"""Tests for sgf_properties.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import sgf_properties

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_interpret_simpletext(tc):
    def interpret(s, encoding):
        context = sgf_properties._Context(19, encoding)
        return sgf_properties.interpret_simpletext(s, context)
    tc.assertEqual(interpret("a\nb\\\\c", "utf-8"), "a b\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(interpret(u.encode("utf-8"), "UTF-8"),
                   u.encode("utf-8"))
    tc.assertEqual(interpret(u.encode("iso-8859-1"), "ISO-8859-1"),
                   u.encode("utf-8"))
    tc.assertRaises(UnicodeDecodeError, interpret,
                    u.encode("iso-8859-1"), "UTF-8")
    tc.assertRaises(UnicodeDecodeError, interpret, u.encode("utf-8"), "ASCII")

def test_serialise_simpletext(tc):
    def serialise(s, encoding):
        context = sgf_properties._Context(19, encoding)
        return sgf_properties.serialise_simpletext(s, context)
    tc.assertEqual(serialise("ab\\c", "utf-8"), "ab\\\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(serialise(u.encode("utf-8"), "UTF-8"),
                   u.encode("utf-8"))
    tc.assertEqual(serialise(u.encode("utf-8"), "ISO-8859-1"),
                   u.encode("iso-8859-1"))
    tc.assertRaises(UnicodeEncodeError, serialise,
                    u"\N{EN DASH}".encode("utf-8"), "ISO-8859-1")

def test_interpret_text(tc):
    def interpret(s, encoding):
        context = sgf_properties._Context(19, encoding)
        return sgf_properties.interpret_text(s, context)
    tc.assertEqual(interpret("a\nb\\\\c", "utf-8"), "a\nb\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(interpret(u.encode("utf-8"), "UTF-8"),
                   u.encode("utf-8"))
    tc.assertEqual(interpret(u.encode("iso-8859-1"), "ISO-8859-1"),
                   u.encode("utf-8"))
    tc.assertRaises(UnicodeDecodeError, interpret,
                    u.encode("iso-8859-1"), "UTF-8")
    tc.assertRaises(UnicodeDecodeError, interpret, u.encode("utf-8"), "ASCII")

def test_serialise_text(tc):
    def serialise(s, encoding):
        context = sgf_properties._Context(19, encoding)
        return sgf_properties.serialise_text(s, context)
    tc.assertEqual(serialise("ab\\c", "utf-8"), "ab\\\\c")
    u = u"test \N{POUND SIGN}"
    tc.assertEqual(serialise(u.encode("utf-8"), "UTF-8"),
                   u.encode("utf-8"))
    tc.assertEqual(serialise(u.encode("utf-8"), "ISO-8859-1"),
                   u.encode("iso-8859-1"))
    tc.assertRaises(UnicodeEncodeError, serialise,
                    u"\N{EN DASH}".encode("utf-8"), "ISO-8859-1")


def test_interpret_number(tc):
    interpret_number = sgf_properties.interpret_number
    tc.assertEqual(interpret_number("1"), 1)
    tc.assertIs(type(interpret_number("1")), int)
    tc.assertEqual(interpret_number("0"), 0)
    tc.assertEqual(interpret_number("-1"), -1)
    tc.assertEqual(interpret_number("+1"), 1)
    tc.assertRaises(ValueError, interpret_number, "1.5")
    tc.assertRaises(ValueError, interpret_number, "0xaf")
    tc.assertRaises(TypeError, interpret_number, 1)


def test_interpret_real(tc):
    interpret_real = sgf_properties.interpret_real
    tc.assertEqual(interpret_real("1"), 1.0)
    tc.assertIs(type(interpret_real("1")), float)
    tc.assertEqual(interpret_real("0"), 0.0)
    tc.assertEqual(interpret_real("1.0"), 1.0)
    tc.assertEqual(interpret_real("1.5"), 1.5)
    tc.assertEqual(interpret_real("-1.5"), -1.5)
    tc.assertEqual(interpret_real("+0.5"), 0.5)
    tc.assertRaises(ValueError, interpret_real, "+")
    tc.assertRaises(ValueError, interpret_real, "0xaf")
    tc.assertRaises(ValueError, interpret_real, "inf")
    tc.assertRaises(ValueError, interpret_real, "-inf")
    tc.assertRaises(ValueError, interpret_real, "NaN")
    tc.assertRaises(ValueError, interpret_real, "1e400")
    #tc.assertRaises(TypeError, interpret_real, 1.0)

def test_serialise_real(tc):
    serialise_real = sgf_properties.serialise_real
    tc.assertEqual(serialise_real(1), "1")
    tc.assertEqual(serialise_real(-1), "-1")
    tc.assertEqual(serialise_real(1.0), "1")
    tc.assertEqual(serialise_real(-1.0), "-1")
    tc.assertEqual(serialise_real(1.5), "1.5")
    tc.assertEqual(serialise_real(-1.5), "-1.5")
    tc.assertEqual(serialise_real(0.001), "0.001")
    tc.assertEqual(serialise_real(0.0001), "0.0001")
    tc.assertEqual(serialise_real(0.00001), "0")
    tc.assertEqual(serialise_real(1e15), "1000000000000000")
    tc.assertEqual(serialise_real(1e16), "10000000000000000")
    tc.assertEqual(serialise_real(1e17), "100000000000000000")
    tc.assertEqual(serialise_real(1e18), "1000000000000000000")
    tc.assertEqual(serialise_real(-1e18), "-1000000000000000000")
    # 1e400 is inf
    tc.assertRaises(ValueError, serialise_real, 1e400)
    # Python 2.5 returns 0
    #tc.assertRaises(ValueError, serialise_real, float("NaN"))


def test_interpret_move(tc):
    def interpret_move(s, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_move(s, context)
    tc.assertEqual(interpret_move("aa", 19), (18, 0))
    tc.assertEqual(interpret_move("ai", 19), (10, 0))
    tc.assertEqual(interpret_move("ba",  9), (8, 1))
    tc.assertEqual(interpret_move("tt", 21), (1, 19))
    tc.assertIs(interpret_move("tt", 19), None)
    tc.assertIs(interpret_move("", 19), None)
    tc.assertIs(interpret_move("", 21), None)
    tc.assertRaises(ValueError, interpret_move, "Aa", 19)
    tc.assertRaises(ValueError, interpret_move, "aA", 19)
    tc.assertRaises(ValueError, interpret_move, "aaa", 19)
    tc.assertRaises(ValueError, interpret_move, "a", 19)
    tc.assertRaises(ValueError, interpret_move, "au", 19)
    tc.assertRaises(ValueError, interpret_move, "ua", 19)
    tc.assertRaises(ValueError, interpret_move, "a`", 19)
    tc.assertRaises(ValueError, interpret_move, "`a", 19)
    tc.assertRaises(ValueError, interpret_move, "11", 19)
    tc.assertRaises(ValueError, interpret_move, " aa", 19)
    tc.assertRaises(ValueError, interpret_move, "aa\x00", 19)
    tc.assertRaises(TypeError, interpret_move, None, 19)
    #tc.assertRaises(TypeError, interpret_move, ('a', 'a'), 19)

def test_serialise_move(tc):
    def serialise_move(s, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.serialise_move(s, context)
    tc.assertEqual(serialise_move((18, 0), 19), "aa")
    tc.assertEqual(serialise_move((10, 0), 19), "ai")
    tc.assertEqual(serialise_move((8, 1), 19), "bk")
    tc.assertEqual(serialise_move((8, 1), 9), "ba")
    tc.assertEqual(serialise_move((1, 19), 21), "tt")
    tc.assertEqual(serialise_move(None, 19), "tt")
    tc.assertEqual(serialise_move(None, 20), "")
    tc.assertRaises(ValueError, serialise_move, (3, 3), 0)
    tc.assertRaises(ValueError, serialise_move, (3, 3), 27)
    tc.assertRaises(ValueError, serialise_move, (9, 0), 9)
    tc.assertRaises(ValueError, serialise_move, (-1, 0), 9)
    tc.assertRaises(ValueError, serialise_move, (0, 9), 9)
    tc.assertRaises(ValueError, serialise_move, (0, -1), 9)
    tc.assertRaises(TypeError, serialise_move, (1, 1.5), 9)

def test_interpret_point(tc):
    def interpret_point(s, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_point(s, context)
    tc.assertEqual(interpret_point("aa", 19), (18, 0))
    tc.assertEqual(interpret_point("ai", 19), (10, 0))
    tc.assertEqual(interpret_point("ba",  9), (8, 1))
    tc.assertEqual(interpret_point("tt", 21), (1, 19))
    tc.assertRaises(ValueError, interpret_point, "tt", 19)
    tc.assertRaises(ValueError, interpret_point, "", 19)
    tc.assertRaises(ValueError, interpret_point, "", 21)
    tc.assertRaises(ValueError, interpret_point, "Aa", 19)
    tc.assertRaises(ValueError, interpret_point, "aA", 19)
    tc.assertRaises(ValueError, interpret_point, "aaa", 19)
    tc.assertRaises(ValueError, interpret_point, "a", 19)
    tc.assertRaises(ValueError, interpret_point, "au", 19)
    tc.assertRaises(ValueError, interpret_point, "ua", 19)
    tc.assertRaises(ValueError, interpret_point, "a`", 19)
    tc.assertRaises(ValueError, interpret_point, "`a", 19)
    tc.assertRaises(ValueError, interpret_point, "11", 19)
    tc.assertRaises(ValueError, interpret_point, " aa", 19)
    tc.assertRaises(ValueError, interpret_point, "aa\x00", 19)
    tc.assertRaises(TypeError, interpret_point, None, 19)
    #tc.assertRaises(TypeError, interpret_point, ('a', 'a'), 19)

def test_serialise_point(tc):
    def serialise_point(s, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.serialise_point(s, context)
    tc.assertEqual(serialise_point((18, 0), 19), "aa")
    tc.assertEqual(serialise_point((10, 0), 19), "ai")
    tc.assertEqual(serialise_point((8, 1), 19), "bk")
    tc.assertEqual(serialise_point((8, 1), 9), "ba")
    tc.assertEqual(serialise_point((1, 19), 21), "tt")
    tc.assertRaises(ValueError, serialise_point, None, 19)
    tc.assertRaises(ValueError, serialise_point, None, 20)
    tc.assertRaises(ValueError, serialise_point, (3, 3), 0)
    tc.assertRaises(ValueError, serialise_point, (3, 3), 27)
    tc.assertRaises(ValueError, serialise_point, (9, 0), 9)
    tc.assertRaises(ValueError, serialise_point, (-1, 0), 9)
    tc.assertRaises(ValueError, serialise_point, (0, 9), 9)
    tc.assertRaises(ValueError, serialise_point, (0, -1), 9)
    tc.assertRaises(TypeError, serialise_point, (1, 1.5), 9)


def test_interpret_point_list(tc):
    def ipl(l, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_point_list(l, context)
    tc.assertEqual(ipl([], 19),
                   set())
    tc.assertEqual(ipl(["aa"], 19),
                   set([(18, 0)]))
    tc.assertEqual(ipl(["aa", "ai"], 19),
                   set([(18, 0), (10, 0)]))
    tc.assertEqual(ipl(["ab:bc"], 19),
                   set([(16, 0), (16, 1), (17, 0), (17, 1)]))
    tc.assertEqual(ipl(["ab:bc", "aa"], 19),
                   set([(18, 0), (16, 0), (16, 1), (17, 0), (17, 1)]))
    # overlap is forbidden by the spec, but we accept it
    tc.assertEqual(ipl(["aa", "aa"], 19),
                   set([(18, 0)]))
    tc.assertEqual(ipl(["ab:bc", "bb:bc"], 19),
                   set([(16, 0), (16, 1), (17, 0), (17, 1)]))
    # 1x1 rectangles are forbidden by the spec, but we accept them
    tc.assertEqual(ipl(["aa", "bb:bb"], 19),
                   set([(18, 0), (17, 1)]))
    # 'backwards' rectangles are forbidden by the spec, and we reject them
    tc.assertRaises(ValueError, ipl, ["ab:aa"], 19)
    tc.assertRaises(ValueError, ipl, ["ba:aa"], 19)
    tc.assertRaises(ValueError, ipl, ["bb:aa"], 19)

    tc.assertRaises(ValueError, ipl, ["aa", "tt"], 19)
    tc.assertRaises(ValueError, ipl, ["aa", ""], 19)
    tc.assertRaises(ValueError, ipl, ["aa:", "aa"], 19)
    tc.assertRaises(ValueError, ipl, ["aa:tt", "aa"], 19)
    tc.assertRaises(ValueError, ipl, ["tt:aa", "aa"], 19)

def test_compressed_point_list_spec_example(tc):
    # Checks the examples at http://www.red-bean.com/sgf/DD_VW.html
    def sgf_point(move, size):
        row, col = move
        row = size - row - 1
        col_s = "abcdefghijklmnopqrstuvwxy"[col]
        row_s = "abcdefghijklmnopqrstuvwxy"[row]
        return col_s + row_s

    def ipl(l, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_point_list(l, context)
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["ac:ic"], 9)),
        set(["ac", "bc", "cc", "dc", "ec", "fc", "gc", "hc", "ic"]))
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["ae:ie"], 9)),
        set(["ae", "be", "ce", "de", "ee", "fe", "ge", "he", "ie"]))
    tc.assertEqual(
        set(sgf_point(move, 9) for move in ipl(["aa:bi", "ca:ce"], 9)),
        set(["aa", "ab", "ac", "ad", "ae", "af", "ag", "ah", "ai",
             "bi", "bh", "bg", "bf", "be", "bd", "bc", "bb", "ba",
             "ca", "cb", "cc", "cd", "ce"]))

def test_serialise_point_list(tc):
    def ipl(l, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_point_list(l, context)
    def spl(l, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.serialise_point_list(l, context)

    tc.assertEqual(spl([(18, 0), (17, 1)], 19), ['aa', 'bb'])
    tc.assertEqual(spl([(17, 1), (18, 0)], 19), ['aa', 'bb'])
    tc.assertEqual(spl([], 9), [])
    tc.assertEqual(ipl(spl([(1,2), (3,4), (4,5)], 19), 19),
                   set([(1,2), (3,4), (4,5)]))
    tc.assertRaises(ValueError, spl, [(18, 0), None], 19)


def test_AP(tc):
    def serialise(arg):
        context = sgf_properties._Context(19, "UTF-8")
        return sgf_properties.serialise_AP(arg, context)
    def interpret(arg):
        context = sgf_properties._Context(19, "UTF-8")
        return sgf_properties.interpret_AP(arg, context)

    tc.assertEqual(serialise(("foo:bar", "2\n3")), "foo\\:bar:2\n3")
    tc.assertEqual(interpret("foo\\:bar:2 3"), ("foo:bar", "2 3"))
    tc.assertEqual(interpret("foo bar"), ("foo bar", ""))

def test_ARLN(tc):
    def serialise(arg, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.serialise_ARLN_list(arg, context)
    def interpret(arg, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_ARLN_list(arg, context)

    tc.assertEqual(serialise([], 19), [])
    tc.assertEqual(interpret([], 19), [])
    tc.assertEqual(serialise([((7, 0), (5, 2)), ((4, 3), (2, 5))], 9),
                   ['ab:cd', 'de:fg'])
    tc.assertEqual(interpret(['ab:cd', 'de:fg'], 9),
                   [((7, 0), (5, 2)), ((4, 3), (2, 5))])
    tc.assertRaises(ValueError, serialise, [((7, 0), None)], 9)
    tc.assertRaises(ValueError, interpret, ['ab:tt', 'de:fg'], 9)

def test_FG(tc):
    def serialise(arg):
        context = sgf_properties._Context(19, "UTF-8")
        return sgf_properties.serialise_FG(arg, context)
    def interpret(arg):
        context = sgf_properties._Context(19, "UTF-8")
        return sgf_properties.interpret_FG(arg, context)
    tc.assertEqual(serialise(None), "")
    tc.assertEqual(interpret(""), None)
    tc.assertEqual(serialise((515, "th]is")), "515:th\\]is")
    tc.assertEqual(interpret("515:th\\]is"), (515, "th]is"))

def test_LB(tc):
    def serialise(arg, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.serialise_LB_list(arg, context)
    def interpret(arg, size):
        context = sgf_properties._Context(size, "UTF-8")
        return sgf_properties.interpret_LB_list(arg, context)
    tc.assertEqual(serialise([], 19), [])
    tc.assertEqual(interpret([], 19), [])
    tc.assertEqual(
        serialise([((6, 0), "lbl"), ((6, 1), "lb]l2")], 9),
        ["ac:lbl", "bc:lb\\]l2"])
    tc.assertEqual(
        interpret(["ac:lbl", "bc:lb\\]l2"], 9),
        [((6, 0), "lbl"), ((6, 1), "lb]l2")])
    tc.assertRaises(ValueError, serialise, [(None, "lbl")], 9)
    tc.assertRaises(ValueError, interpret, [':lbl', 'de:lbl2'], 9)


def test_presenter_interpret(tc):
    p9 = sgf_properties.Presenter(9, "UTF-8")
    p19 = sgf_properties.Presenter(19, "UTF-8")
    tc.assertEqual(p9.interpret('KO', [""]), True)
    tc.assertEqual(p9.interpret('SZ', ["9"]), 9)
    tc.assertRaisesRegexp(ValueError, "multiple values",
                          p9.interpret, 'SZ', ["9", "blah"])
    tc.assertEqual(p9.interpret('CR', ["ab", "cd"]), set([(5, 2), (7, 0)]))
    tc.assertRaises(ValueError, p9.interpret, 'SZ', [])
    tc.assertRaises(ValueError, p9.interpret, 'CR', [])
    tc.assertEqual(p9.interpret('DD', [""]), set())
    # all lists are treated like elists
    tc.assertEqual(p9.interpret('CR', [""]), set())

def test_presenter_serialise(tc):
    p9 = sgf_properties.Presenter(9, "UTF-8")
    p19 = sgf_properties.Presenter(19, "UTF-8")

    tc.assertEqual(p9.serialise('KO', True), [""])
    tc.assertEqual(p9.serialise('SZ', 9), ["9"])
    tc.assertEqual(p9.serialise('KM', 3.5), ["3.5"])
    tc.assertEqual(p9.serialise('C', "foo\\:b]ar\n"), ["foo\\\\:b\\]ar\n"])
    tc.assertEqual(p19.serialise('B', (1, 2)), ["cr"])
    tc.assertEqual(p9.serialise('B', None), ["tt"])
    tc.assertEqual(p19.serialise('AW', set([(17, 1), (18, 0)])),["aa", "bb"])
    tc.assertEqual(p9.serialise('DD', [(1, 2), (3, 4)]), ["ch", "ef"])
    tc.assertEqual(p9.serialise('DD', []), [""])
    tc.assertRaisesRegexp(ValueError, "empty list", p9.serialise, 'CR', [])
    tc.assertEqual(p9.serialise('AP', ("na:me", "2.3")), ["na\\:me:2.3"])
    tc.assertEqual(p9.serialise('FG', (515, "th]is")), ["515:th\\]is"])
    tc.assertEqual(p9.serialise('XX', "foo\\bar"), ["foo\\\\bar"])

    tc.assertRaises(ValueError, p9.serialise, 'B', (1, 9))

def test_presenter_private_properties(tc):
    p9 = sgf_properties.Presenter(9, "UTF-8")
    tc.assertEqual(p9.serialise('XX', "9"), ["9"])
    tc.assertEqual(p9.interpret('XX', ["9"]), "9")
    p9.set_private_property_type(p9.get_property_type("SZ"))
    tc.assertEqual(p9.serialise('XX', 9), ["9"])
    tc.assertEqual(p9.interpret('XX', ["9"]), 9)
    p9.set_private_property_type(None)
    tc.assertRaisesRegexp(ValueError, "unknown property",
                          p9.serialise, 'XX', "foo\\bar")
    tc.assertRaisesRegexp(ValueError, "unknown property",
                          p9.interpret, 'XX', ["asd"])

