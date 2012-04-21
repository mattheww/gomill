"""Tests for gtp_games.py"""

import cPickle as pickle

from gomill import boards
from gomill import gtp_controller
from gomill import gtp_games
from gomill import sgf
from gomill.common import format_vertex

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests.gtp_engine_fixtures import Programmed_player

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))
    for t in handicap_compensation_tests:
        suite.addTest(Handicap_compensation_TestCase(*t))


class Game_fixture(test_framework.Fixture):
    """Fixture managing a Gtp_game.

    Instantiate with the player objects (defaults to a Test_player).

    Additional keyword arguments are passed on to Game.

    attributes:
      game         -- Gtp_game
      controller_b -- Gtp_controller
      controller_w -- Gtp_controller
      channel_b    -- Testing_gtp_channel
      channel_w    -- Testing_gtp_channel
      engine_b     -- Test_gtp_engine_protocol
      engine_w     -- Test_gtp_engine_protocol
      player_b     -- player object
      player_w     -- player object

    """
    def __init__(self, tc, player_b=None, player_w=None, **kwargs):
        self.tc = tc
        kwargs.setdefault('board_size', 9)
        game = gtp_games.Game(**kwargs)
        game.set_player_code('b', 'one')
        game.set_player_code('w', 'two')
        if player_b is None:
            player_b = gtp_engine_fixtures.Test_player()
        if player_w is None:
            player_w = gtp_engine_fixtures.Test_player()
        engine_b = gtp_engine_fixtures.make_player_engine(player_b)
        engine_w = gtp_engine_fixtures.make_player_engine(player_w)
        channel_b = gtp_controller_test_support.Testing_gtp_channel(engine_b)
        channel_w = gtp_controller_test_support.Testing_gtp_channel(engine_w)
        controller_b = gtp_controller.Gtp_controller(channel_b, 'player one')
        controller_w = gtp_controller.Gtp_controller(channel_w, 'player two')
        game.set_player_controller('b', controller_b)
        game.set_player_controller('w', controller_w)
        self.game = game
        self.controller_b = controller_b
        self.controller_w = controller_w
        self.channel_b = channel_b
        self.channel_w = channel_w
        self.engine_b = channel_b.engine
        self.engine_w = channel_w.engine
        self.player_b = channel_b.engine.player
        self.player_w = channel_w.engine.player

    def check_moves(self, expected_moves):
        """Check that the game's moves are as expected.

        expected_moves -- list of pairs (colour, vertex)

        """
        game_moves = [(colour, format_vertex(move))
                      for (colour, move, comment) in self.game.moves]
        self.tc.assertListEqual(game_moves, expected_moves)

    def run_score_test(self, b_score, w_score, allowed_scorers="bw"):
        """Run a game and let the players score it.

        b_score, w_score -- string for final_score to return

        If b_score or w_score is None, the player won't implement final_score.
        If b_score or w_score is an exception, the final_score will fail

        """
        def handle_final_score_b(args):
            if b_score is Exception:
                raise b_score
            return b_score
        def handle_final_score_w(args):
            if w_score is Exception:
                raise w_score
            return w_score
        if b_score is not None:
            self.engine_b.add_command('final_score', handle_final_score_b)
        if w_score is not None:
            self.engine_w.add_command('final_score', handle_final_score_w)
        for colour in allowed_scorers:
            self.game.allow_scorer(colour)
        self.game.ready()
        self.game.run()

    def sgf_string(self):
        return gomill_test_support.scrub_sgf(
            self.game.make_sgf().serialise(wrap=None))


