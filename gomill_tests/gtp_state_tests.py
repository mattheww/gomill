"""Tests for gtp_state.py."""

from gomill import gtp_engine
from gomill import gtp_states

from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_state(tc):
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

    check_engine = gtp_engine_test_support.check_engine
    check_engine(tc, engine, 'genmove', ['b'], "pass")

