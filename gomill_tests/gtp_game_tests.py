"""Tests for gtp_games.py"""

from __future__ import with_statement

import cPickle as pickle
from textwrap import dedent

from gomill import boards
from gomill import gtp_controller
from gomill import gtp_games
from gomill import sgf
from gomill.common import format_vertex
from gomill.gtp_controller import GtpChannelError, GtpChannelClosed

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests.gtp_engine_fixtures import Programmed_player

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))
    for t in handicap_compensation_tests:
        suite.addTest(Handicap_compensation_TestCase(*t))


class Gtp_game_fixture(object):
    """Fixture managing a Gtp_game.

    Instantiate with the player objects (defaults to a Test_player).

    Additional keyword arguments are passed on to Gtp_game.

    attributes:
      game            -- Gtp_game
      game_controller -- Game_controller
      controller_b    -- Gtp_controller
      controller_w    -- Gtp_controller
      channel_b       -- Testing_gtp_channel
      channel_w       -- Testing_gtp_channel
      engine_b        -- Test_gtp_engine_protocol
      engine_w        -- Test_gtp_engine_protocol
      player_b        -- player object
      player_w        -- player object

    """
    def __init__(self, tc, player_b=None, player_w=None, **kwargs):
        self.tc = tc
        kwargs.setdefault('board_size', 9)
        game_controller = gtp_controller.Game_controller('one', 'two')
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
        game_controller.set_player_controller('b', controller_b)
        game_controller.set_player_controller('w', controller_w)
        game = gtp_games.Gtp_game(game_controller, **kwargs)
        self.game_controller = game_controller
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
                      for (colour, move, comment) in self.game.get_moves()]
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
        self.game.prepare()
        self.game.run()

    def sgf_string(self):
        return gomill_test_support.scrub_sgf(
            self.game.make_sgf().serialise(wrap=None))

    def sgf_root(self):
        return self.game.make_sgf().get_root()

    def sgf_last_comment(self):
        return self.game.make_sgf().get_last_node().get("C")

    def sgf_moves_and_comments(self):
        def fmt(node):
            try:
                s = node.get("C")
            except KeyError:
                s = "--"
            colour, move = node.get_move()
            return "%s %s: %s" % (colour, format_vertex(move), s)
        return map(fmt, self.game.make_sgf().get_main_sequence())


