"""Manage games of Go.

This module implements those details of running a game between two players that
don't directly involve GTP.

"""

from gomill import __version__
from gomill.utils import *
from gomill.common import *
from gomill import boards
from gomill import handicap_layout
from gomill import sgf


class GameStateError(StandardError):
    """Error from Game: wrong state for requested action."""

class Game(object):
    """Track the state of a single Go game.

    Instantiate with:
       board        -- the Board to play on (doesn't have to be empty)
       first_player -- colour (default 'b')

    This enforces a simple ko rule, but no superko rule.
    It accepts self-capture moves.
    Two consecutive passes end the game.


    Public attributes (treat as read-only):
      board            -- the Board
      is_over          -- bool
      move_limit       -- int or None
      move_count       -- int

    Meaningful before the game is over:
      next_player      -- colour
      pass_count       -- int (number of consecutive passes just played)

    Meaningful when the game is over:
      passed_out       -- bool
      seen_resignation -- bool
      seen_claim       -- bool
      seen_forfeit     -- bool
      hit_move_limit   -- bool
      winner           -- colour or None
      forfeit_reason   -- string or None

    When is_over is true, exactly one of the other boolean attributes is true.
    winner is set for seen_resignation, seen_claim, and seen_forfeit, but not
    for passed_out or hit_move_limit.

    move_count is the number of moves already played. Passes are included;
    illegal moves are not.

    """
    def __init__(self, board, first_player="b"):
        self.board = board

        self.move_limit = None
        self.next_player = first_player

        self.move_count = 0
        self.pass_count = 0
        self.simple_ko_point = None

        self.is_over = False
        self.passed_out = False
        self.seen_resignation = False
        self.seen_claim = False
        self.seen_forfeit = False
        self.hit_move_limit = False
        self.winner = None
        self.forfeit_reason = None

        self.game_over_callback = None

    def set_move_limit(self, move_limit):
        """Set or clear the move limit.

        move_limit -- int or None

        If this isn't called, the move limit is None.

        """
        self.move_limit = move_limit

    def set_game_over_callback(self, fn):
        """Specify a function to be called when the game is over.

        fn -- callable (no parameters; result ignored)

        This function is called from the record_xxx() method which causes the
        game to end, immediately before that method returns.

        """
        self.game_over_callback = fn

    def _set_over(self):
        self.is_over = True
        self.next_player = None
        self.simple_ko_point = None
        if self.game_over_callback is not None:
            self.game_over_callback()

    def record_resignation_by(self, loser):
        """Record that a player has resigned.

        loser -- colour

        """
        if self.is_over:
            raise GameStateError("game is already over")
        self.winner = opponent_of(loser)
        self.seen_resignation = True
        self._set_over()

    def record_claim_by(self, winner):
        """Record that a player has won by claiming the win.

        winner -- colour

        """
        if self.is_over:
            raise GameStateError("game is already over")
        self.winner = winner
        self.seen_claim = True
        self._set_over()

    def record_forfeit_by(self, loser, reason):
        """Record that a player has forfeited the game.

        loser  -- colour
        reason -- string: human-readable explanation of the forfeit

        """
        if self.is_over:
            raise GameStateError("game is already over")
        self.winner = opponent_of(loser)
        self.seen_forfeit = True
        self.forfeit_reason = reason
        self._set_over()

    def record_move(self, colour, move):
        """Record that a move or pass has been played.

        colour -- colour to play
        move   -- pair (row, col), or None for a pass

        The game must not already be over.

        The colour is a sanity check; it must match next_player.

        Doesn't return anything. Check 'is_over' afterwards to see if the game
        ended.

        This method causes the game to end if the move is a second consecutive
        pass, if the move is illegal, or the move limit is reached.

        The move limit is considered reached if move_limit is set, move_count
        >= move_limit after the move is played, and the game has not been
        passed out.

        """
        if self.is_over:
            raise GameStateError("game is already over")
        if colour != self.next_player:
            raise GameStateError("%s is next to play" % self.next_player)
        if move is not None:
            self.pass_count = 0
            if move == self.simple_ko_point:
                self.record_forfeit_by(
                    colour, "attempted move to ko-forbidden point %s" %
                    format_vertex(move))
                return
            row, col = move
            try:
                self.simple_ko_point = self.board.play(row, col, colour)
            except ValueError:
                self.record_forfeit_by(
                    colour, "attempted move to occupied point %s" %
                    format_vertex(move))
                return
        else:
            self.pass_count += 1
            self.simple_ko_point = None

        self.move_count += 1
        self.next_player = opponent_of(colour)
        if self.pass_count == 2:
            self.passed_out = True
            self._set_over()
        elif self.move_limit is not None and self.move_count >= self.move_limit:
            self.hit_move_limit = True
            self._set_over()


