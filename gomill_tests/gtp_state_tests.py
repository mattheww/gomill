"""Tests for gtp_state.py."""

from textwrap import dedent

from gomill import boards
from gomill import gtp_engine
from gomill import gtp_states
from gomill.common import format_vertex

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
        self.gtp_state = gtp_state_test_support.Testing_gtp_state(
            move_generator=self.player.genmove,
            acceptable_sizes=(9, 11, 13, 19))
        self.engine = gtp_engine.Gtp_engine_protocol()
        self.engine.add_protocol_commands()
        self.engine.add_commands(self.gtp_state.get_handlers())
        self.tc.addTypeEqualityFunc(
            gtp_states.History_move, self.assertHistoryMoveEqual)

    def assertHistoryMoveEqual(self, hm1, hm2, msg=None):
        t1 = (hm1.colour, hm1.move, hm1.comments, hm1.cookie)
        t2 = (hm2.colour, hm2.move, hm2.comments, hm2.cookie)
        self.tc.assertEqual(t1, t2, "History_moves differ")

    def check_command(self, *args, **kwargs):
        """Check a single GTP command.

        parameters as for gtp_engine_test_support.check_engine()

        """
        gtp_engine_test_support.check_engine(
            self.tc, self.engine, *args, **kwargs)

    def check_board_empty_9(self):
        self.check_command('showboard', [], dedent("""
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

def test_gtp_state(tc):
    fx = Gtp_state_fixture(tc)

    fx.check_command('nonsense', [''], "unknown command",
                     expect_failure=True)
    fx.check_command('protocol_version', [''], "2")

    fx.player.set_next_move("A3", "preprogrammed move 0")
    fx.check_command('genmove', ['B'], "A3")
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
    fx.check_command('genmove', ['B'], "C9")
    game_state = fx.player.last_game_state
    tc.assertEqual(game_state.komi, 5.5)
    tc.assertEqual(game_state.history_base, boards.Board(9))
    tc.assertEqual(len(game_state.move_history), 2)
    tc.assertEqual(game_state.move_history[0],
                   gtp_states.History_move('b', (2, 0), "preprogrammed move 0"))
    tc.assertEqual(game_state.move_history[1],
                   gtp_states.History_move('w', (3, 0)))

    fx.check_command('genmove', ['B'], "pass")
    fx.check_command('gomill-explain_last_move', [], "")
    fx.check_command('genmove', ['W'], "pass")
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
    fx.check_command('genmove', ['B'], "resign")
    fx.check_command('quit', [''], "", expect_end=True)


def test_clear_board_and_boardsize(tc):
    fx = Gtp_state_fixture(tc)
    fx.check_command('play', ['W', 'A4'], "")
    fx.check_command('boardsize', ['7'], "unacceptable size",
                     expect_failure=True)
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  o  .  .  .  .  .  .  .  .
    3  .  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('clear_board', [], "")
    fx.check_board_empty_9()
    fx.check_command('play', ['W', 'A4'], "")
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

def test_play(tc):
    fx = Gtp_state_fixture(tc)
    fx.check_command('play', ['B', "E5"], "")
    fx.check_command('play', ['w', "e4"], "")
    fx.check_command('play', [], "invalid arguments", expect_failure=True)
    fx.check_command('play', ['B'], "invalid arguments", expect_failure=True)
    # additional arguments are ignored (following gnugo)
    fx.check_command('play', ['B', "F4", "E5"], "")
    fx.check_command('play', ['white', "f5"], "")
    fx.check_command('play', ['W', "K3"], "vertex is off board: 'k3'",
                     expect_failure=True)
    fx.check_command('play', ['X', "A4"], "invalid colour: 'X'",
                     expect_failure=True)
    fx.check_command('play', ['BLACK', "e4"], "illegal move",
                     expect_failure=True)
    fx.check_command('play', ['B', "pass"], "")
    fx.check_command('play', ['W', "PASS"], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  #  o  .  .  .
    4  .  .  .  .  o  #  .  .  .
    3  .  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))

def test_komi(tc):
    fx = Gtp_state_fixture(tc)
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, 0.0)
    fx.check_command('komi', ['1'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, 1.0)
    fx.check_command('komi', ['1.0'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, 1.0)
    fx.check_command('komi', ['7.5'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, 7.5)
    fx.check_command('komi', ['-3.5'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, -3.5)
    fx.check_command('komi', ['20000'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, 625.0)
    fx.check_command('komi', ['-20000'], "")
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.komi, -625.0)
    fx.check_command('komi', ['nonsense'], "invalid float: 'nonsense'",
                     expect_failure=True)
    fx.check_command('komi', ['NaN'], "invalid float: 'NaN'",
                     expect_failure=True)
    fx.check_command('komi', ['inf'], "invalid float: 'inf'",
                     expect_failure=True)
    fx.check_command('komi', ['-1e400'], "invalid float: '-1e400'",
                     expect_failure=True)

def test_undo(tc):
    fx = Gtp_state_fixture(tc)
    fx.player.set_next_move("A3", "preprogrammed move A3")
    fx.check_command('genmove', ['B'], "A3")
    fx.check_command('gomill-explain_last_move', [], "preprogrammed move A3")
    fx.check_command('play', ['W', 'A4'], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  o  .  .  .  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('undo', [], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.player.set_next_move("D4", "preprogrammed move D4")
    fx.check_command('genmove', ['W'], "D4")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  o  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('gomill-explain_last_move', [], "preprogrammed move D4")
    fx.check_command('undo', [], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('gomill-explain_last_move', [], "preprogrammed move A3")
    fx.check_command('undo', [], "")
    fx.check_board_empty_9()
    fx.check_command('gomill-explain_last_move', [], "")
    fx.check_command('undo', [], "cannot undo", expect_failure=True)

def test_fixed_handicap(tc):
    fx = Gtp_state_fixture(tc)
    fx.check_command('fixed_handicap', ['3'], "C3 G7 C7")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  #  .  .  .  #  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  #  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.handicap, 3)
    fx.check_command('boardsize', ['19'], "")
    fx.check_command('fixed_handicap', ['7'], "D4 Q16 D16 Q4 D10 Q10 K10")
    fx.check_command('fixed_handicap', ['7'], "board not empty",
                     expect_failure=True)
    fx.check_command('boardsize', ['9'], "")
    fx.check_command('play', ['B', 'B2'], "")
    fx.check_command('fixed_handicap', ['2'], "board not empty",
                     expect_failure=True)
    fx.check_command('clear_board', [], "")
    fx.check_command('fixed_handicap', ['0'], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('fixed_handicap', ['1'], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('fixed_handicap', ['10'], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('fixed_handicap', ['2.5'], "invalid int: '2.5'",
                     expect_failure=True)
    fx.check_command('fixed_handicap', [], "invalid arguments",
                     expect_failure=True)

def test_place_free_handicap(tc):
    # See gtp_state_test_support.Testing_gtp_state for description of the choice
    # of points.
    fx = Gtp_state_fixture(tc)
    fx.check_command('place_free_handicap', ['3'], "C3 G7 C7")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  #  .  .  .  #  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  #  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.handicap, 3)
    fx.check_command('boardsize', ['19'], "")
    fx.check_command('place_free_handicap', ['7'], "D4 Q16 D16 Q4 D10 Q10 K10")
    fx.check_command('place_free_handicap', ['7'], "board not empty",
                     expect_failure=True)
    fx.check_command('boardsize', ['9'], "")
    fx.check_command('play', ['B', 'B2'], "")
    fx.check_command('place_free_handicap', ['2'], "board not empty",
                     expect_failure=True)
    fx.check_command('clear_board', [], "")
    fx.check_command('place_free_handicap', ['0'], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('place_free_handicap', ['1'], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('place_free_handicap', ['2.5'], "invalid int: '2.5'",
                     expect_failure=True)
    fx.check_command('place_free_handicap', [], "invalid arguments",
                     expect_failure=True)
    fx.check_command('place_free_handicap', ['10'],
                     "C3 G7 C7 G3 C5 G5 E3 E7 E5")
    fx.check_command('clear_board', [''], "")
    fx.check_command('place_free_handicap', ['5'],
                     "A1 A2 A3 A4 A5")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  #  .  .  .  .  .  .  .  .
    4  #  .  .  .  .  .  .  .  .
    3  #  .  .  .  .  .  .  .  .
    2  #  .  .  .  .  .  .  .  .
    1  #  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('clear_board', [''], "")
    fx.check_command('place_free_handicap', ['6'],
                     "invalid result from move generator: A1,A2,A3,A4,A5,A1",
                     expect_failure=True)
    fx.check_board_empty_9()
    fx.check_command('place_free_handicap', ['2'],
                     "invalid result from move generator: A1,A2,A3",
                     expect_failure=True)
    fx.check_board_empty_9()
    fx.check_command('place_free_handicap', ['4'],
                     "invalid result from move generator: A1,A2,A3,pass",
                     expect_failure=True)
    fx.check_board_empty_9()
    fx.check_command('place_free_handicap', ['8'],
                     "ValueError: need more than 1 value to unpack",
                     expect_internal_error=True)
    fx.check_board_empty_9()

def test_set_free_handicap(tc):
    fx = Gtp_state_fixture(tc)
    fx.check_command('set_free_handicap', ["C3", "E5", "C7"], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  #  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  #  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  #  .  .  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('genmove', ['B'], "pass")
    tc.assertEqual(fx.player.last_game_state.handicap, 3)
    fx.check_command('boardsize', ['9'], "")
    fx.check_command('play', ['B', 'B2'], "")
    fx.check_command('set_free_handicap', ["C3", "E5"], "board not empty",
                     expect_failure=True)
    fx.check_command('clear_board', [], "")
    fx.check_command('set_free_handicap', ["C3"], "invalid number of stones",
                     expect_failure=True)
    fx.check_command('set_free_handicap', [], "invalid number of stones",
                     expect_failure=True)
    all_points = [format_vertex((i, j)) for i in range(9) for j in range(9)]
    fx.check_command('set_free_handicap', all_points,
                     "invalid number of stones", expect_failure=True)
    fx.check_command('set_free_handicap', ["C3", "asdasd"],
                     "invalid vertex: 'asdasd'", expect_failure=True)
    fx.check_board_empty_9()
    fx.check_command('set_free_handicap', ["C3", "pass"],
                     "'pass' not permitted", expect_failure=True)
    fx.check_board_empty_9()
    fx.check_command('set_free_handicap', ["C3", "E5", "C3"],
                     "engine error: C3 is occupied", expect_failure=True)
    fx.check_board_empty_9()


def test_loadsgf(tc):
    fx = Gtp_state_fixture(tc)
    fx.gtp_state._register_file("invalid.sgf", "non-SGF data")
    fx.gtp_state._register_file(
        "test1.sgf",
        "(;SZ[9];B[ee];W[eg];B[dg];W[dh];B[df];W[fh];B[];W[])")
    fx.gtp_state._register_file(
        "test2.sgf",
        "(;SZ[9]AB[fe:ff]AW[gf:gg]PL[W];W[eh];B[ge])")
    fx.check_command('loadsgf', ["unknown.sgf"],
                     "cannot load file", expect_failure=True)
    fx.check_command('loadsgf', ["invalid.sgf"],
                     "cannot load file", expect_failure=True)
    fx.check_command('loadsgf', ["test1.sgf"], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  #  .  .  .  .
    4  .  .  .  #  .  .  .  .  .
    3  .  .  .  #  o  .  .  .  .
    2  .  .  .  o  .  o  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('loadsgf', ["test1.sgf", "4"], "")
    # position _before_ move 4
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  #  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  .  #  o  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('undo', [], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  #  .  .  .  .
    4  .  .  .  .  .  .  .  .  .
    3  .  .  .  .  o  .  .  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('loadsgf', ["test2.sgf"], "")
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  #  #  .  .
    4  .  .  .  .  .  #  o  .  .
    3  .  .  .  .  .  .  o  .  .
    2  .  .  .  .  o  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))
    fx.check_command('undo', [], "")
    fx.check_command('undo', [], "")
    fx.check_command('undo', [], "cannot undo", expect_failure=True)
    fx.check_command('showboard', [], dedent("""
    9  .  .  .  .  .  .  .  .  .
    8  .  .  .  .  .  .  .  .  .
    7  .  .  .  .  .  .  .  .  .
    6  .  .  .  .  .  .  .  .  .
    5  .  .  .  .  .  #  .  .  .
    4  .  .  .  .  .  #  o  .  .
    3  .  .  .  .  .  .  o  .  .
    2  .  .  .  .  .  .  .  .  .
    1  .  .  .  .  .  .  .  .  .
       A  B  C  D  E  F  G  H  J"""))

def test_savesgf(tc):
    scrub_sgf = gomill_test_support.scrub_sgf

    fx = Gtp_state_fixture(tc)
    fx.check_command("play", ['B', 'D4'], "")
    fx.player.set_next_move("C3", "preprogrammed move C3")
    fx.check_command('genmove', ['W'], "C3")
    fx.check_command('gomill-savesgf', ['out1.sgf'], "")
    tc.assertEqual(
        scrub_sgf(fx.gtp_state._load_file('out1.sgf')).replace("\n", ""),
        "(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]"
        "SZ[9];B[df];C[preprogrammed move C3]W[cg])")
    fx.check_command(
        'gomill-savesgf',
        ['out2.sgf', "PB=testplayer", "PW=GNU\_Go:3.8", "RE=W+3.5"],
        "")
    tc.assertEqual(
        scrub_sgf(fx.gtp_state._load_file('out2.sgf')).replace("\n", ""),
        "(;FF[4]AP[gomill:VER]CA[UTF-8]DT[***]GM[1]KM[0]"
        "PB[testplayer]PW[GNU Go:3.8]RE[W+3.5]SZ[9];B[df]"
        ";C[preprogrammed move C3]W[cg])")

    fx.check_command("boardsize", ['19'], "")
    fx.check_command("fixed_handicap", ['3'], "D4 Q16 D16")
    fx.check_command("komi", ['5.5'], "")
    fx.check_command("play", ['W', 'A2'], "")
    fx.check_command('gomill-savesgf', ['out3.sgf'], "")
    tc.assertEqual(
        scrub_sgf(fx.gtp_state._load_file('out3.sgf')).replace("\n", ""),
        "(;FF[4]AB[dd][dp][pd]AP[gomill:VER]CA[UTF-8]DT[***]"
        "GM[1]HA[3]KM[5.5]SZ[19];W[ar])")
    fx.check_command(
        'gomill-savesgf', ['force_fail'],
        "error writing file: [Errno 2] "
        "No such file or directory: '/nonexistent_directory/foo.sgf'",
        expect_failure=True)

def test_get_last_move(tc):
    fx = Gtp_state_fixture(tc)
    fx.player.set_next_move("A3", "preprogrammed move A3")
    fx.check_command('genmove', ['B'], "A3")
    history_moves = fx.player.last_game_state.move_history
    tc.assertEqual(gtp_states.get_last_move(history_moves, 'b'), (False, None))
    tc.assertEqual(gtp_states.get_last_move(history_moves, 'w'), (False, None))

    fx.player.set_next_move("B3", "preprogrammed move B3")
    fx.check_command('genmove', ['W'], "B3")
    history_moves = fx.player.last_game_state.move_history
    tc.assertEqual(gtp_states.get_last_move(history_moves, 'b'), (False, None))
    move_is_available, move = gtp_states.get_last_move(history_moves, 'w')
    tc.assertIs(move_is_available, True)
    tc.assertEqual(format_vertex(move), "A3")

    fx.check_command('genmove', ['B'], "pass")
    history_moves = fx.player.last_game_state.move_history
    move_is_available, move = gtp_states.get_last_move(history_moves, 'b')
    tc.assertIs(move_is_available, True)
    tc.assertEqual(format_vertex(move), "B3")
    tc.assertEqual(gtp_states.get_last_move(history_moves, 'w'), (False, None))

def test_get_last_move_and_cookie(tc):
    fx = Gtp_state_fixture(tc)
    fx.player.set_next_move("A3", "preprogrammed move A3", "COOKIE 1")
    fx.check_command('genmove', ['B'], "A3")
    history_moves = fx.player.last_game_state.move_history
    tc.assertEqual(gtp_states.get_last_move_and_cookie(history_moves, 'b'),
                   (False, None, None))
    tc.assertEqual(gtp_states.get_last_move_and_cookie(history_moves, 'w'),
                   (False, None, None))

    fx.check_command('play', ['W', 'B3'], "")
    fx.check_command('genmove', ['B'], "pass")
    history_moves = fx.player.last_game_state.move_history
    move_is_available, move, cookie = gtp_states.get_last_move_and_cookie(
        history_moves, 'b')
    tc.assertIs(move_is_available, True)
    tc.assertEqual(format_vertex(move), "B3")
    tc.assertIs(cookie, "COOKIE 1")
    tc.assertEqual(gtp_states.get_last_move_and_cookie(history_moves, 'w'),
                   (False, None, None))