def test_game(tc):
    fx = Gtp_game_fixture(tc)
    tc.assertIs(fx.game_controller.get_controller('b'), fx.controller_b)
    tc.assertIs(fx.game_controller.get_controller('w'), fx.controller_w)
    fx.game.use_internal_scorer()
    fx.game.prepare()
    tc.assertIsNone(fx.game.game_id)
    tc.assertIsNone(fx.game.result)
    tc.assertIsNone(fx.game.get_game_score())
    fx.game.run()
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertEqual(fx.game.result.player_b, 'one')
    tc.assertEqual(fx.game.result.player_w, 'two')
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.losing_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertEqual(fx.game.result.losing_player, 'two')
    tc.assertEqual(fx.game.result.sgf_result, "B+18")
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertIs(fx.game.result.is_unknown, False)
    tc.assertIsNone(fx.game.result.detail)
    tc.assertIsNone(fx.game.result.game_id)
    tc.assertEqual(fx.game.result.describe(), "one beat two B+18")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one beat two B+18")
    tc.assertEqual(result2.player_b, 'one')
    tc.assertEqual(result2.player_w, 'two')
    tc.assertIs(result2.is_jigo, False)
    tc.assertDictEqual(fx.game.result.cpu_times, {'one' : None, 'two' : None})
    game_score = fx.game.get_game_score()
    tc.assertIsInstance(game_score, gtp_games.Gtp_game_score)
    tc.assertEqual(game_score.winner, 'b')
    tc.assertEqual(game_score.margin, 18)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : None})
    tc.assertIsNone(game_score.get_detail())
    tc.assertEqual(fx.game.describe_scoring(), "one beat two B+18")
    tc.assertListEqual(fx.game.get_moves(), [
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
        ('name', []),
        ('version', []),
        ('known_command', ['gomill-describe_engine']),
        ('boardsize', ['9']),
        ('clear_board', []),
        ('komi', ['0.0']),
        ('genmove', ['b']),
        ('known_command', ['gomill-explain_last_move']),
        ('play', ['w', 'G1']),
        ('genmove', ['b']),
        ('play', ['w', 'G2']),
        ('genmove', ['b']),
        ('play', ['w', 'G3']),
        ('genmove', ['b']),
        ('play', ['w', 'G4']),
        ('genmove', ['b']),
        ('play', ['w', 'G5']),
        ('genmove', ['b']),
        ('play', ['w', 'G6']),
        ('genmove', ['b']),
        ('play', ['w', 'G7']),
        ('genmove', ['b']),
        ('play', ['w', 'G8']),
        ('genmove', ['b']),
        ('play', ['w', 'G9']),
        ('genmove', ['b']),
        ('play', ['w', 'pass']),
        ('known_command', ['gomill-cpu_time']),
        ])
    tc.assertEqual(fx.engine_w.commands_handled, [
        ('protocol_version', []),
        ('name', []),
        ('version', []),
        ('known_command', ['gomill-describe_engine']),
        ('boardsize', ['9']),
        ('clear_board', []),
        ('komi', ['0.0']),
        ('play', ['b', 'E1']),
        ('genmove', ['w']),
        ('known_command', ['gomill-explain_last_move']),
        ('play', ['b', 'E2']),
        ('genmove', ['w']),
        ('play', ['b', 'E3']),
        ('genmove', ['w']),
        ('play', ['b', 'E4']),
        ('genmove', ['w']),
        ('play', ['b', 'E5']),
        ('genmove', ['w']),
        ('play', ['b', 'E6']),
        ('genmove', ['w']),
        ('play', ['b', 'E7']),
        ('genmove', ['w']),
        ('play', ['b', 'E8']),
        ('genmove', ['w']),
        ('play', ['b', 'E9']),
        ('genmove', ['w']),
        ('play', ['b', 'pass']),
        ('genmove', ['w']),
        ('known_command', ['gomill-cpu_time']),
        ])

def test_unscored_game(tc):
    fx = Gtp_game_fixture(tc)
    tc.assertIs(fx.game_controller.get_controller('b'), fx.controller_b)
    tc.assertIs(fx.game_controller.get_controller('w'), fx.controller_w)
    fx.game.allow_scorer('b') # it can't score
    fx.game.prepare()
    fx.game.run()
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertIsNone(fx.game.result.losing_colour)
    tc.assertIsNone(fx.game.result.winning_player)
    tc.assertIsNone(fx.game.result.losing_player)
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertIs(fx.game.result.is_unknown, True)
    tc.assertEqual(fx.game.result.detail, "no score reported")
    tc.assertEqual(fx.game.result.describe(),
                   "one vs two ? (no score reported)")
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (no score reported)")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one vs two ? (no score reported)")
    tc.assertIs(result2.is_jigo, False)
    game_score = fx.game.get_game_score()
    tc.assertIsNone(game_score.winner)
    tc.assertIsNone(game_score.margin)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : None})
    tc.assertEqual(game_score.get_detail(), "no score reported")

def test_jigo(tc):
    fx = Gtp_game_fixture(tc, komi=18.0)
    fx.game.use_internal_scorer()
    fx.game.prepare()
    tc.assertIsNone(fx.game.result)
    fx.game.run()
    tc.assertDictEqual(fx.game.result.players, {'b' : 'one', 'w' : 'two'})
    tc.assertEqual(fx.game.result.player_b, 'one')
    tc.assertEqual(fx.game.result.player_w, 'two')
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertIsNone(fx.game.result.losing_colour)
    tc.assertIsNone(fx.game.result.winning_player)
    tc.assertIsNone(fx.game.result.losing_player)
    tc.assertEqual(fx.game.result.sgf_result, "0")
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.is_jigo, True)
    tc.assertIs(fx.game.result.is_unknown, False)
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.describe(), "one vs two jigo")
    tc.assertEqual(fx.game.describe_scoring(), "one vs two jigo")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one vs two jigo")
    tc.assertEqual(result2.player_b, 'one')
    tc.assertEqual(result2.player_w, 'two')
    tc.assertIs(result2.is_jigo, True)
    game_score = fx.game.get_game_score()
    tc.assertIsNone(game_score.winner)
    tc.assertEqual(game_score.margin, 0)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : None})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_agree(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3", "B+3.0")
    tc.assertEqual(fx.game.result.sgf_result, "B+3")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(), "one beat two B+3")

