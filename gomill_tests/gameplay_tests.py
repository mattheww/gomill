"""Tests for gameplay.py"""

from textwrap import dedent

from gomill.common import move_from_vertex, format_vertex
from gomill import ascii_boards
from gomill import boards
from gomill import gameplay

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


### Game

class Game_fixture(object):
    def __init__(self, tc, **kwargs):
        self.tc = tc
        kwargs.setdefault('board', boards.Board(9))
        self.game = gameplay.Game(**kwargs)

    def check_not_over(self):
        self.tc.assertIs(self.game.is_over, False)
        self.tc.assertIs(self.game.passed_out, False)
        self.tc.assertIs(self.game.seen_resignation, False)
        self.tc.assertIs(self.game.seen_claim, False)
        self.tc.assertIs(self.game.seen_forfeit, False)
        self.tc.assertIs(self.game.hit_move_limit, False)
        self.tc.assertIsNone(self.game.winner)
        self.tc.assertIsNone(self.game.forfeit_reason)

    def check_over(self, expected_reason):
        self.tc.assertIs(self.game.is_over, True)
        for reason in [
            'passed_out',
            'seen_resignation',
            'seen_claim',
            'seen_forfeit',
            'hit_move_limit',
            ]:
            if reason == expected_reason:
                self.tc.assertIs(getattr(self.game, reason), True)
            else:
                self.tc.assertIs(getattr(self.game, reason), False)
        if expected_reason in ('passed_out', 'hit_move_limit'):
            self.tc.assertIsNone(self.game.winner)
        else:
            self.tc.assertIsNotNone(self.game.winner)
        if expected_reason == 'seen_forfeit':
            self.tc.assertIsNotNone(self.game.forfeit_reason)
        else:
            self.tc.assertIsNone(self.game.forfeit_reason)

    def check_legal_moves(self, moves):
        for colour, vertex in moves:
            self.game.record_move(colour, move_from_vertex(vertex, 9))
            self.check_not_over()


DIAGRAM1 = """\
9  .  .  .  .  .  .  .  .  .
8  .  .  .  .  .  .  .  .  .
7  .  .  .  .  .  .  .  .  .
6  .  .  .  .  .  .  .  .  .
5  .  .  .  .  .  .  .  .  .
4  .  .  .  o  .  .  .  .  .
3  .  .  .  #  .  .  .  .  .
2  .  o  .  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J
"""

def test_game_basic(tc):
    fx = Game_fixture(tc)
    game = fx.game
    tc.assertEqual(game.board.side, 9)
    tc.assertIs(game.board.is_empty(), True)
    tc.assertIsNone(game.move_limit)
    fx.check_not_over()
    tc.assertEqual(game.move_count, 0)
    tc.assertEqual(game.next_player, 'b')
    tc.assertEqual(game.pass_count, 0)
    game.record_move('b', (2, 3))
    fx.check_not_over()
    tc.assertEqual(game.move_count, 1)
    tc.assertEqual(game.next_player, 'w')
    tc.assertEqual(game.pass_count, 0)
    tc.assertRaisesRegexp(gameplay.GameStateError, r"^w is next to play$",
                          game.record_move, 'b', (1, 1))
    tc.assertRaises(IndexError, game.record_move, 'w', (-1, 1))
    fx.check_not_over()
    game.record_move('w', (1, 1))
    game.record_move('b', None)
    tc.assertEqual(game.move_count, 3)
    tc.assertEqual(game.pass_count, 1)
    fx.check_not_over()
    game.record_move('w', (3, 3))
    tc.assertEqual(game.move_count, 4)
    tc.assertEqual(game.pass_count, 0)
    game.record_move('b', None)
    game.record_move('w', None)
    tc.assertEqual(game.move_count, 6)
    tc.assertEqual(game.pass_count, 2)
    fx.check_over('passed_out')
    tc.assertBoardEqual(game.board, DIAGRAM1)
    tc.assertRaisesRegexp(gameplay.GameStateError, r"^game is already over$",
                          game.record_move, 'b', (3, 3))
    tc.assertRaisesRegexp(gameplay.GameStateError, r"^game is already over$",
                          game.record_resignation_by, 'b')
    tc.assertRaisesRegexp(gameplay.GameStateError, r"^game is already over$",
                          game.record_claim_by, 'b')
    tc.assertRaisesRegexp(gameplay.GameStateError, r"^game is already over$",
                          game.record_forfeit_by, 'b', "no good reason")


def test_game_illegal_move(tc):
    fx = Game_fixture(tc)
    game = fx.game
    game.record_move('b', (2, 3))
    fx.check_not_over()
    game.record_move('w', (2, 3))
    fx.check_over('seen_forfeit')
    tc.assertEqual(game.winner, 'b')
    tc.assertEqual(game.forfeit_reason, "attempted move to occupied point D3")
    tc.assertEqual(game.move_count, 1)

