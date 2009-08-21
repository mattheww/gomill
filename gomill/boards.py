"""Go board capable of area scoring."""

BLACK = 'b'
WHITE = 'w'
EMPTY = ''

opponents = {"b":"w", "w":"b"}


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

class Referee_board(object):
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

    def play(self, row, col, colour):
        """Play a move on the board.

        Raises ValueError if the specified point isn't empty.

        Performs any necessary captures. Allows self-captures. Doesn't enforce
        any ko rule.

        """
        if self.board[row][col] != EMPTY:
            raise ValueError
        self.board[row][col] = colour
        captured = self._find_captured_groups()
        if captured:
            if len(captured) == 1 and captured[0].colour == colour:
                to_capture = captured
            else:
                to_capture = [group for group in captured
                              if group.colour == opponents[colour]]
            for group in to_capture:
                for r, c in group.points:
                    self.board[r][c] = EMPTY

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

# FIXME: Clean up, and share code

class Board_base(object):
    """Common implementation for Board classes."""
    def get(self, row, col):
        raise NotImplementedError

class xGroup(object):
    """Represent a solidly-connected group.

    Points are coordinate pairs (row, col).

    Each group can have a 'head', which is one designated point in the group.

    """
    def __init__(self, colour):
        self.colour = colour
        self.points = set()
        self.head = None
        self.plibs = None

    def set_head(self, row, col):
        coords = (row, col)
        if self.head is not None and coords != self.head:
            raise ValueError("inconsistent heads")
        if coords not in self.points:
            raise ValueError("head not in group")
        self.head = coords

class Play_board(Board_base):
    """Represent a go board, and calculate supplementary data like asmgo's.

    This calculates groups and plibs 'from scratch', in contrast to asmgo's
    incremental calculations, so that it can be used as an independent check.

    """
    def __init__(self, side):
        self.side = side
        self.board_coords = [(_row, _col) for _row in range(side)
                             for _col in range(side)]
        self.board = []
        for row in range(side):
            self.board.append([EMPTY] * self.side)
        self.groups = []
        self.groups_by_point = {}
        self.is_consistent = True

    def copy(self):
        """Return an independent copy of this board."""
        b = Board()
        b.board = [self.board[i][:] for i in range(self.side)]
        b.groups = []
        b.groups_by_point = {}
        b.is_consistent = False
        return b

    def get(self, row, col):
        return self.board[row][col]

    def set(self, row, col, colour):
        self.board[row][col] = colour
        self.is_consistent = False

    def group_at(self, row, col):
        assert self.is_consistent
        return self.groups_by_point[row, col]

    def is_empty(self):
        assert self.is_consistent
        return not(self.groups)

    def make_group(self, row, col, colour):
        group = xGroup(colour)
        plibs = 0
        points = group.points
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
                    plibs += 1
                elif neigh_colour == colour:
                    if coords not in points:
                        to_handle.add(coords)
        group.plibs = plibs
        return group

    def recalc(self):
        """Recalculate the per-group data from current board state.

        Returns a list of all Groups which have 0 liberties.

        """
        self.groups = []
        self.groups_by_point = {}
        captured = []
        handled = set()
        for (row, col) in self.board_coords:
            colour = self.board[row][col]
            if colour == EMPTY:
                continue
            coords = (row, col)
            if coords in handled:
                continue
            group = self.make_group(row, col, colour)
            if group.plibs == 0:
                captured.append(group)
            handled.update(group.points)
            self.groups.append(group)
            for coords in group.points:
                self.groups_by_point[coords] = group
        self.is_consistent = True
        return captured

    def play(self, row, col, colour):
        """Play a move on the board.

        Raises ValueError if the specified point isn't empty.

        Performs any necessary captures. Allows self-captures.

        Returns the point forbidden by simple ko, or None

        (With the current implementation, a point reported as forbidden by ko
        might in fact be a single-stone selfcapture)

        """
        # Ko detection is just 'if a single stone captures a single stone'.
        if self.get(row, col) != EMPTY:
            raise ValueError
        self.set(row, col, colour)
        captured = self.recalc()
        simple_ko_point = None
        if captured:
            if len(captured) == 1 and captured[0].colour == colour:
                to_capture = captured
            else:
                to_capture = [group for group in captured
                              if group.colour == opponents[colour]]
                if (len(to_capture) == 1 and
                    len(to_capture[0].points) == 1 and
                    len(self.groups_by_point[row, col].points) == 1):
                    simple_ko_point = iter(to_capture[0].points).next()
            for group in to_capture:
                for r, c in group.points:
                    self.set(r, c, EMPTY)
            captured2 = self.recalc()
            assert captured2 == []
        return simple_ko_point

    def is_self_capture(self, row, col, colour):
        """Check whether a proposed move would be a self-capture.

        Leaves the board inconsistent.

        """
        if self.get(row, col) != EMPTY:
            raise ValueError
        self.set(row, col, colour)
        captured = self.recalc()
        is_self_capture = (len(captured) == 1 and captured[0].colour == colour)
        self.set(row, col, EMPTY)
        return is_self_capture

