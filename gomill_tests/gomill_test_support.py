"""Gomill-specific test support code."""

from gomill.gomill_common import *
from gomill import ascii_boards

def check_boards_equal(b1, b2):
    """Check that two boards are equal.

    Does nothing if they are equal; raises ValueError with a message if they
    are not.

    """
    if b1.side != b2.side:
        raise ValueError("size is different: %s, %s" % (b1.side, b2.side))
    differences = []
    for row, col in b1.board_coords:
        if b1.get(row, col) != b2.get(row, col):
            differences.append((row, col))
    if not differences:
        return
    msg = "boards differ at %s" % " ".join(map(format_vertex, differences))
    try:
        msg += "\n%s\n%s" % (
            ascii_boards.render_board(b1), ascii_boards.render_board(b2))
    except Exception:
        pass
    raise ValueError(msg)