def test_game_ko_violation(tc):
    # After these moves, b E5 is a ko violation
    ko_setup_moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'),
        ('b', 'D4'), ('w', 'E6'),
        ('b', 'E5'), ('w', 'D5'),
        ]

    fx = Game_fixture(tc)
    fx.check_legal_moves(ko_setup_moves)
    fx.game.record_move('b', move_from_vertex('E5', 9))
    fx.check_over('seen_forfeit')
    tc.assertEqual(fx.game.forfeit_reason,
                   "attempted move to ko-forbidden point E5")
    tc.assertEqual(fx.game.move_count, 8)

    Game_fixture(tc).check_legal_moves(ko_setup_moves + [
        ('b', 'A1'), ('w', 'E5'),
        ])

    Game_fixture(tc).check_legal_moves(ko_setup_moves + [
        ('b', 'pass'), ('w', 'E5'),
        ])

    Game_fixture(tc).check_legal_moves(ko_setup_moves + [
        ('b', 'A1'), ('w', 'A2'),
        ('b', 'E5'),
        ])

def test_game_move_limit(tc):
    fx = Game_fixture(tc)
    game = fx.game
    game.set_move_limit(5)
    fx.check_legal_moves([
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'),
        ])
    game.record_move('b', move_from_vertex('C3', 9))
    fx.check_over('hit_move_limit')

def test_game_pass_out_beats_move_limit(tc):
    fx = Game_fixture(tc)
    game = fx.game
    game.set_move_limit(5)
    fx.check_legal_moves([
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'pass'),
        ])
    game.record_move('b', None)
    fx.check_over('passed_out')

def test_game_record_resignation(tc):
    fx = Game_fixture(tc)
    fx.game.record_move('b', (2, 3))
    fx.check_not_over()
    fx.game.record_resignation_by('b')
    fx.check_over('seen_resignation')
    tc.assertEqual(fx.game.winner, 'w')

def test_game_record_claim(tc):
    fx = Game_fixture(tc)
    fx.game.record_move('b', (2, 3))
    fx.check_not_over()
    fx.game.record_claim_by('b')
    fx.check_over('seen_claim')
    tc.assertEqual(fx.game.winner, 'b')

def test_game_record_forfeit(tc):
    fx = Game_fixture(tc)
    fx.game.record_move('b', (2, 3))
    fx.check_not_over()
    fx.game.record_forfeit_by('b', "no good reason")
    fx.check_over('seen_forfeit')
    tc.assertEqual(fx.game.winner, 'w')
    tc.assertEqual(fx.game.forfeit_reason, "no good reason")

DIAGRAM2 = """\
9  .  .  .  .  .  .  .  .  #
8  .  .  .  .  .  .  .  .  .
7  .  .  .  .  .  .  .  .  .
6  .  .  .  #  .  .  .  .  .
5  .  .  .  .  .  .  .  .  .
4  .  .  .  .  .  .  .  .  .
3  .  .  .  o  .  .  .  .  .
2  .  .  #  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J
"""

def test_game_initial_board(tc):
    board = boards.Board(9)
    board.play(1, 2, 'b')
    board.play(5, 3, 'b')
    board.play(8, 8, 'b')
    fx = Game_fixture(tc, board=board, first_player='w')
    game = fx.game
    fx.check_not_over()
    tc.assertEqual(game.move_count, 0)
    tc.assertEqual(game.next_player, 'w')
    game.record_move('w', (2, 3))
    fx.check_not_over()
    tc.assertEqual(game.move_count, 1)
    tc.assertIs(game.board, board)
    tc.assertBoardEqual(game.board, DIAGRAM2)

def test_game_game_over_callback(tc):
    log = []
    def fn():
        log.append("callback")
        tc.assertIs(game.is_over, True)
        tc.assertIs(game.passed_out, True)
        tc.assertIsNone(game.next_player)

    fx = Game_fixture(tc)
    game = fx.game
    game.set_game_over_callback(fn)
    fx.check_legal_moves([
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'pass'),
        ])
    tc.assertEqual(log, [])
    game.record_move('w', None)
    tc.assertEqual(log, ["callback"])
    fx.check_over('passed_out')


### Scoring

def test_adjust_score(tc):
    adjs = gameplay.adjust_score
    tc.assertEqual(adjs(10, 6), ('b', 4))
    tc.assertEqual(adjs(6, 6.5), ('w', 0.5))
    tc.assertEqual(adjs(6, -10), ('b', 16))
    tc.assertEqual(adjs(0, 0), (None, 0))
    tc.assertEqual(adjs(10, 6, 'no', 0), ('b', 4))
    tc.assertEqual(adjs(10, 6, 'short', 0), ('b', 4))
    tc.assertEqual(adjs(10, 6, 'full', 0), ('b', 4))
    tc.assertEqual(adjs(10, 6, 'no', 5), ('b', 4))
    tc.assertEqual(adjs(10, 6, 'short', 5), (None, 0))
    tc.assertEqual(adjs(10, 6, 'full', 5), ('w', 1))
    tc.assertRaises(ValueError, adjs, 10, 6, 'maybe', 5)

