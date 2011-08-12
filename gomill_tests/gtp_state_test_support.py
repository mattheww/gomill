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
        self.last_game_state = None
        self.resign_next_move = False

    def set_next_move(self, vertex, comment=None):
        """Specify what to return from the next genmove-like command."""
        self.next_move = move_from_vertex(vertex, 19)
        self.next_comment = comment

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
        self.next_move = None
        self.next_comment = None
        self.resign_next_move = False
        return result

