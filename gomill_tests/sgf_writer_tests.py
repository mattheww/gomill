"""Tests for sgf_writer.py."""

import datetime

from gomill_tests import gomill_test_support

from gomill import sgf_writer

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

_moves = [
    ('b', (2, 2), None),
    ('w', (3, 3), "cmt"),
    ('b', None, None),
    ]

_setup_stones = [
    ('b', (0, 0)),
    ('b', (1, 1)),
    ('w', (5, 5)),
    ('w', (6, 6)),
    ('b', (4, 4)),
    ]

_expected_sgf = """\
(;AP[test-sgf-writer]CA[utf-8]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PL[B]PW[White engine]RE[W+R]SZ[9]AB[ai][bh][ee]AW[fd][gc];B[cg];W[df]C[cmt]
;B[tt]C[Final comment])
"""

def test_sgf_writer(tc):
    size = 9
    sgf_game = sgf_writer.Sgf_game(size)
    sgf_game.set('komi', 7.5)
    sgf_game.set('application', "test-sgf-writer")
    sgf_game.add_date(datetime.date(2009, 6, 6))
    sgf_game.set('black-player', "Black engine")
    sgf_game.set('white-player', "White engine")
    for colour, move, comment in _moves:
        sgf_game.add_move(colour, move, comment)
    sgf_game.add_setup_stones(_setup_stones)
    sgf_game.set('result', "W+R")
    sgf_game.add_final_comment("Final comment")
    print sgf_game.as_string()
    tc.assertEqual(sgf_game.as_string(), _expected_sgf)
