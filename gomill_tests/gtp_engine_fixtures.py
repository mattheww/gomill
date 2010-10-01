"""Engines (and channels) provided for the use of controller-side testing."""

import os

from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError

from gomill_tests import test_framework
from gomill_tests import gtp_controller_test_support
from gomill_tests.gomill_test_support import SupporterError


class Recording_gtp_engine_protocol(gtp_engine.Gtp_engine_protocol):
    """Variant of Gtp_engine_protocol that records its commands.

    Public attributes:
      commands_handled -- list of pairs (command, args)

    """
    def __init__(self):
        gtp_engine.Gtp_engine_protocol.__init__(self)
        self.commands_handled = []

    def run_command(self, command, args):
        self.commands_handled.append((command, args))
        return gtp_engine.Gtp_engine_protocol.run_command(self, command, args)


def get_test_engine():
    """Return a Gtp_engine_protocol useful for testing controllers.

    Actually returns a Recording_gtp_engine_protocol.

    """

    def handle_test(args):
        if args:
            return "args: " + " ".join(args)
        else:
            return "test response"

    def handle_multiline(args):
        return "first line  \n  second line\nthird line"

    def handle_error(args):
        raise GtpError("normal error")

    def handle_fatal_error(args):
        raise GtpFatalError("fatal error")

    engine = Recording_gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('test', handle_test)
    engine.add_command('multiline', handle_multiline)
    engine.add_command('error', handle_error)
    engine.add_command('fatal', handle_fatal_error)
    return engine

def get_test_channel():
    """Return a Testing_gtp_channel connected to the test engine."""
    engine = get_test_engine()
    return gtp_controller_test_support.Testing_gtp_channel(engine)


class State_reporter_fixture(test_framework.Fixture):
    """Fixture for use with suprocess_state_reporter.py

    Attributes:
      pathname -- pathname of the state reporter python script
      cmd      -- command list suitable for use with suprocess.Popen
      devnull  -- file open for writing to /dev/null

    """
    def __init__(self, tc):
        self._pathname = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         "subprocess_state_reporter.py"))
        self.cmd = ["python", self._pathname]
        self.devnull = open(os.devnull, "w")
        tc.addCleanup(self.devnull.close)