def adjust_score(raw_score, komi, handicap_compensation='no', handicap=0):
    """Adjust an area score for komi and handicap.

    raw_score             -- int (black points minus white points)
    komi                  -- int or float
    handicap_compensation -- 'no' (default), 'short', or 'full'.
    handicap              -- int (default 0)

    Returns a pair (winner, margin)
      winner -- colour or None
      margin -- non-negative float

    If handicap_compensation is 'full', one point is deducted from Black's
    score for each handicap stone; if handicap_compensation is 'short', one
    point is deducted from Black's score for each handicap stone except the
    first. No adjustment is made if handicap is 0.

    """
    if handicap_compensation not in ("full", "short", "no"):
        raise ValueError("unknown handicap_compensation value: %s" %
                         handicap_compensation)
    score = raw_score - float(komi)
    if handicap:
        if handicap_compensation == "full":
            score -= handicap
        elif handicap_compensation == "short":
            score -= (handicap - 1)
    if score > 0:
        winner = "b"
        margin = score
    elif score < 0:
        winner = "w"
        margin = -score
    else:
        winner = None
        margin = 0
    return winner, margin

class Game_score(object):
    """Scoring details from a counted game.

    Public attributes:
      winner -- colour or None
      margin -- non-negative int or float, or None

    Instantiate with winner and margin.

    If winner is None, margin must be 0 or None; otherwise margin must be
    nonzero or None.

    """
    def __init__(self, winner, margin):
        if winner is None:
            if margin is not None and margin != 0:
                raise ValueError("no winner, but nonzero margin")
        else:
            if margin == 0:
                raise ValueError("winner is set but margin is zero")
        if margin is not None and margin < 0:
            raise ValueError("negative margin")
        self.winner = winner
        self.margin = margin

    def get_detail(self):
        """Return additional detail about the score.

        Returns a string or None.

        This is for information that isn't conveyed by winner and margin; it
        returns None if there's nothing interesting to say.

        """
        if self.margin is None:
            if self.winner is None:
                return "no score reported"
            else:
                return "unknown margin"
        else:
            return None

    @classmethod
    def from_position(cls, board, komi, handicap_compensation='no', handicap=0):
        """Instantiate based on a board's area score.

        board                 -- boards.Board
        komi                  -- int or float
        handicap_compensation -- 'no' (default), 'short', or 'full'.
        handicap              -- int (default 0)

        Assumes all stones are alive.

        See adjust_score() for details of handicap compensation.

        """
        winner, margin = adjust_score(
            board.area_score(), komi, handicap_compensation, handicap)
        return cls(winner, margin)


