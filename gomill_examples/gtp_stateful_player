#!/usr/bin/env python
"""GTP engine which maintains the board position.

This provides an example of a GTP engine using the gtp_states module.

It plays (and resigns) randomly.

It supports the following GTP commands, mostly provided by gtp_states:

Standard
  boardsize
  clear_board
  fixed_handicap
  genmove
  known_command
  komi
  list_commands
  loadsgf
  name
  place_free_handicap
  play
  protocol_version
  quit
  reg_genmove
  set_free_handicap
  showboard
  undo
  version

Gomill extensions
  gomill-explain_last_move
  gomill-genmove_ex
  gomill-savesgf

Examples
  gomill_resign_p <float>  -- resign in future with the specified probabiltiy

"""

import random
import sys

from gomill import gtp_engine
from gomill import gtp_states



class Player(object):
    """Player for use with gtp_state."""

    def __init__(self):
        self.resign_probability = 0.1

    def genmove(self, game_state, player):
        """Move generator that chooses a random empty point.

        game_state -- gtp_states.Game_state
        player     -- 'b' or 'w'

        This may return a self-capture move.

        """
        board = game_state.board
        empties = []
        for row, col in board.board_points:
            if board.get(row, col) is None:
                empties.append((row, col))
        result = gtp_states.Move_generator_result()
        if random.random() < self.resign_probability:
            result.resign = True
        else:
            result.move = random.choice(empties)
            # Used by gomill-explain_last_move and gomill-savesgf
            result.comments = "chosen at random from %d choices" % len(empties)
        return result

    def handle_name(self, args):
        return "GTP stateful player"

    def handle_version(self, args):
        return ""

    def handle_resign_p(self, args):
        try:
            f = gtp_engine.interpret_float(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        self.resign_probability = f

    def get_handlers(self):
        return {
            'name'            : self.handle_name,
            'version'         : self.handle_version,
            'gomill-resign_p' : self.handle_resign_p,
            }


def make_engine(player):
    """Return a Gtp_engine_protocol which runs the specified player."""
    gtp_state = gtp_states.Gtp_state(
        move_generator=player.genmove,
        acceptable_sizes=(9, 13, 19))
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands(gtp_state.get_handlers())
    engine.add_commands(player.get_handlers())
    return engine

def main():
    try:
        player = Player()
        engine = make_engine(player)
        gtp_engine.run_interactive_gtp_session(engine)
    except (KeyboardInterrupt, gtp_engine.ControllerDisconnected):
        sys.exit(1)

if __name__ == "__main__":
    main()