def test_game_score(tc):
    gs1 = gameplay.Game_score('b', 1)
    tc.assertEqual(gs1.winner, 'b')
    tc.assertEqual(gs1.margin, 1)
    tc.assertIsNone(gs1.get_detail())
    gs2 = gameplay.Game_score('w', None)
    tc.assertEqual(gs2.winner, 'w')
    tc.assertEqual(gs2.margin, None)
    tc.assertEqual(gs2.get_detail(), "unknown margin")
    gs3 = gameplay.Game_score(None, None)
    tc.assertEqual(gs3.winner, None)
    tc.assertEqual(gs3.margin, None)
    tc.assertEqual(gs3.get_detail(), "no score reported")
    gs4 = gameplay.Game_score(None, 0)
    tc.assertEqual(gs4.winner, None)
    tc.assertEqual(gs4.margin, 0)
    tc.assertIsNone(gs4.get_detail())
    tc.assertRaisesRegexp(ValueError, r"^negative margin$",
                          gameplay.Game_score, 'b', -1)
    tc.assertRaisesRegexp(ValueError, r"winner is set but margin is zero",
                          gameplay.Game_score, 'b', 0)
    tc.assertRaisesRegexp(ValueError, r"no winner, but nonzero margin",
                          gameplay.Game_score, None, 1)

DIAGRAM_B_BY_9 = """\
9  .  .  .  .  .  .  .  .  .
8  .  .  .  .  .  .  .  .  .
7  .  .  .  .  .  .  .  .  .
6  o  o  o  o  o  o  o  o  o
5  #  #  #  #  #  #  #  #  #
4  .  .  .  .  .  .  .  .  .
3  .  .  .  .  .  .  .  .  .
2  .  .  .  .  .  .  .  .  .
1  .  .  .  .  .  .  .  .  .
   A  B  C  D  E  F  G  H  J
"""

def test_game_score_from_position(tc):
    board = ascii_boards.interpret_diagram(DIAGRAM_B_BY_9, 9)
    gs1 = gameplay.Game_score.from_position(board, komi=6.5)
    tc.assertEqual(gs1.winner, 'b')
    tc.assertEqual(gs1.margin, 9-6.5)
    tc.assertIsNone(gs1.get_detail())
    gs2 = gameplay.Game_score.from_position(
        board, komi=0,
        handicap_compensation='full', handicap=9)
    tc.assertEqual(gs2.winner, None)
    tc.assertEqual(gs2.margin, 0)
    tc.assertIsNone(gs2.get_detail())


### Result

def test_result_from_score_unknown(tc):
    result = gameplay.Result.from_score(None, None)
    tc.assertEqual(result.sgf_result, "?")
    tc.assertIsNone(result.detail)
    tc.assertIsNone(result.winning_colour)
    tc.assertIsNone(result.losing_colour)
    tc.assertIs(result.is_jigo, False)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, True)

def test_result_from_score_jigo(tc):
    result = gameplay.Result.from_score(None, 0)
    tc.assertEqual(result.sgf_result, '0')
    tc.assertIsNone(result.detail)
    tc.assertIsNone(result.winning_colour)
    tc.assertIsNone(result.losing_colour)
    tc.assertIs(result.is_jigo, True)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, False)

def test_result_from_score_margin_no_winner(tc):
    tc.assertRaisesRegexp(ValueError, "positive margin without winner",
                          gameplay.Result.from_score, None, 1)

def test_result_from_score_no_margin(tc):
    result = gameplay.Result.from_score('b', None)
    tc.assertEqual(result.sgf_result, 'B+')
    tc.assertIsNone(result.detail)
    tc.assertEqual(result.winning_colour, 'b')
    tc.assertEqual(result.losing_colour, 'w')
    tc.assertIs(result.is_jigo, False)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, False)

def test_result_from_score_winner_zero_margin(tc):
    tc.assertRaisesRegexp(ValueError, "winner with zero margin",
                          gameplay.Result.from_score, 'b', 0)

def test_result_from_score_normal(tc):
    result = gameplay.Result.from_score('w', 1.5)
    tc.assertEqual(result.sgf_result, 'W+1.5')
    tc.assertIsNone(result.detail)
    tc.assertEqual(result.winning_colour, 'w')
    tc.assertEqual(result.losing_colour, 'b')
    tc.assertIs(result.is_jigo, False)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, False)

def test_result_from_score_negative_margin(tc):
    tc.assertRaisesRegexp(ValueError, "negative margin",
                          gameplay.Result.from_score, 'b', -0.5)

def test_result_from_score_detail(tc):
    result = gameplay.Result.from_score('b', 3, "detail")
    tc.assertEqual(result.sgf_result, "B+3")
    tc.assertEqual(result.detail, "detail")

def test_result_from_unscored_game(tc):
    game1 = gameplay.Game(boards.Board(19))
    game1.record_resignation_by('w')
    result = gameplay.Result.from_unscored_game(game1)
    tc.assertEqual(result.sgf_result, "B+R")
    game2 = gameplay.Game(boards.Board(19))
    tc.assertRaisesRegexp(
        ValueError, "^game is not over$",
        gameplay.Result.from_unscored_game, game2)
    game3 = gameplay.Game(boards.Board(19))
    game3.record_move('b', None)
    game3.record_move('w', None)
    tc.assertRaisesRegexp(
        ValueError, "^game is passed out$",
        gameplay.Result.from_unscored_game, game3)