class Result(object):
    """Description of a game result.

    Don't instantiate directly; use one of the from_... classmethods.

    Public attributes (treat as read-only):
      winning_colour -- 'b', 'w', or None
      losing_colour  -- 'b', 'w', or None
      is_jigo        -- bool
      is_forfeit     -- bool
      is_unknown     -- bool
      sgf_result     -- string describing the game's result (for sgf RE)
      detail         -- additional information (string or None)

    Winning/losing colour are None for a jigo, unknown result, or void game.

    """
    def __init__(self):
        self.is_jigo = False
        self.is_forfeit = False
        self.detail = None

    def _set_winning_colour(self, colour):
        self.winning_colour = colour
        if colour is None:
            self.sgf_result = "?"
        else:
            self.sgf_result = "%s+" % colour.upper()

    def _set_jigo(self):
        self.sgf_result = "0"
        self.is_jigo = True

    @property
    def losing_colour(self):
        if self.winning_colour is None:
            return None
        return opponent_of(self.winning_colour)

    @property
    def is_unknown(self):
        return (self.winning_colour is None) and (not self.is_jigo)

    @classmethod
    def from_score(cls, winner, margin, detail=None):
        """Instantiate given winner and margin.

        winner -- colour or None
        margin -- non-negative int or float, or None
        detail -- string or None

        Raises ValueError for nonsensical combinations (positive margin without
        winner, or winner with zero margin).

        winner non-None with margin None is allowed.

        """
        result = cls()
        result._set_winning_colour(winner)
        if margin is not None and margin < 0:
            raise ValueError("negative margin")
        if winner is None:
            if margin == 0:
                result._set_jigo()
            elif margin is not None:
                raise ValueError("positive margin without winner")
        elif margin is not None:
            if margin == 0:
                raise ValueError("winner with zero margin")
            result.sgf_result += format_float(margin)
        # Otherwise (winner without margin), leave SGF result in form 'B+'.
        # (Maybe players disagreed about the margin, or GTP players returned
        # something like 'B+?'.)
        result.detail = detail
        return result

    @classmethod
    def from_game_score(cls, game_score):
        """Instantiate based on a Game_score.

        game_score -- Game_score

        """
        return cls.from_score(game_score.winner, game_score.margin,
                              game_score.get_detail())

    @classmethod
    def from_unscored_game(cls, game):
        """Instantiate based on a non-passed-out Game.

        game -- Game

        """
        if not game.is_over:
            raise ValueError("game is not over")
        if game.passed_out:
            raise ValueError("game is passed out")
        result = cls()
        result._set_winning_colour(game.winner)
        if game.hit_move_limit:
            result.sgf_result = "Void"
            result.detail = "hit move limit"
        elif game.seen_resignation:
            result.sgf_result += "R"
        elif game.seen_claim:
            # Leave SGF result in form 'B+'
            result.detail = "claim"
        elif game.seen_forfeit:
            result.sgf_result += "F"
            result.is_forfeit = True
            result.detail = game.forfeit_reason
        else:
            raise AssertionError
        return result


class Diagnostics(object):
    """Message text received from a player."""
    def __init__(self, colour, message):
        self.colour = colour
        self.message = message

    def __str__(self):
        return "%s: %s" % (self.colour, self.message)


class Backend(object):
    """Set of operations required to play a Go game.

    This is the abstract interface required by Game_runner.

    The Backend's job is to interface with the two players
    (principally, asking for a move, and notifying of the opponent's
    move).

    All operations may raise exceptions. They will be propagated out of
    Game_runner (which documents which of its methods call which backend
    operations).

    In principle these methods are independent of GTP. But I've made no attempt
    to generalise them beyond what's appropriate for managing a pair of GTP
    engines.

    """
    def start_new_game(self, board_size, komi):
        """Perform any necessary initialisation.

        board_size -- int
        komi       -- float

        """
        raise NotImplementedError

    def end_game(self):
        """Note that the game is over.

        This is called as soon as it's known that no more moves will be
        played.

        """
        raise NotImplementedError

    def get_free_handicap(self, handicap):
        """Tell Black to choose free handicap stones, and return them.

        handicap -- int, in the range permitted by the GTP specification

        Returns a list of pairs (row, col)

        """
        raise NotImplementedError

    def notify_free_handicap(self, points):
        """Inform White of free handicap stones.

        points -- list of pairs (row, col)

        """
        raise NotImplementedError

    def notify_fixed_handicap(self, colour, handicap, points):
        """Inform one player of a fixed handicap.

        colour   -- 'b' or 'w'
        handicap -- int
        points   -- list of pairs (row, col)

        'points' will always be the standard GTP points for the number
        of stones and board size (see handicap_layout.py).

        """
        raise NotImplementedError

    def get_move(self, colour):
        """Ask a player for its move.

        colour -- player to ask

        Returns a pair (action, detail)

        'action' is a string:
          "move"    -- player plays or passes; 'detail' is (row, col) or None
          "forfeit" -- player forfeits; 'detail' is a string explanation
          "resign"  -- player resigns; 'detail' is None
          "claim"   -- player claims the win; 'detail' is None

        """
        raise NotImplementedError

    def notify_move(self, colour, move):
        """Inform a player of its opponent's move.

        colour -- player to inform
        move   -- (row, col), or None for a pass

        Returns a pair (status, msg)

        'status' is a string:
          "accept" -- move was accepted; msg is None
          "reject" -- move was rejected as illegal; msg is descriptive text
          "error"  -- move was rejected with an error; msg is error message

        This may be called after end_game() (in which case it doesn't matter
        what status you return).

        """
        raise NotImplementedError

    def score_game(self, board):
        """Score a passed-out game.

        board -- boards.Board

        Returns a Game_score

        This is called after end_game().

        """
        raise NotImplementedError

    def get_last_move_comment(self, colour):
        """Retrieve any comment a player has about its most recent move.

        colour -- player to ask

        Returns a nonempty utf-8 string or None.

        This may be called after end_game().

        There is a default implementation, which always returns None.

        """
        return None


