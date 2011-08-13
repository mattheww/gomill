"""Support code for testing gtp_states."""

from gomill import gtp_states
from gomill.common import *

class Player(object):
    """Player (stateful move generator) for testing gtp_states.

    Public attributes:
      last_game_state -- the Game_state from the last genmove-like command

    """

    def __init__(self):
        self.next_move = None
        self.next_comment = None
        self.next_cookie = None
        self.last_game_state = None
        self.resign_next_move = False

    def set_next_move(self, vertex, comment=None, cookie=None):
        """Specify what to return from the next genmove-like command."""
        self.next_move = move_from_vertex(vertex, 19)
        self.next_comment = comment
        self.next_cookie = cookie

    def set_next_move_resign(self):
        self.resign_next_move = True

    def genmove(self, game_state, player):
        """Move generator returns points from the move list.

        game_state -- gtp_states.Game_state
        player     -- 'b' or 'w'

        """
        self.last_game_state = game_state
        # Freeze the move_history as we saw it
        self.last_game_state.move_history = self.last_game_state.move_history[:]

        result = gtp_states.Move_generator_result()
        if self.resign_next_move:
            result.resign = True
        elif self.next_move is not None:
            result.move = self.next_move
        else:
            result.pass_move = True
        if self.next_comment is not None:
            result.comments = self.next_comment
        if self.next_cookie is not None:
            result.cookie = self.next_cookie
        self.next_move = None
        self.next_comment = None
        self.next_cookie = None
        self.resign_next_move = False
        return result

class Testing_gtp_state(gtp_states.Gtp_state):
    """Variant of Gtp_state suitable for use in tests.

    This doesn't read from or write to the filesystem.

    """
    def __init__(self, *args, **kwargs):
        super(Testing_gtp_state, self).__init__(*args, **kwargs)
        self._file_contents = {}

    def _register_file(self, pathname, contents):
        self._file_contents[pathname] = contents

    def _load_file(self, pathname):
        try:
            return self._file_contents[pathname]
        except KeyError:
            raise EnvironmentError("unknown file: %s" % pathname)

    def _save_file(self, pathname, contents):
        if pathname == "force_fail":
            open("/nonexistent_directory/foo.sgf", "w")
        self._file_contents[pathname] = contents

    def _choose_free_handicap_moves(self, number_of_stones):
        """Implementation of place_free_handicap.

        Returns for a given number of stones:
         2 -- A1 A2 A3          (too many stones)
         4 -- A1 A2 A3 pass     (pass isn't permitted)
         5 -- A1 A2 A3 A4 A5    (which is ok)
         6 -- A1 A2 A3 A4 A5 A1 (repeated point)
         8 -- not even the right result type
         otherwise Gtp_state default (which is to use the fixed handicap points)

        """
        if number_of_stones == 2:
            return ((0, 0), (1, 0), (2, 0))
        elif number_of_stones == 4:
            return ((0, 0), (1, 0), (2, 0), None)
        elif number_of_stones == 5:
            return ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))
        elif number_of_stones == 6:
            return ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 0))
        elif number_of_stones == 8:
            return "nonsense"
        else:
            return super(Testing_gtp_state, self).\
                   _choose_free_handicap_moves(number_of_stones)