def test_result_from_game_score(tc):
    gs = gameplay.Game_score('b', 1)
    result = gameplay.Result.from_game_score(gs)
    tc.assertEqual(result.sgf_result, 'B+1')
    tc.assertIsNone(result.detail)
    tc.assertEqual(result.winning_colour, 'b')
    tc.assertEqual(result.losing_colour, 'w')
    tc.assertIs(result.is_jigo, False)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, False)

def test_result_from_game_score_no_margin(tc):
    gs = gameplay.Game_score('b', None)
    result = gameplay.Result.from_game_score(gs)
    tc.assertEqual(result.sgf_result, 'B+')
    tc.assertEqual(result.detail, "unknown margin")
    tc.assertEqual(result.winning_colour, 'b')
    tc.assertEqual(result.losing_colour, 'w')
    tc.assertIs(result.is_jigo, False)
    tc.assertIs(result.is_forfeit, False)
    tc.assertIs(result.is_unknown, False)


### Game_runner

class Testing_backend(gameplay.Backend):
    """Backend implementation for testing.

    Instantiate with
      size  -- int
      moves -- list of pairs (colour, vertex)

    Supports special vertex values 'resign', 'claim', and 'forfeit', which
    cause get_move() to return the appropriate action and detail.

    get_move() returns the next move for the requested colour. You can specify
    them interleaved for readability, but it doesn't matter.

    When it gets to the end of the list of moves for a colour it passes, but
    explicit 'pass' in the move list is OK too.

    Public attributes for testing:
      log             -- list of strings describing all operations run
      score_to_return -- the Game_score object returned by score_game()
      board_scored    -- a copy of the board passed in to score_game()

      (score_to_return has white winning by 99)

    To enable last-move comments, set the enabled_get_last_move_comment
    attribute.

    To force notify_move() to reject, set the reject_vertex and reject_as_error
    attributes.

    """
    def __init__(self, size, moves):
        self._size = size
        self._move_iters = {}
        for colour in 'b', 'w':
            self._move_iters[colour] = iter(
                [x for (c, x) in moves if c == colour])
        self.enabled_get_last_move_comment = set()
        self.score_to_return = gameplay.Game_score("w", 99)
        self.log = []
        self.board_scored = None
        self.reject_vertex = None
        self.reject_as_error = False

    def start_new_game(self, board_size, komi):
        # If this fails, the test is written wrongly
        assert board_size == self._size
        self.log.append("start_new_game: size=%r, komi=%r" % (board_size, komi))

    def end_game(self):
        self.log.append("end_game")

    def notify_free_handicap(self, points):
        self.log.append("notify_free_handicap: %r" % (points,))

    def notify_fixed_handicap(self, colour, handicap, points):
        self.log.append("notify_fixed_handicap: %r %r %r" %
                        (colour, handicap, points))

    def _action_for_vertex(self, vertex):
        if vertex in ('resign', 'claim'):
            return vertex, None
        if vertex == 'forfeit':
            return 'forfeit', "programmed forfeit"
        return 'move', move_from_vertex(vertex, self._size)

    def get_move(self, colour):
        try:
            vertex = self._move_iters[colour].next()
            action, detail = self._action_for_vertex(vertex)
        except StopIteration:
            action, detail = 'move', None
        if action == 'move':
            log_description = "move/%s" % format_vertex(detail)
        else:
            log_description = "%s/%r" % (action, detail)
        self.log.append("get_move <- %s: %s" % (colour, log_description))
        self.last_move = log_description
        return action, detail

    def notify_move(self, colour, move):
        if (self.reject_vertex is not None and
            move == move_from_vertex(self.reject_vertex, self._size)):
            if self.reject_as_error:
                self.log.append("notify_move -> %s [error]" % colour)
                return 'error', "programmed error"
            else:
                self.log.append("notify_move -> %s [rejecting]" % colour)
                return 'reject', "programmed reject"
        self.log.append("notify_move -> %s %s" % (colour, format_vertex(move)))
        return 'accept', None

    def score_game(self, board):
        self.log.append("score_game")
        self.board_scored = board.copy()
        return self.score_to_return

    def get_last_move_comment(self, colour):
        self.log.append("get_last_move_comment <- %s" % (colour,))
        if colour in self.enabled_get_last_move_comment:
            for s in reversed(self.log):
                _, found, msg = s.partition("get_move <- %s: " % colour)
                if found:
                    return "%s-%s" % (colour, msg)
            return "..(no moves played)"
        return None


class Game_runner_fixture(object):
    def __init__(self, tc, moves, backend_cls=Testing_backend,
                 size=5, komi=11, move_limit=None):
        self.tc = tc
        self.backend = backend_cls(size, moves)
        self.game_runner = gameplay.Game_runner(
            self.backend, board_size=size, komi=komi, move_limit=move_limit)

    def enable_get_last_move_comment(self, colour):
        self.backend.enabled_get_last_move_comment.add(colour)

    def enable_after_move_callback(self):
        self.callback_boards = []
        def callback(colour, move, board, **kwargs):
            self.backend.log.append("[callback %s %s]" %
                                    (colour, format_vertex(move)))
            self.callback_boards.append(board.copy())
            self.tc.assertEqual(kwargs, {})
        self.game_runner.set_move_callback(callback)

    def force_reject(self, vertex, as_error=False):
        self.backend.reject_vertex = vertex
        self.backend.reject_as_error = as_error

    def run_game(self):
        self.game_runner.prepare()
        self.game_runner.run()

    def check_final_diagnostics(self, colour, message):
        d = self.game_runner.get_final_diagnostics()
        self.tc.assertIsNotNone(d)
        self.tc.assertEqual(d.colour, colour)
        self.tc.assertEqual(d.message, message)

    def sgf_string(self):
        return gomill_test_support.scrub_sgf(
            self.game_runner.make_sgf().serialise(wrap=None))

    def sgf_moves_and_comments(self):
        return gomill_test_support.sgf_moves_and_comments(
            self.game_runner.make_sgf())


