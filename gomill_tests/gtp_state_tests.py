"""Tests for gtp_state.py."""

from textwrap import dedent

from gomill import boards
from gomill import gtp_engine
from gomill import gtp_states

from gomill_tests import test_framework
from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_test_support
from gomill_tests import gtp_state_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Gtp_state_fixture(test_framework.Fixture):
    """Fixture for managing a Gtp_state.

    The move generator comes from gtp_state_test_support.Player

    Adds a type equality function for History_move.

    """
    def __init__(self, tc):
        self.tc = tc
        self.player = gtp_state_test_support.Player()
        gtp_state = gtp_states.Gtp_state(
            move_generator=self.player.genmove,
            acceptable_sizes=(9, 11, 13, 19))
        self.engine = gtp_engine.Gtp_engine_protocol()
        self.engine.add_protocol_commands()
        self.engine.add_commands(gtp_state.get_handlers())
        self.tc.addTypeEqualityFunc(
            gtp_states.History_move, self.assertHistoryMoveEqual)

    def assertHistoryMoveEqual(self, hm1, hm2, msg=None):
        t1 = (hm1.colour, hm1.coords, hm1.comments, hm1.cookie)
        t2 = (hm2.colour, hm2.coords, hm2.comments, hm2.cookie)
        self.tc.assertEqual(t1, t2, "History_moves differ")

    def check_command(self, *args, **kwargs):
        """Check a single GTP command.

        parameters as for gtp_engine_test_support.check_engine()

        """
        gtp_engine_test_support.check_engine(
            self.tc, self.engine, *args, **kwargs)

def test_simplest_state(tc):
    def genmove(game_state, player):
        result = gtp_states.Move_generator_result()
        result.pass_move = True
        return result

    gtp_state = gtp_states.Gtp_state(
        move_generator=genmove,
        acceptable_sizes=(9, 13, 19))
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands(gtp_state.get_handlers())

    gtp_engine_test_support.check_engine(tc, engine, 'genmove', ['b'], "pass")

def test_gtp_state(tc):
    fx = Gtp_state_fixture(tc)

    fx.check_command('nonsense', [''], "unknown command",
                     expect_failure=True)

    fx.player.set_next_move("A3", "preprogrammed move 0")
    fx.check_command('genmove', ['b'], "A3")
    game_state = fx.player.last_game_state
    # default board size is min(acceptable_sizes)
    tc.assertEqual(game_state.size, 9)
    b = boards.Board(9)
    b.play(2, 0, 'b')
    tc.assertEqual(game_state.board, b)
    tc.assertEqual(game_state.komi, 0.0)
    tc.assertEqual(game_state.history_base, boards.Board(9))
    tc.assertEqual(game_state.move_history, [])
    tc.assertIsNone(game_state.ko_point)
    tc.assertIsNone(game_state.handicap)
    tc.assertIs(game_state.for_regression, False)
    tc.assertIsNone(game_state.time_settings)
    tc.assertIsNone(game_state.time_remaining)
    tc.assertIsNone(game_state.canadian_stones_remaining)
    fx.check_command('gomill-explain_last_move', [], "preprogrammed move 0")

    fx.check_command('play', ['W', 'A4'], "")
    fx.check_command('komi', ['5.5'], "")
    fx.player.set_next_move("C9")
    fx.check_command('genmove', ['b'], "C9")
    game_state = fx.player.last_game_state
    # gtp_states currently rounds komi to an integer.
    # FIXME: Get rid of this flooring behaviour
    tc.assertEqual(game_state.komi, 5)
    tc.assertEqual(game_state.history_base, boards.Board(9))
    tc.assertEqual(len(game_state.move_history), 2)
    tc.assertEqual(game_state.move_history[0],
                   gtp_states.History_move('b', (2, 0), "preprogrammed move 0"))
    tc.assertEqual(game_state.move_history[1],
                   gtp_states.History_move('w', (3, 0)))

    fx.check_command('genmove', ['b'], "pass")
    fx.check_command('gomill-explain_last_move', [], "")
    fx.check_command('genmove', ['w'], "pass")
    fx.check_command('showboard', [], dedent("""
    9  .  .  #  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  o  .  .  .  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))

    fx.player.set_next_move_resign()
    fx.check_command('genmove', ['b'], "resign")

    fx.check_command('clear_board', [], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('boardsize', ['7'], "unacceptable size",
                     expect_failure=True)
    fx.check_command('boardsize', ['11'], "")
    fx.check_command('showboard', [], dedent("""
    11  .  .  .  .  .  .  .  .  .  .  .
    10  .  .  .  .  .  .  .  .  .  .  .
     9  .  .  .  .  .  .  .  .  .  .  .
     8  .  .  .  .  .  .  .  .  .  .  .
     7  .  .  .  .  .  .  .  .  .  .  .
     6  .  .  .  .  .  .  .  .  .  .  .
     5  .  .  .  .  .  .  .  .  .  .  .
     4  .  .  .  .  .  .  .  .  .  .  .
     3  .  .  .  .  .  .  .  .  .  .  .
     2  .  .  .  .  .  .  .  .  .  .  .
     1  .  .  .  .  .  .  .  .  .  .  .
        A  B  C  D  E  F  G  H  J  K  L"""))

