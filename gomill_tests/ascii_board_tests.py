from gomill_tests import test_framework

from gomill import ascii_boards
from gomill import boards

def make_tests(suite):
    suite.addTests(test_framework.make_simple_tests(globals()))

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

def test_9x9(tc):
    b = boards.Board(9)
    b.play(2, 3, 'b')
    b.play(3, 4, 'w')
    tc.assertMultiLineEqual(ascii_boards.render_board(b), _9x9_expected)

def test_13x13(tc):
    b = boards.Board(13)
    b.play(2, 3, 'b')
    b.play(3, 4, 'w')
    tc.assertMultiLineEqual(ascii_boards.render_board(b), _13x13_expected)