def test_game_runner(tc):
    fx = Game_runner_fixture(
        tc, moves=[
            # B+5 on the board
            ('b', 'C1'), ('w', 'D1'),
            ('b', 'C2'), ('w', 'D2'),
            ('b', 'C3'), ('w', 'D3'),
            ('b', 'C4'), ('w', 'D4'),
            ('b', 'C5'), ('w', 'D5'),
            ])
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/C2",
        "get_last_move_comment <- b",
        "notify_move -> w C2",
        "get_move <- w: move/D2",
        "get_last_move_comment <- w",
        "notify_move -> b D2",
        "get_move <- b: move/C3",
        "get_last_move_comment <- b",
        "notify_move -> w C3",
        "get_move <- w: move/D3",
        "get_last_move_comment <- w",
        "notify_move -> b D3",
        "get_move <- b: move/C4",
        "get_last_move_comment <- b",
        "notify_move -> w C4",
        "get_move <- w: move/D4",
        "get_last_move_comment <- w",
        "notify_move -> b D4",
        "get_move <- b: move/C5",
        "get_last_move_comment <- b",
        "notify_move -> w C5",
        "get_move <- w: move/D5",
        "get_last_move_comment <- w",
        "notify_move -> b D5",
        "get_move <- b: move/pass",
        "get_last_move_comment <- b",
        "notify_move -> w pass",
        "get_move <- w: move/pass",
        "end_game",
        "get_last_move_comment <- w",
        "notify_move -> b pass",
        "score_game",
        ])
    tc.assertIs(fx.game_runner.get_game_score(), fx.backend.score_to_return)
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+99')
    tc.assertIsNone(result.detail)
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', (1, 2), None),
        ('w', (1, 3), None),
        ('b', (2, 2), None),
        ('w', (2, 3), None),
        ('b', (3, 2), None),
        ('w', (3, 3), None),
        ('b', (4, 2), None),
        ('w', (4, 3), None),
        ('b', None, None),
        ('w', None, None),
        ])
    tc.assertBoardEqual(
        fx.backend.board_scored,
        dedent("""
        5  .  .  #  o  .
        4  .  .  #  o  .
        3  .  .  #  o  .
        2  .  .  #  o  .
        1  .  .  #  o  .
           A  B  C  D  E
        """).strip())
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]RE[W+99]SZ[5];B[ce];W[de];B[cd];W[dd];B[cc];W[dc];B[cb];W[db];B[ca];W[da];B[tt];W[tt])
""")

def test_game_runner_move_callback(tc):
    fx = Game_runner_fixture(tc, moves=[('b', 'C1'), ('w', 'D1')])
    fx.enable_after_move_callback()
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/pass",
        "get_last_move_comment <- b",
        "notify_move -> w pass",
        "[callback b pass]",
        "get_move <- w: move/pass",
        "end_game",
        "get_last_move_comment <- w",
        "notify_move -> b pass",
        "[callback w pass]",
        "score_game",
        ])
    tc.assertBoardEqual(
        fx.callback_boards[1],
        dedent("""
        5  .  .  .  .  .
        4  .  .  .  .  .
        3  .  .  .  .  .
        2  .  .  .  .  .
        1  .  .  #  o  .
           A  B  C  D  E
        """).strip())

def test_game_runner_resign(tc):
    fx = Game_runner_fixture(
        tc, moves=[('b', 'C1'), ('w', 'D1'), ('b', 'C2'), ('w', 'resign')])
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/C2",
        "get_last_move_comment <- b",
        "notify_move -> w C2",
        "get_move <- w: resign/None",
        "end_game",
        'get_last_move_comment <- w',
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'B+R')
    tc.assertIsNone(result.detail)
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', (1, 2), None),
        ])
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]RE[B+R]SZ[5];B[ce];W[de];B[cd])
""")

def test_game_runner_claim(tc):
    fx = Game_runner_fixture(
        tc, moves=[('b', 'C1'), ('w', 'D1'), ('b', 'C2'), ('w', 'claim')])
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/C2",
        "get_last_move_comment <- b",
        "notify_move -> w C2",
        "get_move <- w: claim/None",
        "end_game",
        'get_last_move_comment <- w',
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+')
    tc.assertEqual(result.detail, "claim")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', (1, 2), None),
        ])
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]RE[W+]SZ[5];B[ce];W[de];B[cd])
""")

def test_game_runner_forfeit(tc):
    fx = Game_runner_fixture(
        tc, moves=[('b', 'C1'), ('w', 'D1'), ('b', 'forfeit')])
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: forfeit/'programmed forfeit'",
        "end_game",
        'get_last_move_comment <- b',
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+F')
    tc.assertEqual(result.detail, "programmed forfeit")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])
    # NB, result.detail is not present in the SGF
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]RE[W+F]SZ[5];B[ce];W[de])
""")