def test_players_score_agree_draw(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("0", "0")
    tc.assertEqual(fx.game.result.sgf_result, "0")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(), "one vs two jigo")
    game_score = fx.game.get_game_score()
    tc.assertIsNone(game_score.winner)
    tc.assertEqual(game_score.margin, 0)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : '0', 'w' : '0'})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_disagree(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3.0", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+3.0\n"
                   "two final_score: W+4")
    game_score = fx.game.get_game_score()
    tc.assertIsNone(game_score.winner)
    tc.assertIsNone(game_score.margin)
    tc.assertIs(game_score.scorers_disagreed, True)
    tc.assertEqual(game_score.player_scores, {'b' : 'b+3.0', 'w' : "W+4"})
    tc.assertEqual(game_score.get_detail(), "players disagreed")

def test_players_score_disagree_one_no_margin(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+\n"
                   "two final_score: W+4")

def test_players_score_disagree_one_jigo(tc):
    fx = Gtp_game_fixture(tc)
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
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+4", "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "?")
    tc.assertEqual(fx.game.result.detail, "players disagreed")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertEqual(fx.game.describe_scoring(),
                   "one vs two ? (players disagreed)\n"
                   "one final_score: b+4\n"
                   "two final_score: W+4")

def test_players_score_one_unreliable(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3", "W+4", allowed_scorers="w")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")
    game_score = fx.game.get_game_score()
    tc.assertEqual(game_score.winner, 'w')
    tc.assertEqual(game_score.margin, 4)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : "W+4"})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_one_cannot_score(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test(None, "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")
    game_score = fx.game.get_game_score()
    tc.assertEqual(game_score.winner, 'w')
    tc.assertEqual(game_score.margin, 4)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : "W+4"})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_one_fails(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test(Exception, "W+4")
    tc.assertEqual(fx.game.result.sgf_result, "W+4")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(), "two beat one W+4")
    game_score = fx.game.get_game_score()
    tc.assertEqual(game_score.winner, 'w')
    tc.assertEqual(game_score.margin, 4)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : None, 'w' : "W+4"})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_one_illformed(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("black win", "W+4.5")
    tc.assertEqual(fx.game.result.sgf_result, "W+4.5")
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.describe_scoring(),
                   "two beat one W+4.5\n"
                   "one final_score: black win\n"
                   "two final_score: W+4.5")
    game_score = fx.game.get_game_score()
    tc.assertEqual(game_score.winner, 'w')
    tc.assertEqual(game_score.margin, 4.5)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : "black win", 'w' : "W+4.5"})
    tc.assertIsNone(game_score.get_detail())

def test_players_score_agree_except_margin(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3", "B+4.0")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+4.0")
    game_score = fx.game.get_game_score()
    tc.assertEqual(game_score.winner, 'b')
    tc.assertIsNone(game_score.margin)
    tc.assertIs(game_score.scorers_disagreed, False)
    tc.assertEqual(game_score.player_scores, {'b' : "b+3", 'w' : "B+4.0"})
    tc.assertEqual(game_score.get_detail(), "unknown margin")

def test_players_score_agree_one_no_margin(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3", "B+")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+")

def test_players_score_agree_one_illformed_margin(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+3", "B+a")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+3\n"
                   "two final_score: B+a")

def test_players_score_agree_margin_zero(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("b+0", "B+0")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "one final_score: b+0\n"
                   "two final_score: B+0")

def test_players_score_one_scores_illformed(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test(None, "B+X")
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "unknown margin")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.describe_scoring(),
                   "one beat two B+ (unknown margin)\n"
                   "two final_score: B+X")

