import datetime

from gomill import sgf_writer

def make_sgf(size, moves):
    """Return an SGF description of the game.

    Returns an Sgf_game object.

    """
    sgf_game = sgf_writer.Sgf_game(size)
    sgf_game.set('komi', 7.5)
    sgf_game.set('application', "test-sgf-writer")
    sgf_game.add_date(datetime.date(2009, 6, 6))
    sgf_game.set('black-player', "Black engine")
    sgf_game.set('white-player', "White engine")
    for colour, move, comment in moves:
        sgf_game.add_move(colour, move, comment)
    sgf_game.set('result', "W+R")
    sgf_game.add_final_comment("Final comment")
    return sgf_game

test_moves = [
    ('b', (2, 2), None),
    ('w', (3, 3), "cmt"),
    ('b', None, None),
    ]

expected_sgf = """\
(;AP[test-sgf-writer]DT[2009-06-06]FF[4]GM[1]KM[7.5]PB[Black engine]
PW[White engine]RE[W+R]SZ[9];B[cg];W[df]C[cmt];B[tt]C[Final comment])
"""

def main():
    sgf = make_sgf(25, test_moves)
    print sgf.as_string()
    assert sgf.as_string() == expected_sgf

if __name__ == "__main__":
    main()