def test_game_runner_illegal_move(tc):
    fx = Game_runner_fixture(tc, moves=[('b', 'C1'), ('w', 'D1'), ('b', 'D1')])
    fx.enable_after_move_callback()
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/D1",
        "end_game",
        "get_last_move_comment <- b",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+F')
    tc.assertEqual(result.detail, "attempted move to occupied point D1")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])

def test_game_runner_move_rejected_as_illegal(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'E1')])
    fx.force_reject('E1')
    fx.enable_after_move_callback()
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/E1",
        "get_last_move_comment <- b",
        "notify_move -> w [rejecting]",
        "end_game",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+F')
    tc.assertEqual(result.detail, "programmed reject")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])

def test_game_runner_notify_move_failed(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'E1')])
    fx.force_reject('E1', as_error=True)
    fx.enable_after_move_callback()
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/E1",
        "get_last_move_comment <- b",
        "notify_move -> w [error]",
        "end_game",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'B+F')
    tc.assertEqual(result.detail, "programmed error")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])

def test_game_runner_move_limit(tc):
    fx = Game_runner_fixture(
        tc, moves=[('b', 'C1'), ('w', 'D1'), ('b', 'C2'), ('w', 'D2')],
        move_limit=3)
    fx.enable_after_move_callback()
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/C2",
        "end_game",
        "get_last_move_comment <- b",
        "notify_move -> w C2",
        "[callback b C2]",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'Void')
    tc.assertEqual(result.detail, "hit move limit")
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', (1, 2), None),
        ])

def test_game_runner_last_move_comment(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'C2'), ('w', 'D2')])
    fx.enable_get_last_move_comment('b')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/C2",
        "get_last_move_comment <- b",
        "notify_move -> w C2",
        "get_move <- w: move/D2",
        "get_last_move_comment <- w",
        "notify_move -> b D2",
        "get_move <- b: move/pass",
        "get_last_move_comment <- b",
        "notify_move -> w pass",
        "get_move <- w: move/pass",
        "end_game",
        "get_last_move_comment <- w",
        "notify_move -> b pass",
        "score_game",
        ])
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), "b-move/C1"),
        ('w', (0, 3), None),
        ('b', (1, 2), "b-move/C2"),
        ('w', (1, 3), None),
        ('b', None, "b-move/pass"),
        ('w', None, None),
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        'root: --',
        'b C1: b-move/C1',
        'w D1: --',
        'b C2: b-move/C2',
        'w D2: --',
        'b pass: b-move/pass',
        'w pass: --',
        ])

def test_game_runner_last_move_comment_resign(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'resign')])
    fx.enable_get_last_move_comment('b')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: resign/None",
        "end_game",
        'get_last_move_comment <- b',
        ])
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, "W+R")
    fx.check_final_diagnostics('b', "b-resign/None")
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), "b-move/C1"),
        ('w', (0, 3), None),
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        'root: --',
        'b C1: b-move/C1',
        'w D1: final message from b: <<<\nb-resign/None\n>>>',
        ])

def test_game_runner_last_move_comment_from_both_resign(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'resign')])
    fx.enable_get_last_move_comment('b')
    fx.enable_get_last_move_comment('w')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: resign/None",
        "end_game",
        'get_last_move_comment <- b',
        ])
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, "W+R")
    fx.check_final_diagnostics('b', "b-resign/None")
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), "b-move/C1"),
        ('w', (0, 3), "w-move/D1"),
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        'root: --',
        'b C1: b-move/C1',
        'w D1: w-move/D1\n\nfinal message from b: <<<\nb-resign/None\n>>>',
        ])

def test_game_runner_last_move_comment_forfeit_illegal(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'C1')])
    fx.enable_get_last_move_comment('b')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/C1",
        "end_game",
        "get_last_move_comment <- b",
        ])
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, "W+F")
    fx.check_final_diagnostics('b', "b-move/C1")
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), "b-move/C1"),
        ('w', (0, 3), None),
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        'root: --',
        'b C1: b-move/C1',
        'w D1: final message from b: <<<\nb-move/C1\n>>>',
        ])

def test_game_runner_last_move_comment_rejected(tc):
    fx = Game_runner_fixture(
        tc,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'E1')])
    fx.force_reject('E1')
    fx.enable_get_last_move_comment('b')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/E1",
        "get_last_move_comment <- b",
        "notify_move -> w [rejecting]",
        "end_game",
        ])
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, "W+F")
    fx.check_final_diagnostics('b', "b-move/E1")
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), "b-move/C1"),
        ('w', (0, 3), None),
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        'root: --',
        'b C1: b-move/C1',
        'w D1: final message from b: <<<\nb-move/E1\n>>>',
        ])

