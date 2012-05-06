"""Tests for boards.py and ascii_boards.py

We test these together because it's convenient for later boards tests to use
ascii_boards facilities.

"""

from __future__ import with_statement

from gomill.common import format_vertex, move_from_vertex
from gomill import ascii_boards
from gomill import boards

from gomill_tests import gomill_test_support
from gomill_tests import board_test_data

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))
    for t in board_test_data.play_tests:
        suite.addTest(Play_test_TestCase(*t))
    for t in board_test_data.score_tests:
        suite.addTest(Score_test_TestCase(*t))
    for t in board_test_data.setup_tests:
        suite.addTest(Setup_test_TestCase(*t))

def test_attributes(tc):
    b = boards.Board(5)
    tc.assertEqual(b.side, 5)
    tc.assertEqual(
        b.board_points,
        [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
         (1, 0), (1, 1), (1, 2), (1, 3), (1, 4),
         (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
         (3, 0), (3, 1), (3, 2), (3, 3), (3, 4),
         (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)])

def test_basics(tc):
    b = boards.Board(9)

    tc.assertTrue(b.is_empty())
    tc.assertItemsEqual(b.list_occupied_points(), [])

    tc.assertEqual(b.get(2, 3), None)
    b.play(2, 3, 'b')
    tc.assertEqual(b.get(2, 3), 'b')
    tc.assertFalse(b.is_empty())
    b.play(3, 4, 'w')

    with tc.assertRaises(ValueError):
        b.play(3, 4, 'w')

    tc.assertItemsEqual(b.list_occupied_points(),
                        [('b', (2, 3)), ('w', (3, 4))])


_9x9_expected = """\
9  .  .  .  .  .  .  .  .  .
8  .  .  .  .  .  .  .  .  .
7  .  .  .  .  .  .  .  .  .
6  .  .  .  .  .  .  .  .  .
5  .  .  .  .  .  .  .  .  .
4  .  .  .  .  o  .  .  .  .
3  .  .  .  #  .  .  .  .  .
2  .  .  .  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J\
"""

_13x13_expected = """\
13  .  .  .  .  .  .  .  .  .  .  .  .  .
12  .  .  .  .  .  .  .  .  .  .  .  .  .
11  .  .  .  .  .  .  .  .  .  .  .  .  .
10  .  .  .  .  .  .  .  .  .  .  .  .  .
 9  .  .  .  .  .  .  .  .  .  .  .  .  .
 8  .  .  .  .  .  .  .  .  .  .  .  .  .
 7  .  .  .  .  .  .  .  .  .  .  .  .  .
 6  .  .  .  .  .  .  .  .  .  .  .  .  .
 5  .  .  .  .  .  .  .  .  .  .  .  .  .
 4  .  .  .  .  o  .  .  .  .  .  .  .  .
 3  .  .  .  #  .  .  .  .  .  .  .  .  .
 2  .  .  .  .  .  .  .  .  .  .  .  .  .
 1  .  .  .  .  .  .  .  .  .  .  .  .  .
    A  B  C  D  E  F  G  H  J  K  L  M  N\
"""

def test_render_board_9x9(tc):
    b = boards.Board(9)
    b.play(2, 3, 'b')
    b.play(3, 4, 'w')
    tc.assertDiagramEqual(ascii_boards.render_board(b), _9x9_expected)

def test_render_board_13x13(tc):
    b = boards.Board(13)
    b.play(2, 3, 'b')
    b.play(3, 4, 'w')
    tc.assertDiagramEqual(ascii_boards.render_board(b), _13x13_expected)

def test_interpret_diagram(tc):
    b1 = boards.Board(9)
    b1.play(2, 3, 'b')
    b1.play(3, 4, 'w')
    b2 = ascii_boards.interpret_diagram(_9x9_expected, 9)
    tc.assertEqual(b1, b2)
    b3 = boards.Board(9)
    b4 = ascii_boards.interpret_diagram(_9x9_expected, 9, b3)
    tc.assertIs(b3, b4)
    tc.assertEqual(b1, b3)
    tc.assertRaisesRegexp(ValueError, "board not empty",
                          ascii_boards.interpret_diagram, _9x9_expected, 9, b3)
    b5 = boards.Board(19)
    tc.assertRaisesRegexp(ValueError, "wrong board size, must be 9$",
                          ascii_boards.interpret_diagram, _9x9_expected, 9, b5)

    tc.assertRaises(ValueError, ascii_boards.interpret_diagram, "nonsense", 9)
    b6 = ascii_boards.interpret_diagram(_13x13_expected, 13)
    tc.assertDiagramEqual(ascii_boards.render_board(b6), _13x13_expected)

def test_copy(tc):
    b1 = boards.Board(9)
    b1.play(2, 3, 'b')
    b1.play(3, 4, 'w')
    b2 = b1.copy()
    tc.assertEqual(b1, b2)
    b2.play(5, 5, 'b')
    b2.play(2, 1, 'b')
    tc.assertNotEqual(b1, b2)
    b1.play(5, 5, 'b')
    b1.play(2, 1, 'b')
    tc.assertEqual(b1, b2)

def test_full_board_selfcapture(tc):
    b = boards.Board(9)
    tc.assertTrue(b.is_empty())
    tc.assertItemsEqual(b.list_occupied_points(), [])
    for row in range(9):
        for col in range(9):
            b.play(row, col, 'b')
    tc.assertEqual(b, boards.Board(9))
    tc.assertIs(b.is_empty(), True)


class Play_test_TestCase(gomill_test_support.Gomill_ParameterisedTestCase):
    """Check final position reached by playing a sequence of moves."""
    test_name = "play_test"
    parameter_names = ('moves', 'diagram', 'ko_vertex', 'score')

    def runTest(self):
        b = boards.Board(9)
        ko_point = None
        for move in self.moves:
            colour, vertex = move.split()
            colour = colour.lower()
            row, col = move_from_vertex(vertex, b.side)
            ko_point = b.play(row, col, colour)
        self.assertDiagramEqual(ascii_boards.render_board(b),
                                self.diagram.rstrip())
        if ko_point is None:
            ko_vertex = None
        else:
            ko_vertex = format_vertex(ko_point)
        self.assertEqual(ko_vertex, self.ko_vertex, "wrong ko point")
        self.assertEqual(b.area_score(), self.score, "wrong score")


class Score_test_TestCase(gomill_test_support.Gomill_ParameterisedTestCase):
    """Check score of a diagram."""
    test_name = "score_test"
    parameter_names = ('diagram', 'score')

    def runTest(self):
        b = ascii_boards.interpret_diagram(self.diagram, 9)
        self.assertEqual(b.area_score(), self.score, "wrong score")


class Setup_test_TestCase(gomill_test_support.Gomill_ParameterisedTestCase):
    """Check apply_setup()."""
    test_name = "setup_test"
    parameter_names = ('black_points', 'white_points', 'empty_points',
                       'diagram', 'is_legal')

    def runTest(self):
        def _interpret(moves):
            return [move_from_vertex(v, b.side) for v in moves]

        b = boards.Board(9)
        is_legal = b.apply_setup(_interpret(self.black_points),
                                 _interpret(self.white_points),
                                 _interpret(self.empty_points))
        self.assertDiagramEqual(ascii_boards.render_board(b),
                                self.diagram.rstrip())
        if self.is_legal:
            self.assertTrue(is_legal, "setup should be considered legal")
        else:
            self.assertFalse(is_legal, "setup should be considered illegal")
