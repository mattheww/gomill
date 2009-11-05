"""Stateful GTP engine."""

import math

from gomill_common import *
from gomill import ascii_boards
from gomill import boards
from gomill import gtp_engine
from gomill import handicap_layout
from gomill import sgf_reader
from gomill.gtp_engine import GtpError


class Game_state(object):
    """Data passed to a move generator.

    Public attributes:
      size                      -- int
      board                     -- boards.Board
      komi                      -- float
      history_base              -- boards.Board
      move_history              -- list of tuples (colour, point)
      ko_point                  -- point forbidden by the simple ko rule
      for_regression            -- bool
      time_remaining            -- int (seconds), or None
      canadian_stones_remaining -- int or None
    where point is (row, col) or None

    'board' represents the current board position.

    history_base represents a (possibly) earlier board position; move_history
    lists the moves leading to 'board' from that position. This is provided so
    that engines can check for superko violations. A pass is represented in
    move_history by point None.

    Normally, history_base will be an empty board, or else be the position after
    the placement of handicap stones; but if the loadsgf command has been used
    it may be the position given by setup stones in the SGF file.

    ko_point is provided for engines which don't want to deduce it from the move
    history.

    for_regression is true if the command was 'reg_genmove'; engines which care
    should use a fixed seed in this case.

    time_remaining None means time information isn't available.
    canadian_stones_remaining None means we're in main time.

    """

class Move_generator_result(object):
    """Return value from a move generator.

    Public attributes:
      resign    -- bool
      pass_move -- bool
      move      -- (row, col), or None
      claim     -- bool (for gomill-genmove_claim)

    Exactly one of the first three attributes should be set to a nondefault
    value.

    If claim is true, either 'move' or 'pass_move' must still be set.

    """
    def __init__(self):
        self.resign = False
        self.pass_move = False
        self.move = None
        self.claim = False


