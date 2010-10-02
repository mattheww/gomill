"""Tests for gtp_engine.py"""

from gomill import gtp_engine

from gomill_tests import gomill_test_support
from gomill_tests import gtp_engine_test_support
from gomill_tests import test_support

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

def test_run_gtp_session(tc):
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()

    stream = "known_command list_commands\nxyzzy\nquit\n"
    command_pipe = test_support.Mock_reading_pipe(stream)
    response_pipe = test_support.Mock_writing_pipe()
    gtp_engine.run_gtp_session(engine, command_pipe, response_pipe)
    tc.assertMultiLineEqual(response_pipe.getvalue(),
                            "= true\n\n? unknown command\n\n=\n\n")
    command_pipe.close()
    response_pipe.close()

