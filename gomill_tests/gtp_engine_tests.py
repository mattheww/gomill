"""Tests for gtp_engine.py"""

from gomill import gtp_engine

from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_engine(tc):
    def handle_test(args):
        if args:
            return "args: " + " ".join(args)
        else:
            return "test response"

    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('test', handle_test)

    check_engine = gtp_engine_test_support.check_engine
    check_engine(tc, engine, 'test', ['ab', 'cd'], "args: ab cd")