class Gtp_board(object):
    """Implement a stateful GTP board for use with a stateless engine.

    Sample use:
      gtp_board = Gtp_board(...)
      engine = Gtp_engine_protocol()
      engine.add_commands(gtp_board.get_handlers())

    A Gtp_board maintains the following state:
      board configuration
      move history
      komi
      simple ko ban

    Komi is tracked as an integer (treat as +.5 for scoring jigo).


    Instantiate with a _move generator function_ and a list of acceptable board
    sizes (default 19 only).

    The move generator function is called to handle genmove. It is passed
    arguments (game_state, colour to play). It should return a
    Move_generator_result. It must not modify data passed in the game_state.

    If the move generator returns an occupied point, Gtp_board will report a GTP
    error. Gtp_board does not enforce any ko rule. It permits self-captures.

    """

    def __init__(self, move_generator, acceptable_sizes=None):
        self.komi = 0
        self.time_status = {
            'b' : (None, None),
            'w' : (None, None),
            }
        self.move_generator = move_generator
        if acceptable_sizes is None:
            self.acceptable_sizes = set((19,))
            self.board_size = 19
        else:
            self.acceptable_sizes = set(acceptable_sizes)
            self.board_size = min(self.acceptable_sizes)
        self.reset()

    def reset(self):
        self.board = boards.Board(self.board_size)
        self.simple_ko_point = None
        # Player that any simple_ko_point is banned for
        self.simple_ko_player = None
        self.history_base = boards.Board(self.board_size)
        # list of (colour, point-or-None)
        self.move_history = []

    def set_history_base(self, board):
        """Change the history base to a new position.

        Takes ownership of 'board'.

        Clears the move history.

        """
        self.history_base = board
        self.move_history = []

    def reset_to_moves(self, moves):
        """Reset to history base and play the specified moves.

        moves -- list of pairs (colour, coords) (same as move history)

        'moves' becomes the new move history. Takes ownership of 'moves'.

        Raises ValueError if there is an invalid move in the list.

        """
        self.board = self.history_base.copy()
        simple_ko_point = None
        colour = 'b'
        for colour, coords in moves:
            if coords is None:
                # pass
                self.simple_ko_point = None
                continue
            row, col = coords
            # Propagates ValueError if the move is bad
            simple_ko_point = self.board.play(row, col, colour)
        self.simple_ko_point = simple_ko_point
        self.simple_ko_player = opponent_of(colour)
        self.move_history = moves

    def set_komi(self, f):
        max_komi = 625
        try:
            k = int(math.floor(f))
        except OverflowError:
            if f < 0:
                k = -max_komi
            else:
                k = max_komi
        else:
            if k < -max_komi:
                k = -max_komi
            if k > max_komi:
                k = max_komi
        self.komi = k

    def handle_boardsize(self, args):
        try:
            size = gtp_engine.interpret_int(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        if size not in self.acceptable_sizes:
            raise GtpError("unacceptable size")
        self.board_size = size
        self.reset()

    def handle_clear_board(self, args):
        self.reset()

    def handle_komi(self, args):
        try:
            f = gtp_engine.interpret_float(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        self.set_komi(f)

    def handle_fixed_handicap(self, args):
        try:
            number_of_stones = gtp_engine.interpret_int(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        if not self.board.is_empty():
            raise GtpError("board not empty")
        try:
            points = handicap_layout.handicap_points(
                number_of_stones, self.board_size)
        except ValueError:
            raise GtpError("invalid number of stones")
        for row, col in points:
            self.board.play(row, col, 'b')
        self.simple_ko_point = None
        self.set_history_base(self.board.copy())

    def handle_set_free_handicap(self, args):
        if len(args) < 2:
            gtp_engine.report_bad_arguments()
        for vertex_s in args:
            row, col = gtp_engine.interpret_vertex(vertex_s, self.board_size)
            try:
                self.board.play(row, col, 'b')
            except ValueError:
                raise GtpError("engine error: %s is occupied" % vertex)
        self.set_history_base(self.board.copy())
        self.simple_ko_point = None

    def handle_place_free_handicap(self, args):
        try:
            number_of_stones = gtp_engine.interpret_int(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        max_points = self.board_size * self.board_size - 1
        if not 2 <= number_of_stones <= max_points:
            raise GtpError("invalid number of stones")
        if not self.board.is_empty():
            raise GtpError("board not empty")
        if number_of_stones == max_points:
            number_of_stones = max_points - 1
        moves = []
        for i in xrange(number_of_stones):
            game_state = Game_state()
            game_state.size = self.board_size
            game_state.board = self.board
            game_state.history_base = self.board
            game_state.move_history = []
            game_state.komi = self.board_size * number_of_stones // 2
            game_state.ko_point = None
            game_state.time_remaining = None
            game_state.canadian_stones_remaining = None
            game_state.for_regression = False

            generated = self.move_generator(game_state, 'b')
            if generated.resign or generated.pass_move:
                continue
            row, col = generated.move
            try:
                self.board.play(row, col, 'b')
            except ValueError:
                raise GtpError("engine error: tried to play %s" % vertex)
            moves.append(generated.move)
        self.simple_ko_point = None
        self.set_history_base(self.board.copy())
        return " ".join(gtp_engine.format_vertex_from_coords(row, col)
                        for (row, col) in moves)

    def handle_play(self, args):
        try:
            colour_s, vertex_s = args[:2]
        except ValueError:
            gtp_engine.report_bad_arguments()
        colour = gtp_engine.interpret_colour(colour_s)
        coords = gtp_engine.interpret_vertex(vertex_s, self.board_size)
        if coords is None:
            self.simple_ko_point = None
            self.move_history.append((colour, None))
            return
        row, col = coords
        try:
            self.simple_ko_point = self.board.play(row, col, colour)
            self.simple_ko_player = opponent_of(colour)
        except ValueError:
            raise GtpError("illegal move")
        self.move_history.append((colour, coords))

    def handle_showboard(self, args):
        return "\n%s\n" % ascii_boards.render_board(self.board)

    def _handle_genmove(self, args, for_regression=False, allow_claim=False):
        """Common implementation for genmove commands."""
        try:
            colour = gtp_engine.interpret_colour(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        game_state = Game_state()
        game_state.size = self.board_size
        game_state.board = self.board
        game_state.history_base = self.history_base
        game_state.move_history = self.move_history
        game_state.komi = self.komi
        game_state.for_regression = for_regression
        if self.simple_ko_point is not None and self.simple_ko_player == colour:
            game_state.ko_point = self.simple_ko_point
        else:
            game_state.ko_point = None
        game_state.time_remaining, game_state.canadian_stones_remaining = \
            self.time_status[colour]
        generated = self.move_generator(game_state, colour)
        if allow_claim and generated.claim:
            return 'claim'
        if generated.resign:
            return 'resign'
        if generated.pass_move:
            if not for_regression:
                self.move_history.append((colour, None))
            return 'pass'
        row, col = generated.move
        vertex = gtp_engine.format_vertex_from_coords(row, col)
        if not for_regression:
            try:
                self.simple_ko_point = self.board.play(row, col, colour)
                self.simple_ko_player = opponent_of(colour)
            except ValueError:
                raise GtpError("engine error: tried to play %s" % vertex)
            self.move_history.append((colour, generated.move))
        return vertex

    def handle_genmove(self, args):
        return self._handle_genmove(args)

    def handle_genmove_claim(self, args):
        return self._handle_genmove(args, allow_claim=True)

    def handle_reg_genmove(self, args):
        return self._handle_genmove(args, for_regression=True)

    def handle_undo(self, args):
        if not self.move_history:
            raise GtpError("cannot undo")
        try:
            self.reset_to_moves(self.move_history[:-1])
        except ValueError:
            raise GtpError("corrupt history")

    def handle_loadsgf(self, args):
        try:
            pathname = args[0]
        except IndexError:
            gtp_engine.report_bad_arguments()
        if len(args) > 1:
            move_number = gtp_engine.interpret_int(args[1])
        else:
            move_number = None
        try:
            f = open(pathname)
            s = f.read()
            f.close()
        except EnvironmentError:
            raise GtpError("cannot load file")
        try:
            sgf = sgf_reader.read_sgf(s)
        except ValueError:
            raise GtpError("cannot load file")
        new_size = sgf.get_size()
        if new_size not in self.acceptable_sizes:
            raise GtpError("unacceptable size")
        self.board_size = new_size
        try:
            komi = sgf.get_komi()
        except ValueError:
            raise GtpError("bad komi")
        sgf_board, sgf_moves = sgf.get_setup_and_moves()
        if move_number is None:
            new_move_history = sgf_moves
        else:
            # gtp spec says we want the "position before move_number"
            move_number = max(0, move_number-1)
            new_move_history = sgf_moves[:move_number]
        old_history_base = self.history_base
        old_move_history = self.move_history
        try:
            self.set_history_base(sgf_board)
            self.reset_to_moves(new_move_history)
        except ValueError:
            try:
                self.set_history_base(old_history_base)
                self.reset_to_moves(old_move_history)
            except ValueError:
                raise GtpError("bad move in file and corrupt history")
            raise GtpError("bad move in file")
        self.set_komi(komi)

    def handle_time_left(self, args):
        # colour time stones
        try:
            colour = gtp_engine.interpret_colour(args[0])
            time_remaining = gtp_engine.interpret_int(args[1])
            stones_remaining = gtp_engine.interpret_int(args[2])
        except IndexError:
            gtp_engine.report_bad_arguments()
        if stones_remaining == 0:
            stones_remaining = None
        self.time_status[colour] = (time_remaining, stones_remaining)

    def handle_time_settings(self, args):
        # Accept the command, but ignore what it sends for now.
        pass

    def get_handlers(self):
        return {'boardsize'            : self.handle_boardsize,
                'clear_board'          : self.handle_clear_board,
                'komi'                 : self.handle_komi,
                'fixed_handicap'       : self.handle_fixed_handicap,
                'set_free_handicap'    : self.handle_set_free_handicap,
                'place_free_handicap'  : self.handle_place_free_handicap,
                'play'                 : self.handle_play,
                'genmove'              : self.handle_genmove,
                'gomill-genmove_claim' : self.handle_genmove_claim,
                'reg_genmove'          : self.handle_reg_genmove,
                'undo'                 : self.handle_undo,
                'showboard'            : self.handle_showboard,
                'loadsgf'              : self.handle_loadsgf,
                }

    def get_time_handlers(self):
        """Return handlers for time-related commands.

        These are separated out so that engines which don't support time
        handling can avoid advertising time support.

        """
        return {'time_left'           : self.handle_time_left,
                'time_settings'       : self.handle_time_settings,
                }