def test_game(tc):
    fx = Game_fixture(tc)
    tc.assertDictEqual(fx.game.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIs(fx.game.get_controller('b'), fx.controller_b)
    tc.assertIs(fx.game.get_controller('w'), fx.controller_w)
    fx.game.use_internal_scorer()
    fx.game.ready()
    tc.assertIsNone(fx.game.game_id)
    tc.assertIsNone(fx.game.result)
    fx.game.run()
    fx.game.close_players()
    tc.assertIsNone(fx.game.describe_late_errors())
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertEqual(fx.game.result.player_b, 'one')
    tc.assertEqual(fx.game.result.player_w, 'two')
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.losing_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertEqual(fx.game.result.losing_player, 'two')
    tc.assertEqual(fx.game.result.sgf_result, "B+18")
    tc.assertFalse(fx.game.result.is_forfeit)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertIsNone(fx.game.result.detail)
    tc.assertIsNone(fx.game.result.game_id)
    tc.assertEqual(fx.game.result.describe(), "one beat two B+18")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one beat two B+18")
    tc.assertEqual(fx.game.describe_scoring(), "one beat two B+18")
    tc.assertEqual(result2.player_b, 'one')
    tc.assertEqual(result2.player_w, 'two')
    tc.assertIs(result2.is_jigo, False)
    tc.assertDictEqual(fx.game.result.cpu_times, {'one' : None, 'two' : None})
    tc.assertListEqual(fx.game.moves, [
        ('b', (0, 4), None), ('w', (0, 6), None),
        ('b', (1, 4), None), ('w', (1, 6), None),
        ('b', (2, 4), None), ('w', (2, 6), None),
        ('b', (3, 4), None), ('w', (3, 6), None),
        ('b', (4, 4), None), ('w', (4, 6), None),
        ('b', (5, 4), None), ('w', (5, 6), None),
        ('b', (6, 4), None), ('w', (6, 6), None),
        ('b', (7, 4), None), ('w', (7, 6), None),
        ('b', (8, 4), None), ('w', (8, 6), None),
        ('b', None, None), ('w', None, None)])
    fx.check_moves([
        ('b', 'E1'), ('w', 'G1'),
        ('b', 'E2'), ('w', 'G2'),
        ('b', 'E3'), ('w', 'G3'),
        ('b', 'E4'), ('w', 'G4'),
        ('b', 'E5'), ('w', 'G5'),
        ('b', 'E6'), ('w', 'G6'),
        ('b', 'E7'), ('w', 'G7'),
        ('b', 'E8'), ('w', 'G8'),
        ('b', 'E9'), ('w', 'G9'),
        ('b', 'pass'), ('w', 'pass'),
        ])
    tc.assertEqual(fx.engine_b.commands_handled, [
        ('protocol_version', []),
        ('boardsize', ['9']),
        ('clear_board', []),
        ('komi', ['0.0']),
        ('genmove', ['b']),
        ('known_command', ['gomill-explain_last_move']),
        ('play', ['w', 'g1']),
        ('genmove', ['b']),
        ('play', ['w', 'g2']),
        ('genmove', ['b']),
        ('play', ['w', 'g3']),
        ('genmove', ['b']),
        ('play', ['w', 'g4']),
        ('genmove', ['b']),
        ('play', ['w', 'g5']),
        ('genmove', ['b']),
        ('play', ['w', 'g6']),
        ('genmove', ['b']),
        ('play', ['w', 'g7']),
        ('genmove', ['b']),
        ('play', ['w', 'g8']),
        ('genmove', ['b']),
        ('play', ['w', 'g9']),
        ('genmove', ['b']),
        ('play', ['w', 'pass']),
        ('known_command', ['gomill-cpu_time']),
        ('quit', []),
        ])
    tc.assertEqual(fx.engine_w.commands_handled, [
        ('protocol_version', []),
        ('boardsize', ['9']),
        ('clear_board', []),
        ('komi', ['0.0']),
        ('play', ['b', 'e1']),
        ('genmove', ['w']),
        ('known_command', ['gomill-explain_last_move']),
        ('play', ['b', 'e2']),
        ('genmove', ['w']),
        ('play', ['b', 'e3']),
        ('genmove', ['w']),
        ('play', ['b', 'e4']),
        ('genmove', ['w']),
        ('play', ['b', 'e5']),
        ('genmove', ['w']),
        ('play', ['b', 'e6']),
        ('genmove', ['w']),
        ('play', ['b', 'e7']),
        ('genmove', ['w']),
        ('play', ['b', 'e8']),
        ('genmove', ['w']),
        ('play', ['b', 'e9']),
        ('genmove', ['w']),
        ('play', ['b', 'pass']),
        ('genmove', ['w']),
        ('known_command', ['gomill-cpu_time']),
        ('quit', []),
        ])

def test_unscored_game(tc):
    fx = Game_fixture(tc)
    tc.assertDictEqual(fx.game.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIs(fx.game.get_controller('b'), fx.controller_b)
    tc.assertIs(fx.game.get_controller('w'), fx.controller_w)
    fx.game.allow_scorer('b') # it can't score
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertIsNone(fx.game.describe_late_errors())
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertIsNone(fx.game.result.losing_colour)
    tc.assertIsNone(fx.game.result.winning_player)
    tc.assertIsNone(fx.game.result.losing_player)
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertFalse(fx.game.result.is_forfeit)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertEqual(fx.game.result.detail, "no score reported")
    tc.assertEqual(fx.game.result.describe(),
                   "one vs two ? (no score reported)")
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (no score reported)")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one vs two ? (no score reported)")
    tc.assertIs(result2.is_jigo, False)

def test_jigo(tc):
    fx = Game_fixture(tc, komi=18.0)
    fx.game.use_internal_scorer()
    fx.game.ready()
    tc.assertIsNone(fx.game.result)
    fx.game.run()
    fx.game.close_players()
    tc.assertIsNone(fx.game.describe_late_errors())
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertEqual(fx.game.result.player_b, 'one')
    tc.assertEqual(fx.game.result.player_w, 'two')
    tc.assertEqual(fx.game.result.winning_colour, None)
    tc.assertEqual(fx.game.result.losing_colour, None)
    tc.assertEqual(fx.game.result.winning_player, None)
    tc.assertEqual(fx.game.result.losing_player, None)
    tc.assertEqual(fx.game.result.sgf_result, "0")
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.is_jigo, True)
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.describe(), "one vs two jigo")
    tc.assertEqual(fx.game.describe_scoring(), "one vs two jigo")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one vs two jigo")
    tc.assertEqual(result2.player_b, 'one')
    tc.assertEqual(result2.player_w, 'two')
    tc.assertIs(result2.is_jigo, True)

