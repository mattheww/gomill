"""Standard layout of fixed handicap stones.

This follows the rules from the GTP spec.

"""

handicap_9x9 = [
    ['C3', 'G7'],
    ['C3', 'G7', 'C7'],
    ['C3', 'G7', 'C7', 'G3'],
    ['C3', 'G7', 'C7', 'G3', 'E5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E3', 'E7'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E3', 'E7', 'E5'],
]

from gomill_common import *

def handicap_points(number_of_stones, board_size):
    """Return the handicap points for a given number of stones and board size.

    Returns a list of coords, length 'number'.

    Raises ValueError if there isn't a placement pattern for the specified
    number of handicap stones and board size.

    """
    if board_size != 9:
        raise ValueError
    if number_of_stones <= 1:
        raise ValueError
    try:
        return [coords_from_vertex(s, board_size)
                for s in handicap_9x9[number_of_stones-2]]
    except IndexError:
        raise ValueError