class GameRunnerStateError(StandardError):
    """Error from Game_runner: wrong state for requested action."""

class Game_runner(object):
    """Run a single Go game, with the players controlled by a Backend.

    Instantiate with:
      backend    -- the Backend
      board_size -- int
      komi       -- int or float (default 0)
      move_limit -- int or None  (default None)

    Order of operations:
      runner = Game_runner(...)
      runner.set_move_callback(...) [optional]
      runner.set_result_class(...) [optional]
      runner.prepare()
      runner.set_handicap(...) [optional]
      runner.run()
      runner.make_sgf()

    Public attributes, useful after run() has been called:
      result -- Result, or None

    Game_runner enforces a simple ko rule, but no superko rule. It accepts
    self-capture moves. Two consecutive passes end the game and trigger
    scoring.

    If move_limit is not None, the game ends (with result 'Void') when that
    number of moves (including passes) has been played.

    If a player rejects its opponent's move as illegal, we assume it is correct
    and the opponent forfeits the game.

    """

    def __init__(self, backend, board_size, komi=0, move_limit=None):
        self.backend = backend
        self.board_size = board_size
        self.komi = float(komi)
        self.move_limit = move_limit
        self.after_move_callback = None
        self.result_class = Result
        self.additional_sgf_props = []
        self.handicap_stones = None
        self.moves = []
        self.final_diagnostics = None
        self.game_score = None
        self.result = None
        self._state = 0

    def set_move_callback(self, fn):
        """Specify a callback function to be called after every move.

        The function is called after each move is played, including passes.

        It is not called after moves which triggered a forfeit. It isn't called
        for resignations or claims.

        It must accept arbitrary keyword arguments.

        At least the following keyword arguments will be passed:
          colour -- 'b' or 'w'
          move   -- pair (row, col), or None for a pass
          board  -- boards.Board

        Treat the board parameter as read-only.

        Exceptions raised from the callback will be propagated unchanged out of
        run().

        """
        self.after_move_callback = fn

    def set_result_class(self, cls):
        """Specify a Result subclass to use.

        If this is called, run() will use this subclass when it
        instantiates the object for the result attribute.

        """
        self.result_class = cls

    def prepare(self):
        """Perform any initialisation needed by the backend.

        Propagates any exceptions from the backend start_new_game() method.

        """
        if self._state != 0:
            raise GameRunnerStateError
        self.backend.start_new_game(self.board_size, self.komi)
        self._state = 1

    def set_handicap(self, handicap, is_free):
        """Arrange for the game to be played at a handicap.

        handicap -- int (number of stones)
        is_free  -- bool

        Raises ValueError if the number of stones isn't valid (see GTP spec).

        Propagates any exceptions from the handicap-related backend methods:
          get_free_handicap()
          notify_free_handicap()
          notify_fixed_handicap()

        """
        if self._state != 1:
            raise GameRunnerStateError
        if is_free:
            max_points = handicap_layout.max_free_handicap_for_board_size(
                self.board_size)
            if not 2 <= handicap <= max_points:
                raise ValueError
            self._state = 2
            points = self.backend.get_free_handicap(handicap)
            self.backend.notify_free_handicap(points)
        else:
            # May propagate ValueError
            points = handicap_layout.handicap_points(handicap, self.board_size)
            self._state = 2
            for colour in "b", "w":
                self.backend.notify_fixed_handicap(colour, handicap, points)
        self.additional_sgf_props.append(('HA', handicap))
        self.handicap_stones = points

    def _set_final_diagnostics(self, colour, comment):
        if comment is not None:
            self.final_diagnostics = Diagnostics(colour, comment)

    def _make_game(self):
        board = boards.Board(self.board_size)
        if self.handicap_stones:
            board.apply_setup(self.handicap_stones, [], [])
            first_player = 'w'
        else:
            first_player = 'b'
        game = Game(board, first_player)
        game.set_move_limit(self.move_limit)
        game.set_game_over_callback(self.backend.end_game)
        return game

    def _do_move(self, game):
        colour = game.next_player
        opponent = opponent_of(colour)
        action, detail = self.backend.get_move(colour)
        if action == 'forfeit':
            game.record_forfeit_by(colour, detail)
        elif action == 'resign':
            game.record_resignation_by(colour)
        elif action == 'claim':
            game.record_claim_by(colour)
        elif action == 'move':
            move = detail
        else:
            raise ValueError("bad get_move action: %s" % action)

        if game.is_over:
            self._set_final_diagnostics(
                colour, self.backend.get_last_move_comment(colour))
            return

        # Record the move, and so call end_game() if the move ends the game,
        # before asking for the comment.
        game.record_move(colour, move)
        comment = self.backend.get_last_move_comment(colour)

        if game.seen_forfeit:
            self._set_final_diagnostics(colour, comment)
            return

        status, msg = self.backend.notify_move(opponent, move)
        if status not in ('reject', 'error', 'accept'):
            raise ValueError("bad notify_move status: %s" % status)
        # If the game is over (typically a game-ending pass), there's no need to
        # treat a failure response as a forfeit.
        if (not game.is_over) and (status != 'accept'):
            if status == 'reject':
                # we assume the move really was illegal, so 'colour' should lose
                forfeiter = colour
            else:
                forfeiter = opponent
            game.record_forfeit_by(forfeiter, msg)
            self._set_final_diagnostics(colour, comment)
            return

        self.moves.append((colour, move, comment))

        if self.after_move_callback:
            self.after_move_callback(colour=colour, move=move, board=game.board)

    def _set_result(self, game):
        if game.passed_out:
            self.game_score = self.backend.score_game(game.board)
            self.result = self.result_class.from_game_score(self.game_score)
        else:
            self.result = self.result_class.from_unscored_game(game)

    def run(self):
        """Run the game, to completion.

        Sets the 'result' attribute.

        Propagates any exceptions from backend methods:
          get_move()
          notify_move()
          score_game()
          get_last_move_comment()
          end_game()

        Propagates any exceptions from any after-move callback.

        If an exception is propagated, 'result' will not be set, but
        get_moves() will reflect the moves which were completed.

        """
        if self._state not in (1, 2):
            raise GameRunnerStateError
        game = self._make_game()
        self._state = 3
        while not game.is_over:
            self._do_move(game)
        self._set_result(game)

    def get_moves(self):
        """Retrieve a list of the moves played.

        Returns a list of tuples (colour, move, comment)
          move is a pair (row, col), or None for a pass

        Returns an empty list if run() has not been called.

        If the game ended due to an illegal move (or a move rejected by the
        other player), that move is not included (result.detail indicates what
        it was).

        """
        return self.moves

    def get_final_diagnostics(self):
        """Retrieve any comment from a resignation or game-forfeiting move.

        Returns a Diagnostics instance if the game has been resigned or
        forfeited, and the resigning or forfeiting player provided a comment.

        Otherwise returns None.

        """
        return self.final_diagnostics

    def get_game_score(self):
        """Retrieve scoring details from a passed-out game.

        Returns the score returned by the call to backend.score_game().

        Returns None if the game was not passed out.

        """
        return self.game_score

    def make_sgf(self):
        """Return an SGF description of the game.

        Returns an Sgf_game object with the following root node properties set:
          FF GM CA
          DT AP SZ KM
          HA (if there was a handicap)
          RE (if the result is known)

        Doesn't set a root node comment. Doesn't put result.detail anywhere.

        The moves described are the same as those from get_moves().

        Anything returned by backend.get_last_move_comment() is used as a
        comment on the corresponding move (in the final node for comments on
        resignation, forfeits and so on).

        """
        sgf_game = sgf.Sgf_game(self.board_size)
        root = sgf_game.get_root()
        root.set('KM', self.komi)
        root.set('AP', ("gomill",  __version__))
        if self.result is not None:
            root.set('RE', self.result.sgf_result)
        for prop, value in self.additional_sgf_props:
            root.set(prop, value)
        sgf_game.set_date()
        if self.handicap_stones:
            root.set_setup_stones(black=self.handicap_stones, white=[])
        for colour, move, comment in self.moves:
            node = sgf_game.extend_main_sequence()
            node.set_move(colour, move)
            if comment is not None:
                node.set("C", comment)
        final = self.get_final_diagnostics()
        if final is not None:
            sgf_game.get_last_node().add_comment_text(
                "final message from %s: <<<\n%s\n>>>" %
                (final.colour, final.message))
        return sgf_game