def test_players_score_agree(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3", "B+3.0")
    tc.assertEqual(fx.game.result.sgf_result, "B+3")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(), "one beat two B+3")

def test_players_score_agree_draw(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("0", "0")
    tc.assertEqual(fx.game.result.sgf_result, "0")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(), "one vs two jigo")

def test_players_score_disagree(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3.0", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+3.0\n"
                   "two final_score: W+4")

def test_players_score_disagree_one_no_margin(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+\n"
                   "two final_score: W+4")

def test_players_score_disagree_one_jigo(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("0", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: 0\n"
                   "two final_score: W+4")

def test_players_score_disagree_equal_margin(tc):
    # check equal margin in both directions doesn't confuse it
    fx = Game_fixture(tc)
    fx.run_score_test("b+4", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+4\n"
                   "two final_score: W+4")

def test_players_score_one_unreliable(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3", "W+4", allowed_scorers="w")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")

def test_players_score_one_cannot_score(tc):
    fx = Game_fixture(tc)
    fx.run_score_test(None, "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")

def test_players_score_one_fails(tc):
    fx = Game_fixture(tc)
    fx.run_score_test(Exception, "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")

def test_players_score_one_illformed(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("black wins", "W+4.5")
    tc.assertEqual(fx.game.result.sgf_result, "W+4.5")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(),
                   "two beat one W+4.5\n"
                   "one final_score: black wins\n"
                   "two final_score: W+4.5")

def test_players_score_agree_except_margin(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3", "B+4.0")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+4.0")

def test_players_score_agree_one_no_margin(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3", "B+")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+")

def test_players_score_agree_one_illformed_margin(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+3", "B+a")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+a")

def test_players_score_agree_margin_zero(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("b+0", "B+0")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+0\n"
                   "two final_score: B+0")

def test_players_score_one_scores_illformed(tc):
    fx = Game_fixture(tc)
    fx.run_score_test(None, "B+X")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "two final_score: B+X")

