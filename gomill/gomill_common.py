"""Common utility functions for gomill.

This module is designed to be used with 'from gomill_common import *'.

"""

__all__ = ["opponent_of", "column_letters", "coords_from_vertex", "gtp_boolean"]

_opponents = {"b":"w", "w":"b"}
def opponent_of(colour):
    """Return the opponent colour.

    colour -- 'b' or 'w'

    Returns 'b' or 'w'.

    """
    try:
        return _opponents[colour]
    except KeyError:
        return ValueError

column_letters = "ABCDEFGHJKLMNOPQRSTUVWXZ"

def coords_from_vertex(vertex, board_size):
    """Interpret a string representing a vertex, as specified by GTP.

    Returns a pair of coordinates (row, col) in range(0, board_size)

    Raises ValueError with an appropriate message if 'arg' isn't a valid GTP
    vertex specification for a board of size 'board_size'.

    """
    assert 0 < board_size <= 25
    s = vertex.lower()
    if s == "pass":
        return None
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        if col_c > "i":
            col = ord(col_c) - ord("b")
        else:
            col = ord(col_c) - ord("a")
        row = int(s[1:]) - 1
        if row < 0:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("invalid vertex: '%s'" % s)
    if not (col < board_size and row < board_size):
        raise ValueError("vertex is off board: '%s'" % s)
    return row, col

def gtp_boolean(s):
    """Interpret a string representing a boolean, as specified by GTP.

    Returns a Python bool.

    Raises ValueError with an appropriate message if 's' isn't a valid GTP
    boolean specification.

    """
    try:
        return {'true': True, 'false': False}[s]
    except KeyError:
        raise ValueError