def test_players_score_one_scores_negative(tc):
    fx = Gtp_game_fixture(tc)
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
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "W+R")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.detail, None)
    tc.assertEqual(fx.game.result.describe(), "two beat one W+R")
    fx.check_moves(moves[:-1])
    tc.assertIsNone(fx.game.get_game_score())

def test_claim(tc):
    def handle_genmove_ex_b(args):
        tc.assertIn('claim', args)
        if fx.player_b.row_to_play < 3:
            return fx.player_b.handle_genmove(args)
        return "claim"
    def handle_genmove_ex_w(args):
        return "claim"
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('gomill-genmove_ex', handle_genmove_ex_b)
    fx.engine_w.add_command('gomill-genmove_ex', handle_genmove_ex_w)
    fx.game.set_claim_allowed('b')
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+")
    tc.assertEqual(fx.game.result.detail, "claim")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertIs(fx.game.result.is_forfeit, False)
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
    fx = Gtp_game_fixture(tc, black_player, white_player)
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by two: attempted move to occupied point D4")
    tc.assertEqual(fx.game.result.describe(),
                   "one beat two B+F "
                   "(forfeit by two: attempted move to occupied point D4)")
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
    fx = Gtp_game_fixture(tc, black_player, white_player)
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by one: attempted move to ko-forbidden point E5")
    fx.check_moves(moves[:-1])
    tc.assertEqual(white_player.seen_played, ['C5', 'D6', 'D4', 'E5'])

def test_forfeit_illformed_move(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'Z99'), # ill-formed move
        ]
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by two: attempted ill-formed move Z99")
    fx.check_moves(moves[:-1])

def test_forfeit_genmove_fails(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'fail'), # GTP failure response
        ]
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(
        fx.game.result.detail,
        "forfeit by one: failure response from 'genmove b' to player one:\n"
        "forced to fail")
    fx.check_moves(moves[:-1])

def test_forfeit_rejected_as_illegal(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'), # will be rejected
        ]
    fx = Gtp_game_fixture(
        tc,
        Programmed_player(moves, reject=('E4', 'illegal move')),
        Programmed_player(moves))
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by two: one claims move E4 is illegal")
    fx.check_moves(moves[:-1])

def test_forfeit_play_failed(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'), # will be rejected
        ]
    fx = Gtp_game_fixture(
        tc,
        Programmed_player(moves, reject=('E4', 'no thanks')),
        Programmed_player(moves))
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "W+F")
    tc.assertEqual(fx.game.result.winning_colour, 'w')
    tc.assertEqual(fx.game.result.winning_player, 'two')
    tc.assertIs(fx.game.result.is_forfeit, True)
    tc.assertEqual(
        fx.game.result.detail,
        "forfeit by one: failure response from 'play w E4' to player one:\n"
        "no thanks")
    fx.check_moves(moves[:-1])

def test_move_limit(tc):
    fx = Gtp_game_fixture(tc, move_limit=4)
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "Void")
    tc.assertIsNone(fx.game.result.winning_colour)
    tc.assertIs(fx.game.result.is_jigo, False)
    tc.assertIs(fx.game.result.is_forfeit, False)
    tc.assertIs(fx.game.result.is_unknown, True)
    tc.assertEqual(fx.game.result.detail, "hit move limit")
    fx.check_moves([
        ('b', 'E1'), ('w', 'G1'),
        ('b', 'E2'), ('w', 'G2'),
        ])
    tc.assertIsNone(fx.game.get_game_score())

def test_move_limit_exact(tc):
    fx = Gtp_game_fixture(tc, move_limit=20)
    fx.game.use_internal_scorer()
    fx.game.prepare()
    fx.game.run()
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

