"""ASCII board representation."""

from gomill.gomill_common import *
from gomill.gomill_common import column_letters

def render_grid(point_formatter, size):
    """Render a board-shaped grid as a list of strings.

    point_formatter -- function (row, col) -> string of length 2.

    Returns a list of strings.

    """
    column_header_string = "  ".join(column_letters[i] for i in range(size))
    result = []
    if size > 9:
        rowstart = "%2d "
        padding = " "
    else:
        rowstart = "%d "
        padding = ""
    for row in range(size-1, -1, -1):
        result.append(rowstart % (row+1) +
                      " ".join(point_formatter(row, col)
                      for col in range(size)))
    result.append(padding + "   " + column_header_string)
    return result

_point_strings = {
    None  : " .",
    'b'   : " #",
    'w'   : " o",
    }

def render_board(board):
    """Render a gomill Board in ascii.

    Returns a string without final newline.

    """
    def format_pt(row, col):
        return _point_strings.get(board.get(row, col), " ?")
    return "\n".join(render_grid(format_pt, board.side))

def play_diagram(board, diagram):
    """Set up the position from a diagram.

    board   -- Board
    diagram -- board representation as from render_board()

    """
    lines = diagram.split("\n")
    colours = {'#' : 'b', 'o' : 'w', '.' : None}
    if board.side > 9:
        extra_offset = 1
    else:
        extra_offset = 0
    try:
        for (row, col) in board.board_coords:
            colour = colours[lines[board.side-row-1][3*(col+1)+extra_offset]]
            if colour is not None:
                board.play(row, col, colour)
    except Exception:
        raise ValueError