def test_game_runner_last_move_comment_zero_move_game(tc):
    # Checking SGF output when get_last_node() == get_root().
    fx = Game_runner_fixture(tc, moves=[('b', 'forfeit')])
    fx.enable_get_last_move_comment('b')
    fx.run_game()
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: forfeit/'programmed forfeit'",
        "end_game",
        'get_last_move_comment <- b',
        ])
    result = fx.game_runner.result
    tc.assertEqual(result.sgf_result, 'W+F')
    tc.assertEqual(result.detail, "programmed forfeit")
    fx.check_final_diagnostics('b', "b-forfeit/'programmed forfeit'")
    tc.assertEqual(fx.game_runner.get_moves(), [
        ])
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "root: final message from b: <<<\nb-forfeit/'programmed forfeit'\n>>>",
        ])

def test_game_runner_fixed_handicap(tc):
    fx = Game_runner_fixture(
        tc, size=9,
        moves=[('w', 'C1'), ('b', 'D1')])
    fx.game_runner.prepare()
    tc.assertRaises(ValueError, fx.game_runner.set_handicap,
                    handicap=1, is_free=False)
    tc.assertRaises(ValueError, fx.game_runner.set_handicap,
                    handicap=10, is_free=False)
    fx.game_runner.set_handicap(3, is_free=False)
    fx.game_runner.run()
    tc.assertEqual(fx.backend.log[:4], [
        "start_new_game: size=9, komi=11.0",
        "notify_fixed_handicap: 'b' 3 [(2, 2), (6, 6), (6, 2)]",
        "notify_fixed_handicap: 'w' 3 [(2, 2), (6, 6), (6, 2)]",
        "get_move <- w: move/C1",
        ])
    tc.assertBoardEqual(
        fx.backend.board_scored,
        dedent("""
        9  .  .  .  .  .  .  .  .  .
        8  .  .  .  .  .  .  .  .  .
        7  .  .  #  .  .  .  #  .  .
        6  .  .  .  .  .  .  .  .  .
        5  .  .  .  .  .  .  .  .  .
        4  .  .  .  .  .  .  .  .  .
        3  .  .  #  .  .  .  .  .  .
        2  .  .  .  .  .  .  .  .  .
        1  .  .  o  #  .  .  .  .  .
           A  B  C  D  E  F  G  H  J
        """).strip())
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AB[cc][cg][gc]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]HA[3]KM[11]RE[W+99]SZ[9];W[ci];B[di];W[tt];B[tt])
""")

def test_game_runner_free_handicap(tc):
    class _Backend(Testing_backend):
        def get_free_handicap(self, handicap):
            self.log.append("get_free_handicap: %r" % (handicap,))
            return [move_from_vertex(s, self._size)
                    for s in "e4 e2 c2".split()]

    fx = Game_runner_fixture(tc, backend_cls=_Backend,
                             moves=[('w', 'C1'), ('b', 'D1')])
    fx.game_runner.prepare()
    fx.game_runner.set_handicap(3, is_free=True)
    fx.game_runner.run()
    tc.assertEqual(fx.backend.log[:4], [
        "start_new_game: size=5, komi=11.0",
        "get_free_handicap: 3",
        "notify_free_handicap: [(3, 4), (1, 4), (1, 2)]",
        "get_move <- w: move/C1",
        ])
    tc.assertBoardEqual(
        fx.backend.board_scored,
        dedent("""
        5  .  .  .  .  .
        4  .  .  .  .  #
        3  .  .  .  .  .
        2  .  .  #  .  #
        1  .  .  o  #  .
           A  B  C  D  E
        """).strip())
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AB[cd][eb][ed]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]HA[3]KM[11]RE[W+99]SZ[5];W[ce];B[de];W[tt];B[tt])
""")

def test_game_runner_free_handicap_bounds(tc):
    class _Backend(Testing_backend):
        def get_free_handicap(self, handicap):
            self.log.append("get_free_handicap: %r" % (handicap,))
            return []

    fx = Game_runner_fixture(tc, backend_cls=_Backend,
                             moves=[('w', 'C1'), ('b', 'D1')])
    fx.game_runner.prepare()
    tc.assertRaises(ValueError, fx.game_runner.set_handicap,
                    handicap=1, is_free=True)
    tc.assertRaises(ValueError, fx.game_runner.set_handicap,
                    handicap=25, is_free=True)
    fx.game_runner.set_handicap(24, is_free=True)
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_free_handicap: 24",
        "notify_free_handicap: []",
        ])

def test_game_runner_exception_from_get_move(tc):
    class _Backend(Testing_backend):
        def get_move(self, colour):
            if len(self.log) >= 7:
                1 / 0
            return Testing_backend.get_move(self, colour)

    fx = Game_runner_fixture(
        tc, backend_cls=_Backend,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'E1')])
    tc.assertRaises(ZeroDivisionError, fx.run_game)
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    tc.assertIsNone(fx.game_runner.result)
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]SZ[5];B[ce];W[de])
""")

def test_game_runner_exception_from_notify_move(tc):
    class _Backend(Testing_backend):
        def notify_move(self, colour, move):
            if len(self.log) >= 8:
                1 / 0
            return Testing_backend.notify_move(self, colour, move)

    fx = Game_runner_fixture(
        tc, backend_cls=_Backend,
        moves=[('b', 'C1'), ('w', 'D1'), ('b', 'E1')])
    tc.assertRaises(ZeroDivisionError, fx.run_game)
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "get_move <- b: move/E1",
        "get_last_move_comment <- b",
        ])
    tc.assertIsNone(fx.game_runner.get_game_score())
    tc.assertIsNone(fx.game_runner.result)
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    # Note the move which triggered the exception doesn't appear
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ])
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]SZ[5];B[ce];W[de])
""")