def test_make_sgf(tc):
    class Named_player(gtp_engine_fixtures.Test_player):
        def get_handlers(self):
            handlers = {'name' : lambda args: "blackplayer",
                        'version' : lambda args: "0.9"}
            handlers.update(gtp_engine_fixtures.Test_player.get_handlers(self))
            return handlers
    fx = Gtp_game_fixture(tc, player_b=Named_player())
    fx.game.use_internal_scorer()
    fx.game.prepare()
    fx.game.run()
    tc.assertMultiLineEqual(fx.sgf_string(), """\
(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]PB[blackplayer:0.9]PW[two]RE[B+18]SZ[9];B[ei];W[gi];B[eh];W[gh];B[eg];W[gg];B[ef];W[gf];B[ee];W[ge];B[ed];W[gd];B[ec];W[gc];B[eb];W[gb];B[ea];W[ga];B[tt];C[one beat two B+18]W[tt])
""")

def test_make_sgf_scoring_details(tc):
    fx = Gtp_game_fixture(tc)
    fx.run_score_test("B+3", "B+4")
    tc.assertEqual(fx.sgf_root().get("RE"), "B+")
    tc.assertMultiLineEqual(fx.sgf_last_comment(), dedent("""\
    one beat two B+ (unknown margin)
    one final_score: B+3
    two final_score: B+4"""))

def test_game_id(tc):
    fx = Gtp_game_fixture(tc)
    fx.game.use_internal_scorer()
    fx.game.set_game_id("gitest")
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.game_id, "gitest")
    tc.assertEqual(fx.sgf_root().get("GN"), "gitest")

def test_explain_last_move(tc):
    counter = [0]
    def handle_explain_last_move(args):
        counter[0] += 1
        return "EX%d" % counter[0]
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('gomill-explain_last_move',
                            handle_explain_last_move)
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.sgf_moves_and_comments(), [
        "None pass: --",
        "b E1: EX1",
        "w G1: --",
        "b E2: EX2",
        "w G2: --",
        "b E3: EX3",
        "w G3: --",
        "b E4: EX4",
        "w G4: --",
        "b E5: EX5",
        "w G5: --",
        "b E6: EX6",
        "w G6: --",
        "b E7: EX7",
        "w G7: --",
        "b E8: EX8",
        "w G8: --",
        "b E9: EX9",
        "w G9: --",
        "b pass: EX10",
        "w pass: one vs two ? (no score reported)",
        ])


def test_fixed_handicap(tc):
    fh_calls = []
    def handle_fixed_handicap(args):
        fh_calls.append(args[0])
        return "C3 G7 C7"
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap)
    fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap)
    fx.game.prepare()
    fx.game.set_handicap(3, is_free=False)
    tc.assertEqual(fh_calls, ["3", "3"])
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by two: attempted move to occupied point G7")
    fx.check_moves([
        ('w', 'G1'), ('b', 'E1'),
        ('w', 'G2'), ('b', 'E2'),
        ('w', 'G3'), ('b', 'E3'),
        ('w', 'G4'), ('b', 'E4'),
        ('w', 'G5'), ('b', 'E5'),
        ('w', 'G6'), ('b', 'E6'),
        ])
    root = fx.sgf_root()
    tc.assertEqual(root.get("HA"), 3)
    tc.assertItemsEqual(map(format_vertex, root.get("AB")), ["C3", "G7", "C7"])
    tc.assertFalse(root.has_property("AW"))
    tc.assertFalse(root.has_property("AE"))

def test_fixed_handicap_bad_engine(tc):
    fh_calls = []
    def handle_fixed_handicap_good(args):
        fh_calls.append(args[0])
        return "g7 c7 c3"
    def handle_fixed_handicap_bad(args):
        fh_calls.append(args[0])
        return "C3 G3 C7" # Should be G7, not G3
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap_good)
    fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap_bad)
    fx.game.prepare()
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
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('place_free_handicap', handle_place_free_handicap)
    fx.engine_w.add_command('set_free_handicap', handle_set_free_handicap)
    fx.game.prepare()
    fx.game.set_handicap(4, is_free=True)
    tc.assertEqual(fh_calls, ["P ['4']", "S ['G6', 'C6', 'G4', 'C4']"])
    fx.game.run()
    tc.assertEqual(fx.game.result.sgf_result, "B+F")
    tc.assertEqual(fx.game.result.detail,
                   "forfeit by two: attempted move to occupied point G4")
    fx.check_moves([
        ('w', 'G1'), ('b', 'E1'),
        ('w', 'G2'), ('b', 'E2'),
        ('w', 'G3'), ('b', 'E3'),
        ])
    root = fx.sgf_root()
    tc.assertEqual(root.get("HA"), 4)
    tc.assertItemsEqual(map(format_vertex, root.get("AB")),
                        ['G6', 'C6', 'G4', 'C4'])
    tc.assertFalse(root.has_property("AW"))
    tc.assertFalse(root.has_property("AE"))

