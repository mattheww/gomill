import random
import sys

from gomill import gtp_engine
from gomill import gtp_boards

def handle_name(args):
    return "Gomill-dummy"

def handle_version(args):
    return ""

def handle_help(args):
    return ("This is a GTP interface.\n"
            "Use list_commands to see the commands available.\n"
            "See http://www.lysator.liu.se/~gunnar/gtp/ for information.\n")

def kiai_dummy_engine(gtp_board):
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands({
        'help'    : handle_help,
        'name'    : handle_name,
        'version' : handle_version,
        })
    engine.add_commands(gtp_board.get_handlers())
    return engine

def dummy_move_generator(game_state, colour):
    """Move generator that chooses a random empty point.

    This may return a self-capture move.

    """
    board = game_state.board
    empties = []
    for row, col in board.board_coords:
        if board.get(row, col) == '':
            empties.append((row, col))
    result = gtp_boards.Move_generator_result()
    result.move = random.choice(empties)
    return result

def test():
    gtp_board = gtp_boards.Gtp_board(dummy_move_generator, [13])
    engine = kiai_dummy_engine(gtp_board)
    try:
        gtp_engine.run_interactive_gtp_session(engine)
    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == "__main__":
    test()
