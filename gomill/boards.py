"""Go board representation."""

from gomill_common import *

BLACK = 'b'
WHITE = 'w'
EMPTY = ''


class Group(object):
    """Represent a solidly-connected group.

    Public attributes:
      colour
      points
      is_captured

    Points are coordinate pairs (row, col).

    """

class Region(object):
    """Represent an empty region.

    Public attributes:
      points
      neighbouring_colours

    Points are coordinate pairs (row, col).

    """
    def __init__(self):
        self.points = set()
        self.neighbouring_colours = set()

class Board(object):
    """State of a go board.

    Supports playing stones with captures, and area scoring.

    """
    def __init__(self, side):
        self.side = side
        self.board_coords = [(_row, _col) for _row in range(side)
                             for _col in range(side)]
        self.board = []
        for row in range(side):
            self.board.append([EMPTY] * side)

    def _make_group(self, row, col, colour):
        points = set()
        is_captured = True
        to_handle = set()
        to_handle.add((row, col))
        while to_handle:
            point = to_handle.pop()
            points.add(point)
            r, c = point
            for coords in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
                (r1, c1) = coords
                if not ((0 <= r1 < self.side) and (0 <= c1 < self.side)):
                    continue
                neigh_colour = self.board[r1][c1]
                if neigh_colour == EMPTY:
                    is_captured = False
                elif neigh_colour == colour:
                    if coords not in points:
                        to_handle.add(coords)
        group = Group()
        group.colour = colour
        group.points = points
        group.is_captured = is_captured
        return group

    def _make_empty_region(self, row, col):
        points = set()
        neighbouring_colours = set()
        to_handle = set()
        to_handle.add((row, col))
        while to_handle:
            point = to_handle.pop()
            points.add(point)
            r, c = point
            for coords in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
                (r1, c1) = coords
                if not ((0 <= r1 < self.side) and (0 <= c1 < self.side)):
                    continue
                neigh_colour = self.board[r1][c1]
                if neigh_colour == EMPTY:
                    if coords not in points:
                        to_handle.add(coords)
                else:
                    neighbouring_colours.add(neigh_colour)
        region = Region()
        region.points = points
        region.neighbouring_colours = neighbouring_colours
        return region

    def _find_captured_groups(self):
        """Find solidly-connected groups with 0 liberties.

        Returns a list of Groups.

        """
        captured = []
        handled = set()
        for (row, col) in self.board_coords:
            colour = self.board[row][col]
            if colour == EMPTY:
                continue
            coords = (row, col)
            if coords in handled:
                continue
            group = self._make_group(row, col, colour)
            if group.is_captured:
                captured.append(group)
            handled.update(group.points)
        return captured

    def get(self, row, col):
        """Return the state of the specified point.

        Returns a colour, or '' for an empty point.

        """
        return self.board[row][col]

    def play(self, row, col, colour):
        """Play a move on the board.

        Raises ValueError if the specified point isn't empty.

        Performs any necessary captures. Allows self-captures. Doesn't enforce
        any ko rule.

        Returns the point forbidden by simple ko, or None

        """
        if self.board[row][col] != EMPTY:
            raise ValueError
        self.board[row][col] = colour
        captured = self._find_captured_groups()
        simple_ko_point = None
        if captured:
            if len(captured) == 1 and captured[0].colour == colour:
                to_capture = captured
            else:
                to_capture = [group for group in captured
                              if group.colour == opponent_of(colour)]
                if (len(to_capture) == 1 and len(to_capture[0].points) == 1):
                    self_capture = [group for group in captured
                                    if group.colour == colour]
                    if (len(self_capture) == 1 and
                        len(self_capture[0].points) == 1):
                        simple_ko_point = iter(to_capture[0].points).next()
            for group in to_capture:
                for r, c in group.points:
                    self.board[r][c] = EMPTY
        return simple_ko_point

    def area_score(self):
        """Calculate the area score of a position.

        Assumes all stones are alive.

        Returns black score minus white score.

        Doesn't take komi into account.

        """
        scores = {BLACK : 0, WHITE : 0}
        captured = []
        handled = set()
        for (row, col) in self.board_coords:
            colour = self.board[row][col]
            if colour != EMPTY:
                scores[colour] += 1
                continue
            coords = (row, col)
            if coords in handled:
                continue
            region = self._make_empty_region(row, col)
            region_size = len(region.points)
            for colour in (BLACK, WHITE):
                if colour in region.neighbouring_colours:
                    scores[colour] += region_size
            handled.update(region.points)
        return scores[BLACK] - scores[WHITE]

