"""Common utility functions for gomill.

This module is designed to be used with 'from gomill_common import *'.

"""

__all__ = ["opponent_of", "format_vertex", "format_vertex_list",
           "coords_from_vertex", "sanitise_utf8"]

_opponents = {"b":"w", "w":"b"}
def opponent_of(colour):
    """Return the opponent colour.

    colour -- 'b' or 'w'

    Returns 'b' or 'w'.

    """
    try:
        return _opponents[colour]
    except KeyError:
        raise ValueError

column_letters = "ABCDEFGHJKLMNOPQRSTUVWXZ"

def format_vertex(coords):
    """Return coordinates as a string like 'A1', or 'pass'.

    coords -- pair (row, col), or None for a pass

    The result is suitable for use directly in GTP responses.

    """
    if coords is None:
        return "pass"
    row, col = coords
    return column_letters[col] + str(row+1)

def format_vertex_list(l):
    """Return a list of coordinates as a string like 'A1,B2'."""
    return ",".join(map(format_vertex, l))

def coords_from_vertex(vertex, board_size):
    """Interpret a string representing a vertex, as specified by GTP.

    Returns a pair of coordinates (row, col) in range(0, board_size)

    Raises ValueError with an appropriate message if 'vertex' isn't a valid GTP
    vertex specification for a board of size 'board_size'.

    """
    if not 0 < board_size <= 25:
        raise ValueError("board_size out of range")
    try:
        s = vertex.lower()
    except Exception:
        raise ValueError("invalid vertex")
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


def sanitise_utf8(s):
    """Ensure an 8-bit string is utf-8.

    s -- 8-bit string (or None)

    Returns the sanitised string. If the string was already valid utf-8, returns
    the same object.

    This replaces bad characters with ascii question marks (I don't want to use
    a unicode replacement character, because if this function is doing anything
    then it's likely that there's a non-unicode setup involved somewhere, so it
    probably wouldn't be helpful).

    """
    if s is None:
        return None
    try:
        u = s.decode("utf-8")
    except UnicodeDecodeError:
        return (s.decode("utf-8", 'replace')
                .replace(u"\ufffd", u"?")
                .encode("utf-8"))
    else:
        return s
