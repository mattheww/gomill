"""Tests for gtp_games.py"""

import cPickle as pickle

from gomill import gtp_controller
from gomill import gtp_games
from gomill.gomill_common import format_vertex

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support
from gomill_tests import gtp_engine_fixtures
from gomill_tests.gtp_engine_fixtures import Programmed_player

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Game_fixture(test_framework.Fixture):
    """Fixture managing a Gtp_game.

    Instantiate with the player objects (defaults to a Test_player)

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
    def __init__(self, tc, player_b=None, player_w=None):
        self.tc = tc
        self.board_size = 9
        game = gtp_games.Game(board_size=self.board_size)
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
        game_moves = [(colour, format_vertex(coords))
                      for (colour, coords, comment) in self.game.moves]
        self.tc.assertListEqual(game_moves, expected_moves)


def test_game(tc):
    fx = Game_fixture(tc)
    tc.assertDictEqual(fx.game.players, {'b' : 'one', 'w' : 'two'})
    tc.assertIs(fx.game.get_controller('b'), fx.controller_b)
    tc.assertIs(fx.game.get_controller('w'), fx.controller_w)
    fx.game.use_internal_scorer()
    fx.game.ready()
    tc.assertIsNone(fx.game.result)
    fx.game.run()
    fx.game.close_players()
    tc.assertIsNone(fx.game.describe_late_errors())
    tc.assertEqual(fx.game.result.player_b, 'one')
    tc.assertEqual(fx.game.result.player_w, 'two')
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertEqual(fx.game.result.sgf_result, "B+18")
    tc.assertFalse(fx.game.result.is_forfeit)
    tc.assertIsNone(fx.game.result.detail)
    tc.assertEqual(fx.game.result.describe(), "one beat two B+18")
    result2 = pickle.loads(pickle.dumps(fx.game.result))
    tc.assertEqual(result2.describe(), "one beat two B+18")
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
    fx.game.use_internal_scorer()
    fx.game.set_claim_allowed('b')
    fx.game.ready()
    fx.game.run()
    fx.game.close_players()
    tc.assertEqual(fx.game.result.sgf_result, "B+C")
    tc.assertEqual(fx.game.result.winning_colour, 'b')
    tc.assertEqual(fx.game.result.winning_player, 'one')
    tc.assertFalse(fx.game.result.is_forfeit)
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
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.use_internal_scorer()
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

def test_forfeit_simple_ko(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'E4'),
        ('b', 'D4'), ('w', 'E6'),
        ('b', 'E5'), ('w', 'D5'),
        ('b', 'E5'), # ko violation
        ]
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.use_internal_scorer()
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

def test_forfeit_illformed_move(tc):
    moves = [
        ('b', 'C5'), ('w', 'F5'),
        ('b', 'D6'), ('w', 'Z99'), # ill-formed move
        ]
    fx = Game_fixture(tc, Programmed_player(moves), Programmed_player(moves))
    fx.game.use_internal_scorer()
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
    fx.game.use_internal_scorer()
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