def test_free_handicap_bad_engine(tc):
    fh_calls = []
    def handle_place_free_handicap(args):
        fh_calls.append("P " + str(args))
        return "g6 c6 g4 g6"
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('place_free_handicap', handle_place_free_handicap)
    fx.game.prepare()
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
        fx = Gtp_game_fixture(self, board_size=13)
        fx.engine_b.add_command('fixed_handicap', handle_fixed_handicap)
        fx.engine_w.add_command('fixed_handicap', handle_fixed_handicap)
        fx.game.use_internal_scorer(handicap_compensation=self.hc)
        fx.game.prepare()
        if self.has_handicap:
            fx.game.set_handicap(3, is_free=False)
        fx.game.run()
        self.assertEqual(fx.game.result.sgf_result, self.result)

def test_move_callback(tc):
    seen = []
    def see(colour, move, board):
        tc.assertIsInstance(board, boards.Board)
        seen.append("%s %s" % (colour, format_vertex(move)))
    fx = Gtp_game_fixture(tc)
    fx.game.set_move_callback(see)
    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(",".join(seen),
                   "b E1,w G1,b E2,w G2,b E3,w G3,b E4,w G4,b E5,w G5,b E6,"
                   "w G6,b E7,w G7,b E8,w G8,b E9,w G9,b pass,w pass")

def test_gtp_cpu_time(tc):
    def handle_cpu_time_good(args):
        return "99.5"
    def handle_cpu_time_bad(args):
        return "nonsense"
    fx = Gtp_game_fixture(tc)
    fx.engine_b.add_command('gomill-cpu_time', handle_cpu_time_good)
    fx.engine_w.add_command('gomill-cpu_time', handle_cpu_time_bad)
    fx.game.prepare()
    fx.game.run()
    fx.game_controller.close_players()
    tc.assertDictEqual(fx.game.result.cpu_times, {'one' : 99.5, 'two' : None})
    tc.assertEqual(fx.game.cpu_time_errors, set(['w']))
    tc.assertIsNone(fx.game_controller.describe_late_errors())

def test_gtp_cpu_time_fail(tc):
    fx = Gtp_game_fixture(tc)
    fx.engine_b.force_error('gomill-cpu_time')
    fx.engine_w.force_fatal_error('gomill-cpu_time')
    fx.game.prepare()
    fx.game.run()
    fx.game_controller.close_players()
    tc.assertDictEqual(fx.game.result.cpu_times, {'one' : None, 'two' : None})
    tc.assertEqual(fx.game.cpu_time_errors, set(['b', 'w']))
    tc.assertEqual(fx.game_controller.describe_late_errors(),
                   "error sending 'quit' to player two:\n"
                   "engine has closed the command channel")

def test_game_result_cpu_time_pickle_compatibility(tc):
    fx = Gtp_game_fixture(tc)
    fx.game.prepare()
    fx.game.run()
    result = fx.game.result
    result.cpu_times = {'one' : 33.5, 'two' : '?'}
    result2 = pickle.loads(pickle.dumps(result))
    tc.assertEqual(result2.cpu_times, {'one' : 33.5, 'two' : None})


def test_cautious_mode_setting(tc):
    fx = Gtp_game_fixture(tc)
    fx.game_controller.set_cautious_mode(True)
    fx.game.prepare()
    tc.assertFalse(fx.game_controller.in_cautious_mode)
    fx.game.run()
    tc.assertTrue(fx.game_controller.in_cautious_mode)
    tc.assertEqual(fx.game.result.detail, "no score reported")

