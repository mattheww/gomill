"""Tests for gtp_games.py"""

import cPickle as pickle

from gomill import gtp_controller
from gomill import gtp_games

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_fixtures

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Game_fixture(test_framework.Fixture):
    """Fixture managing a Gtp_game.

    Both players are test player engines.

    attributes:
      game         -- Gtp_game
      controller_b -- Gtp_controller
      controller_w -- Gtp_controller
      channel_b    -- Testing_gtp_channel (like get_test_player_channel())
      channel_w    -- Testing_gtp_channel (like get_test_player_channel())

    """
    def __init__(self, tc):
        game = gtp_games.Game(board_size=9)
        game.set_player_code('b', 'one')
        game.set_player_code('w', 'two')
        channel_b = gtp_engine_fixtures.get_test_player_channel()
        channel_w = gtp_engine_fixtures.get_test_player_channel()
        controller_b = gtp_controller.Gtp_controller(channel_b, 'player one')
        controller_w = gtp_controller.Gtp_controller(channel_w, 'player two')
        game.set_player_controller('b', controller_b)
        game.set_player_controller('w', controller_w)
        self.game = game
        self.controller_b = controller_b
        self.controller_w = controller_w
        self.channel_b = channel_b
        self.channel_w = channel_w



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
