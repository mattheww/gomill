"""Tests for gtp_games.py"""

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
      game -- Gtp_game

    """
    def __init__(self, tc):
        self.game = gtp_games.Game(board_size=9)
        self.game.set_player_code('b', 'one')
        self.game.set_player_code('w', 'two')
        channel_b = gtp_engine_fixtures.get_test_player_channel()
        channel_w = gtp_engine_fixtures.get_test_player_channel()
        self.game.set_player_controller('b', gtp_controller.Gtp_controller(
            channel_b, 'player one'))
        self.game.set_player_controller('w', gtp_controller.Gtp_controller(
            channel_w, 'player two'))



def test_game(tc):
    fx = Game_fixture(tc)
    tc.assertDictEqual(fx.game.players, {'b' : 'one', 'w' : 'two'})
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
    tc.assertEqual(fx.game.result.detail, None)
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