def test_players_score_one_scores_negative(tc):
    fx = Game_fixture(tc)
    fx.run_score_test(None, "B+-3")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "two final_score: B+-3")



def test_resign(tc):
    moves = [
        ('b', 'C3'), ('w', 'D3'),
        ('b', 'resign'),
        ]
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "W+R")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertFalse(fx.game.result.is_forfeit)
    tc.assertIs(fx.game.result.detail, None)
    tc.assertEqual(fx.game.result.describe(), "two beat one W+R")
    fx.check_moves(moves[:-1])

def test_claim(tc):
    def handle_genmove_ex_b(args):
        tc.assertIn('claim', args)
        if fx.player_b.row_to_play < 3:
            return fx.player_b.handle_genmove(args)
        return "claim"
    def handle_genmove_ex_w(args):
        return "claim"
    fx = Game_fixture(tc)
    fx.engine_b.add_command('gomill-genmove_ex', handle_genmove_ex_b)
    fx.engine_w.add_command('gomill-genmove_ex', handle_genmove_ex_w)
    fx.game.set_claim_allowed('b')
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "claim")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertFalse(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.describe(), "one beat two B+ (claim)")
    tc.assertEqual(fx.game.describe_scoring(), "one beat two B+ (claim)")
    fx.check_moves([
        ('b', 'E1'), ('w', 'G1'),
        ('b', 'E2'), ('w', 'G2'),
        ('b', 'E3'), ('w', 'G3'),
        ])

def test_forfeit_occupied_point(tc):
    moves = [
        ('b', 'C3'), ('w', 'D3'),
        ('b', 'D4'), ('w', 'D4'), # occupied point
        ]
    black_player = Programmed_player(moves)
    white_player = Programmed_player(moves)
    fx = Game_fixture(tc, black_player, white_player)
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: two attempted move to occupied point d4")
    tc.assertEqual(fx.game.result.describe(),
                   "one beat two B+F "
                   "(forfeit: two attempted move to occupied point d4)")
    fx.check_moves(moves[:-1])
    tc.assertEqual(black_player.seen_played, ['D3'])

def test_forfeit_simple_ko(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'),
        ('b', 'D4'), ('w', 'E6'),
        ('b', 'E5'), ('w', 'D5'),
        ('b', 'E5'), # ko violation
        ]
    black_player = Programmed_player(moves)
    white_player = Programmed_player(moves)
    fx = Game_fixture(tc, black_player, white_player)
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: one attempted move to ko-forbidden point e5")
    fx.check_moves(moves[:-1])
    tc.assertEqual(white_player.seen_played, ['C5', 'D6', 'D4', 'E5'])

def test_forfeit_illformed_move(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'Z99'), # ill-formed move
        ]
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: two attempted ill-formed move z99")
    fx.check_moves(moves[:-1])

def test_forfeit_genmove_fails(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'fail'), # GTP failure response
        ]
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: failure response from 'genmove b' to player one:\n"
                   "forced to fail")
    fx.check_moves(moves[:-1])

def test_forfeit_rejected_as_illegal(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'), # will be rejected
        ]
    fx = Game_fixture(tc,
                      Programmed_player(moves, reject=('E4', 'illegal move')),
                      Programmed_player(moves))
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: one claims move e4 is illegal")
    fx.check_moves(moves[:-1])

def test_forfeit_play_failed(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'), # will be rejected
        ]
    fx = Game_fixture(tc,
                      Programmed_player(moves, reject=('E4', 'crash')),
                      Programmed_player(moves))
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertTrue(fx.game.result.is_forfeit)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: failure response from 'play w e4' to player one:\n"
                   "crash")
    fx.check_moves(moves[:-1])