def test_channel_error_from_genmove(tc):
    def trigger_fail_next_genmove():
        fx.channel_b.fail_command = "genmove"
        return 'C3'
    moves = [
        ('b', trigger_fail_next_genmove),
        ('w', 'D3'),
        ('b', 'E3'),
        ]
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))

    fx.game.prepare()
    with tc.assertRaises(GtpChannelError) as ar:
        fx.game.run()
    tc.assertEqual(str(ar.exception),
                   "transport error sending 'genmove b' to player one:\n"
                   "forced failure for send_command_line")
    tc.assertIsNone(fx.game.result)
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'),
        ])

def test_channel_error_genmove_exits(tc):
    moves = [
        ('b', 'C3'),      ('w', 'D3'),
        ('b', 'E3&exit'), ('w', 'F3'),
        ]
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))

    fx.game.prepare()
    with tc.assertRaises(GtpChannelClosed) as ar:
        fx.game.run()
    tc.assertEqual(str(ar.exception),
                   "error sending 'play w F3' to player one:\n"
                   "engine has closed the command channel")
    tc.assertIsNone(fx.game.result)
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'), ('b', 'E3'),
        ])

def test_illegal_move_and_exit(tc):
    # Black returns an illegal move and immediately exits
    class Explaining_player(Programmed_player):
        def get_handlers(self):
            handlers = {'gomill-explain_last_move' : lambda args: "xxx"}
            handlers.update(Programmed_player.get_handlers(self))
            return handlers
    moves = [
        ('b', 'C3'),      ('w', 'D3'),
        ('b', 'D3&exit'),
        ]
    fx = Gtp_game_fixture(
        tc, Explaining_player(moves), Explaining_player(moves))

    # Current behaviour is poor: we should know that Black forfeited.
    # This problem only occurs when gomill-explain_last_move is implemented.
    fx.game.prepare()
    with tc.assertRaises(GtpChannelError) as ar:
        fx.game.run()
    tc.assertEqual(str(ar.exception),
                   "error sending 'gomill-explain_last_move' to player one:\n"
                   "engine has closed the command channel")
    tc.assertIsNone(fx.game.result)
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'),
        ])
    fx.game_controller.close_players()
    tc.assertIsNone(fx.game_controller.describe_late_errors())

def test_pass_and_exit(tc):
    # Black passes and immediately exits; White passes
    moves = [
        ('b', 'C3'),        ('w', 'D3'),
        ('b', 'pass&exit'), ('w', 'pass'),
        ]
    fx = Gtp_game_fixture(
        tc, Programmed_player(moves), Programmed_player(moves))

    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.detail, "no score reported")
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'), ('b', 'pass'), ('w', 'pass'),
        ])
    fx.game_controller.close_players()
    tc.assertEqual(fx.game_controller.describe_late_errors(),
                   "error sending 'play w pass' to player one:\n"
                   "engine has closed the command channel")

def test_reject_second_pass(tc):
    # Black returns an error response from 'play' for a game-ending pass
    moves = [
        ('b', 'C3'),   ('w', 'D3'),
        ('b', 'pass'), ('w', 'pass'),
        ]
    fx = Gtp_game_fixture(
        tc,
        Programmed_player(moves, reject=('pass', "no thanks")),
        Programmed_player(moves))

    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.detail, "no score reported")
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'), ('b', 'pass'), ('w', 'pass'),
        ])

def test_reject_second_pass_as_illegal(tc):
    # Black claims a game-ending pass is illegal
    moves = [
        ('b', 'C3'),   ('w', 'D3'),
        ('b', 'pass'), ('w', 'pass'),
        ]
    fx = Gtp_game_fixture(
        tc,
        Programmed_player(moves, reject=('pass', "illegal move")),
        Programmed_player(moves))

    fx.game.prepare()
    fx.game.run()
    tc.assertEqual(fx.game.result.detail, "no score reported")
    fx.check_moves([
        ('b', 'C3'), ('w', 'D3'), ('b', 'pass'), ('w', 'pass'),
        ])
