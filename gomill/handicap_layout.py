"""Standard layout of fixed handicap stones.

This follows the rules from the GTP spec.

"""

handicap_pattern = [
    ['C3', 'G7'],
    ['C3', 'G7', 'C7'],
    ['C3', 'G7', 'C7', 'G3'],
    ['C3', 'G7', 'C7', 'G3', 'E5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E5'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E3', 'E7'],
    ['C3', 'G7', 'C7', 'G3', 'C5', 'G5', 'E3', 'E7', 'E5'],
]

def handicap_points(number_of_stones, board_size):
    """Return the handicap points for a given number of stones and board size.

    Returns a list of coords, length 'number'.

    Raises ValueError if there isn't a placement pattern for the specified
    number of handicap stones and board size.

    """
    if not 7 <= board_size <= 25:
        raise ValueError
    if number_of_stones <= 1:
        raise ValueError
    if board_size % 2 == 0 or board_size == 7:
        if number_of_stones > 4:
            raise ValueError
    else:
        if number_of_stones > 9:
            raise ValueError
    if board_size < 13:
        altitude = 2
    else:
        altitude = 3
    low = altitude
    mid = (board_size - 1) / 2
    high = board_size - altitude - 1
    row_map = {'3' : low, '5' : mid, '7' : high}
    col_map = {'C' : low, 'E' : mid, 'G' : high}
    return [(row_map[s[1]], col_map[s[0]])
            for s in handicap_pattern[number_of_stones-2]]