def test_game_runner_exception_from_score_game(tc):
    class _Backend(Testing_backend):
        def score_game(self, board):
            1 / 0

    fx = Game_runner_fixture(
        tc, backend_cls=_Backend,
        moves=[('b', 'C1'), ('w', 'D1')])
    tc.assertRaises(ZeroDivisionError, fx.run_game)
    tc.assertIsNone(fx.game_runner.get_game_score())
    tc.assertIsNone(fx.game_runner.result)
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', None, None),
        ('w', None, None),
        ])
    tc.assertEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[11]SZ[5];B[ce];W[de];B[tt];W[tt])
""")

def test_game_runner_exception_from_move_callback(tc):
    fx = Game_runner_fixture(tc, moves=[('b', 'C1'), ('w', 'D1')])
    def callback(colour, move, board, **kwargs):
        fx.backend.log.append("[callback %s %s]" %
                              (colour, format_vertex(move)))
        if move is None:
            1 / 0
    fx.game_runner.set_move_callback(callback)

    tc.assertRaises(ZeroDivisionError, fx.run_game)
    tc.assertEqual(fx.backend.log, [
        "start_new_game: size=5, komi=11.0",
        "get_move <- b: move/C1",
        "get_last_move_comment <- b",
        "notify_move -> w C1",
        "[callback b C1]",
        "get_move <- w: move/D1",
        "get_last_move_comment <- w",
        "notify_move -> b D1",
        "[callback w D1]",
        "get_move <- b: move/pass",
        "get_last_move_comment <- b",
        "notify_move -> w pass",
        "[callback b pass]",
        ])
    tc.assertIsNone(fx.game_runner.get_final_diagnostics())
    tc.assertEqual(fx.game_runner.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', None, None),
        ])

def test_game_runner_defaults(tc):
    backend = Testing_backend(size=9, moves=[('b', 'C1'), ('w', 'D1')])
    gr = gameplay.Game_runner(backend, board_size=9)
    tc.assertIsNone(gr.move_limit)
    gr.prepare()
    gr.run()
    tc.assertEqual(backend.log[0], "start_new_game: size=9, komi=0.0")
    tc.assertIsNone(gr.get_final_diagnostics())
    tc.assertEqual(gr.get_moves(), [
        ('b', (0, 2), None),
        ('w', (0, 3), None),
        ('b', None, None),
        ('w', None, None),
        ])

def test_game_runner_result_setting(tc):
    # Tests Game_runner._set_result() behaves as expected
    # Also tests set_result_class()

    class Mock_result_class(object):
        @staticmethod
        def from_game_score(game_score):
            return ("from_game_score", game_score)

        @staticmethod
        def from_unscored_game(game):
            return ("from_unscored_game", game)

    backend1 = Testing_backend(size=5, moves=[('b', 'C1'), ('w', 'D1')])
    gr1 = gameplay.Game_runner(backend1, board_size=5, komi=11)
    gr1.set_result_class(Mock_result_class)
    gr1.prepare()
    gr1.run()
    tc.assertEqual(gr1.result, ("from_game_score", backend1.score_to_return))

    backend2 = Testing_backend(size=5, moves=[('b', 'C1'), ('w', 'resign')])
    gr2 = gameplay.Game_runner(backend2, board_size=5, komi=11)
    gr2.set_result_class(Mock_result_class)
    gr2.prepare()
    gr2.run()
    tc.assertEqual(gr2.result[0], "from_unscored_game")
    game = gr2.result[1]
    tc.assertIs(game.seen_resignation, True)
    tc.assertEqual(game.move_count, 1)

def test_game_runner_state_checks(tc):
    backend1 = Testing_backend(size=9, moves=[('b', 'C1'), ('w', 'D1')])
    gr1 = gameplay.Game_runner(backend1, board_size=9)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.set_handicap, 3, False)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.run)
    gr1.prepare()
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.prepare)
    gr1.run()
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.prepare)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.set_handicap, 3, False)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.run)
    tc.assertFalse(gr1.make_sgf().get_root().has_property("HA"))

    backend2 = Testing_backend(size=9, moves=[('b', 'C1'), ('w', 'D1')])
    gr2 = gameplay.Game_runner(backend2, board_size=9)
    gr2.prepare()
    gr2.set_handicap(3, False)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.prepare)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.set_handicap, 9, False)
    gr2.run()
    tc.assertRaises(gameplay.GameRunnerStateError, gr2.prepare)
    tc.assertRaises(gameplay.GameRunnerStateError, gr2.set_handicap, 3, False)
    tc.assertRaises(gameplay.GameRunnerStateError, gr1.run)
    tc.assertEqual(gr2.make_sgf().get_root().get("HA"), 3)
