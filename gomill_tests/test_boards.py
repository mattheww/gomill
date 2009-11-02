from gomill import boards

BLACK = 'b'
WHITE = 'w'
EMPTY = None

play_tests = [

('multiple', [
(WHITE, 3, 3),
(BLACK, 2, 3),
(WHITE, 4, 2),
(BLACK, 3, 2),
(WHITE, 4, 4),
(BLACK, 3, 4),
(BLACK, 4, 1),
(BLACK, 4, 5),
(BLACK, 5, 2),
(BLACK, 5, 4),
(BLACK, 6, 3),
(WHITE, 5, 3),

(BLACK, 4, 3),
], """\
9  .  .  .  .  .  .  .  .  .
8  .  .  .  .  .  .  .  .  .
7  .  .  .  #  .  .  .  .  .
6  .  .  #  .  #  .  .  .  .
5  .  #  .  #  .  #  .  .  .
4  .  .  #  .  #  .  .  .  .
3  .  .  .  #  .  .  .  .  .
2  .  .  .  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J
""", 81),

]


score_positions = [

("""\
9  .  .  o  .  .  o  #  .  #
8  .  o  o  o  o  o  #  .  #
7  .  o  .  o  o  #  #  #  o
6  o  .  o  #  o  #  o  o  o
5  o  o  #  #  #  #  #  o  o
4  .  o  o  #  .  o  #  o  .
3  o  #  #  #  o  o  o  o  o
2  .  o  o  #  #  #  o  o  .
1  o  .  o  #  .  #  o  o  o
   A  B  C  D  E  F  G  H  J
""", -26)

]


def debug_show_board(board):
    for row in range(board.side):
        for col in range(board.side):
            print (board.board[row][col] or " "),
        print

def play_diagram(board, diagram):
    """Set up the position from a diagram.

    board   -- Board_base implementing play()
    diagram -- board representation as from Board_base.format()

    """
    lines = diagram.split("\n")
    colours = {'#' : BLACK, 'o' : WHITE, '.' : EMPTY}
    if board.side > 9:
        extra_offset = 1
    else:
        extra_offset = 0
    result = []
    for (row, col) in board.board_coords:
        colour = colours[lines[board.side-row-1][3*(col+1)+extra_offset]]
        if colour != EMPTY:
            board.play(row, col, colour)

def main():
    b = boards.Board(9)
    assert b.is_empty()
    assert b.area_score() == 0
    b.play(2, 3, 'b')
    assert not b.is_empty()
    assert b.area_score() == 81
    b.play(3, 4, 'w')
    assert b.area_score() == 0

    for code, moves, diagram, score in play_tests:
        b = boards.Board(9)
        for colour, row, col in moves:
            b.play(row, col, colour)
        assert b.area_score() == score

    for diagram, score in score_positions:
        b = boards.Board(9)
        play_diagram(b, diagram)
        assert b.area_score() == score

if __name__ == "__main__":
    main()
