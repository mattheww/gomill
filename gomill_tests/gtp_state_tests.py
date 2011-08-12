"""Tests for gtp_state.py."""

from textwrap import dedent

from gomill import boards
from gomill import gtp_engine
from gomill import gtp_states

from gomill_tests import gomill_test_support
from gomill_tests.gtp_engine_test_support import check_engine
from gomill_tests import gtp_state_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

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

    check_engine(tc, engine, 'genmove', ['b'], "pass")

def test_gtp_state(tc):

    def assertHistoryMoveEqual(hm1, hm2, msg=None):
        t1 = (hm1.colour, hm1.coords, hm1.comments, hm1.cookie)
        t2 = (hm2.colour, hm2.coords, hm2.comments, hm2.cookie)
        tc.assertEqual(t1, t2, "History_moves differ")
    tc.addTypeEqualityFunc(gtp_states.History_move, assertHistoryMoveEqual)

    player = gtp_state_test_support.Player()
    gtp_state = gtp_states.Gtp_state(
        move_generator=player.genmove,
        acceptable_sizes=(9, 11, 13, 19))
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands(gtp_state.get_handlers())
    check_engine(tc, engine, 'nonsense', [''], "unknown command",
                 expect_failure=True)

    player.set_next_move("A3", "preprogrammed move 0")
    check_engine(tc, engine, 'genmove', ['b'], "A3")
    game_state = player.last_game_state
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
    check_engine(tc, engine, 'gomill-explain_last_move', [],
                 "preprogrammed move 0")

    check_engine(tc, engine, 'play', ['W', 'A4'], "")
    check_engine(tc, engine, 'komi', ['5.5'], "")
    player.set_next_move("C9")
    check_engine(tc, engine, 'genmove', ['b'], "C9")
    game_state = player.last_game_state
    # gtp_states currently rounds komi to an integer.
    # FIXME: Get rid of this flooring behaviour
    tc.assertEqual(game_state.komi, 5)
    tc.assertEqual(game_state.history_base, boards.Board(9))
    tc.assertEqual(len(game_state.move_history), 2)
    tc.assertEqual(game_state.move_history[0],
                   gtp_states.History_move('b', (2, 0), "preprogrammed move 0"))
    tc.assertEqual(game_state.move_history[1],
                   gtp_states.History_move('w', (3, 0)))

    check_engine(tc, engine, 'genmove', ['b'], "pass")
    check_engine(tc, engine, 'gomill-explain_last_move', [], "")
    check_engine(tc, engine, 'genmove', ['w'], "pass")
    check_engine(tc, engine, 'showboard', [], dedent("""
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

    player.set_next_move_resign()
    check_engine(tc, engine, 'genmove', ['b'], "resign")

    check_engine(tc, engine, 'clear_board', [], "")
    check_engine(tc, engine, 'showboard', [], dedent("""
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
    check_engine(tc, engine, 'boardsize', ['7'], "unacceptable size",
                 expect_failure=True)
    check_engine(tc, engine, 'boardsize', ['11'], "")
    check_engine(tc, engine, 'showboard', [], dedent("""
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

