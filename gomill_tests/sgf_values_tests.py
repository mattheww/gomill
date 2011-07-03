"""Tests for sgf_values.py."""

from textwrap import dedent

from gomill_tests import gomill_test_support

from gomill import sgf_values

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_interpret_point(tc):
    interpret_point = sgf_values.interpret_point
    tc.assertEqual(interpret_point("aa", 19), (18, 0))
    tc.assertEqual(interpret_point("ai", 19), (10, 0))
    tc.assertEqual(interpret_point("ba",  9), (8, 1))
    tc.assertEqual(interpret_point("tt", 21), (1, 19))
    tc.assertIs(interpret_point("tt", 19), None)
    tc.assertIs(interpret_point("", 19), None)
    tc.assertIs(interpret_point("", 21), None)
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

def test_interpret_point_list(tc):
    ipl = sgf_values.interpret_point_list
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

    ipl = sgf_values.interpret_point_list
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
