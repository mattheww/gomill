from __future__ import with_statement

from gomill_tests import gomill_test_support
from gomill_tests import test_framework
from gomill_tests import board_test_data

from gomill import boards

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))
    for code, moves, diagram, score in board_test_data.play_tests:
        suite.addTest(Play_test_TestCase(code, moves, diagram, score))

def test_attributes(tc):
    b = boards.Board(5)
    tc.assertEqual(b.side, 5)
    tc.assertEqual(
        b.board_coords,
        [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
         (1, 0), (1, 1), (1, 2), (1, 3), (1, 4),
         (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
         (3, 0), (3, 1), (3, 2), (3, 3), (3, 4),
         (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)])

def test_basics(tc):
    b = boards.Board(9)

    tc.assertTrue(b.is_empty())
    tc.assertItemsEqual(b.list_occupied_points(), [])

    tc.assertEqual(b.area_score(), 0)
    tc.assertEqual(b.get(2, 3), None)
    b.play(2, 3, 'b')
    tc.assertEqual(b.get(2, 3), 'b')
    tc.assertFalse(b.is_empty())
    tc.assertEqual(b.area_score(), 81)
    b.play(3, 4, 'w')
    tc.assertEqual(b.area_score(), 0)

    with tc.assertRaises(ValueError):
        b.play(3, 4, 'w')

    tc.assertItemsEqual(b.list_occupied_points(),
                        [('b', (2, 3)), ('w', (3, 4))])


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


class Play_test_TestCase(gomill_test_support.Gomill_testcase_mixin,
                         test_framework.FrameworkTestCase):
    """Check final position reached by playing a sequence of moves."""
    def __init__(self, code, moves, diagram, score):
        test_framework.FrameworkTestCase.__init__(self)
        self.code = code
        self.name = (self.__class__.__module__.split(".", 1)[-1] + "." +
                     "play_test:" + code)
        self.moves = moves
        self.diagram = diagram
        self.score = score

    def runTest(self):
        b = boards.Board(9)
        for colour, row, col in self.moves:
            b.play(row, col, colour)
        # FIXME: Check the diagram
        self.assertEqual(b.area_score(), self.score, "wrong score")

    def id(self):
        return self.name

    def shortDescription(self):
        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)