def test_move_limit(tc):
    fx = Game_fixture(tc, move_limit=4)
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "Void")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertEqual(fx.game.result.detail, "hit move limit")
    fx.check_moves([
        ('b', 'E1'), ('w', 'G1'),
        ('b', 'E2'), ('w', 'G2'),
        ])

def test_move_limit_exact(tc):
    fx = Game_fixture(tc, move_limit=20)
    fx.game.use_internal_scorer()
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+18")
    fx.check_moves([
        ('b', 'E1'), ('w', 'G1'),
        ('b', 'E2'), ('w', 'G2'),
        ('b', 'E3'), ('w', 'G3'),
        ('b', 'E4'), ('w', 'G4'),
        ('b', 'E5'), ('w', 'G5'),
        ('b', 'E6'), ('w', 'G6'),
        ('b', 'E7'), ('w', 'G7'),
        ('b', 'E8'), ('w', 'G8'),
        ('b', 'E9'), ('w', 'G9'),
        ('b', 'pass'), ('w', 'pass'),
        ])

def test_same_player_code(tc):
    game = gtp_games.Game(board_size=9, komi=0)
    game.set_player_code('b', 'one')
    tc.assertRaisesRegexp(ValueError, "player codes must be distinct",
                          game.set_player_code, 'w', 'one')


def test_make_sgf(tc):
    fx = Game_fixture(tc)
    fx.game.use_internal_scorer()
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]RE[B+18]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+18]W[tt])
""")
    tc.assertMultiLineEqual(gomill_test_support.scrub_sgf(
        fx.game.make_sgf(game_end_message="zzzz").serialise(wrap=None)), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]RE[B+18]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+18

zzzz]W[tt])
""")

def test_make_sgf_scoring_details(tc):
    fx = Game_fixture(tc)
    fx.run_score_test("B+3", "B+4")
    fx.game.close_players()
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]RE[B+]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+ (unknown margin)
one final_score: B+3
two final_score: B+4]W[tt])
""")

def test_game_id(tc):
    fx = Game_fixture(tc)
    fx.game.use_internal_scorer()
    fx.game.set_game_id("gitest")
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.game_id, "gitest")
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]GN[gitest]KM[0]RE[B+18]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+18]W[tt])
""")

def test_explain_last_move(tc):
    counter = [0]
    def handle_explain_last_move(args):
        counter[0] += 1
        return "EX%d" % counter[0]
    fx = Game_fixture(tc)
    fx.engine_b.add_command('gomill-explain_last_move',
                            handle_explain_last_move)
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]RE[?]SZ[9];B[ei]C[EX1];W[gi];B[eh]C[EX2];W[gh];B[eg]C[EX3];W[gg];B[ef]C[EX4];W[gf];B[ee]C[EX5];W[ge];B[ed]C[EX6];W[gd];B[ec]C[EX7];W[gc];B[eb]C[EX8];W[gb];B[ea]C[EX9];W[ga];B[tt]C[EX10];C[one vs two ? (no score reported)]W[tt])
""")


def test_fixed_handicap(tc):
    fh_calls = []
    def handle_fixed_handicap(args):
        fh_calls.append(args[0])
        return "C3 G7 C7"
    fx = Game_fixture(tc)
    fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap)
    fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap)
    fx.game.ready()
    fx.game.set_handicap(3, is_free=False)
    tc.assertEqual(fh_calls, ["3", "3"])
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: two attempted move to occupied point g7")
    fx.check_moves([
        ('w', 'G1'), ('b', 'E1'),
        ('w', 'G2'), ('b', 'E2'),
        ('w', 'G3'), ('b', 'E3'),
        ('w', 'G4'), ('b', 'E4'),
        ('w', 'G5'), ('b', 'E5'),
        ('w', 'G6'), ('b', 'E6'),
        ])
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AB[cc][cg][gc]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]HA[3]KM[0]RE[B+F]SZ[9];W[gi];B[ei];W[gh];B[eh];W[gg];B[eg];W[gf];B[ef];W[ge];B[ee];W[gd];B[ed]C[one beat two B+F (forfeit: two attempted move to occupied point g7)])
""")

def test_fixed_handicap_bad_engine(tc):
    fh_calls = []
    def handle_fixed_handicap_good(args):
        fh_calls.append(args[0])
        return "g7 c7 c3"
    def handle_fixed_handicap_bad(args):
        fh_calls.append(args[0])
        return "C3 G3 C7" # Should be G7, not G3
    fx = Game_fixture(tc)
    fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap_good)
    fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap_bad)
    fx.game.ready()
    tc.assertRaisesRegexp(
        gtp_controller.BadGtpResponse,
        "^bad response from fixed_handicap command to two: C3 G3 C7$",
        fx.game.set_handicap, 3, is_free=False)

def test_free_handicap(tc):
    fh_calls = []
    def handle_place_free_handicap(args):
        fh_calls.append("P " + str(args))
        return "g6 c6 g4 c4"
    def handle_set_free_handicap(args):
        fh_calls.append("S " + str(args))
        return ""
    fx = Game_fixture(tc)
    fx.engine_b.add_command('place_free_handicap', handle_place_free_handicap)
    fx.engine_w.add_command('set_free_handicap', handle_set_free_handicap)
    fx.game.ready()
    fx.game.set_handicap(4, is_free=True)
    tc.assertEqual(fh_calls, ["P ['4']", "S ['G6', 'C6', 'G4', 'C4']"])
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.detail,
                   "forfeit: two attempted move to occupied point g4")
    fx.check_moves([
        ('w', 'G1'), ('b', 'E1'),
        ('w', 'G2'), ('b', 'E2'),
        ('w', 'G3'), ('b', 'E3'),
        ])
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AB[cd][cf][gd][gf]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]HA[4]KM[0]RE[B+F]SZ[9];W[gi];B[ei];W[gh];B[eh];W[gg];B[eg]C[one beat two B+F (forfeit: two attempted move to occupied point g4)])
""")

def test_free_handicap_bad_engine(tc):
    fh_calls = []
    def handle_place_free_handicap(args):
        fh_calls.append("P " + str(args))
        return "g6 c6 g4 g6"
    fx = Game_fixture(tc)
    fx.engine_b.add_command('place_free_handicap', handle_place_free_handicap)
    fx.game.ready()
    tc.assertRaisesRegexp(
        gtp_controller.BadGtpResponse,
        "^invalid response from place_free_handicap command to one: "
        "duplicate point$",
        fx.game.set_handicap, 4, is_free=True)


handicap_compensation_tests = [
    # test code, has_handicap, handicap_compensation, result
    ('h-no', True, 'no', "B+53"),
    ('h-full', True, 'full', "B+50"),
    ('h-short', True, 'short', "B+51"),
    ('n-no', False, 'no', "W+26"),
    ('n-full', False, 'full', "W+26"),
    ('n-short', False, 'short', "W+26"),
    ]

class Handicap_compensation_TestCase(
        gomill_test_support.Gomill_ParameterisedTestCase):
    test_name = "test_handicap_compensation"
    parameter_names = ('has_handicap', 'hc', 'result')

    def runTest(self):
        def handle_fixed_handicap(args):
            return "D4 K10 D10"
        fx = Game_fixture(self, board_size=13)
        fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap)
        fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap)
        fx.game.use_internal_scorer(handicap_compensation=self.hc)
        fx.game.ready()
        if self.has_handicap:
            fx.game.set_handicap(3, is_free=False)
        fx.game.run()
        fx.game.close_players()
        self.assertEqual(fx.game.result.sgf_result, self.result)

def test_move_callback(tc):
    seen = []
    def see(colour, move, board):
        tc.assertIsInstance(board, boards.Board)
        seen.append("%s %s" % (colour, format_vertex(move)))
    fx = Game_fixture(tc)
    fx.game.set_move_callback(see)
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(",".join(seen),
                   "b E1,w G1,b E2,w G2,b E3,w G3,b E4,w G4,b E5,w G5,b E6,"
                   "w G6,b E7,w G7,b E8,w G8,b E9,w G9,b pass,w pass")
