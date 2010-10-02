"""Engines (and channels) provided for the use of controller-side testing."""

import os

from gomill import gomill_common
from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError

from gomill_tests import test_framework
from gomill_tests import gtp_controller_test_support
from gomill_tests.gomill_test_support import SupporterError


## Test engine

class Test_gtp_engine_protocol(gtp_engine.Gtp_engine_protocol):
    """Variant of Gtp_engine_protocol with additional facilities for testing.

    Public attributes:
      commands_handled -- list of pairs (command, args)

    This records all commands sent to the engine and makes them available in the
    commands_handled attribute. It also provides a mechanism to force commands
    to fail.

    """
    def __init__(self):
        gtp_engine.Gtp_engine_protocol.__init__(self)
        self.commands_handled = []

    def run_command(self, command, args):
        self.commands_handled.append((command, args))
        return gtp_engine.Gtp_engine_protocol.run_command(self, command, args)

    def _forced_error(self, args):
        raise GtpError("handler forced to fail")

    def _forced_fatal_error(self, args):
        raise GtpFatalError("handler forced to fail and exit")

    def force_error(self, command):
        """Set the handler for 'command' to report failure."""
        self.add_command(command, self._forced_error)

    def force_fatal_error(self, command):
        """Set the handler for 'command' to report failure and exit."""
        self.add_command(command, self._forced_fatal_error)


def get_test_engine():
    """Return a Gtp_engine_protocol useful for testing controllers.

    Actually returns a Test_gtp_engine_protocol.

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

    engine = Test_gtp_engine_protocol()
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


## Test player engine

class Test_player(object):
    """Trivial player.

    This supports at least the minimal commands required to play a game.

    At present, this plays up column 4 (for black) or 6 (for white), then
    resigns. It pays no attention to its opponent's moves, and doesn't maintain
    a board position.

    """
    def __init__(self):
        self.boardsize = None
        self.row_to_play = 0

    def handle_boardsize(self, args):
        self.boardsize = gtp_engine.interpret_int(args[0])

    def handle_clear_board(self, args):
        pass

    def handle_komi(self, args):
        pass

    def handle_play(self, args):
        pass

    def handle_genmove(self, args):
        colour = gtp_engine.interpret_colour(args[0])
        if self.row_to_play < self.boardsize:
            col = 4 if colour == 'b' else 6
            result = gomill_common.format_vertex((self.row_to_play, col))
            self.row_to_play += 1
            return result
        else:
            return "pass"

    def get_handlers(self):
        return {
            'boardsize'   : self.handle_boardsize,
            'clear_board' : self.handle_clear_board,
            'komi'        : self.handle_komi,
            'play'        : self.handle_play,
            'genmove'     : self.handle_genmove,
            }

def get_test_player_engine():
    """Return a Gtp_engine_protocol based on a Test_player.

    Actually returns a Test_gtp_engine_protocol.

    """
    test_player = Test_player()
    engine = Test_gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands(test_player.get_handlers())
    return engine

def get_test_player_channel():
    """Return a Testing_gtp_channel connected to the test player engine."""
    engine = get_test_player_engine()
    return gtp_controller_test_support.Testing_gtp_channel(engine)


## State reporter subprocess

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


## Mock subprocess gtp channel

class Mock_subprocess_gtp_channel(
    gtp_controller_test_support.Testing_gtp_channel):
    """Mock substitute for Subprocess_gtp_channel.

    This has the same construction interface as Subprocess_gtp_channel, but is
    in fact a Testing_gtp_channel.

    Public attributes:
        engine_registry   -- map command name -> Gtp_engine_protocol
        requested_command -- list of strings
        requested_stderr
        requested_cwd
        requested_env

    The underlying engine is specified by the command name (ie, the first item
    of the 'command' list given to Subprocess_gtp_channel):
     - if it's 'test', a new test player engine is created and used
     - otherwise, an engine is looked up in the engine registry
     - if it's not found there, SupporterError is raised

    """
    engine_registry = {}

    def __init__(self, command, stderr=None, cwd=None, env=None):
        self.requested_command = command
        self.requested_stderr = stderr
        self.requested_cwd = cwd
        self.requested_env = env
        if command[0] == 'test':
            engine = get_test_player_engine()
        else:
            try:
                engine = self.engine_registry[command[0]]
            except KeyError:
                raise SupporterError(
                    "Mock_subprocess_gtp_channel: unregistered engine '%s'" %
                    command[0])
        gtp_controller_test_support.Testing_gtp_channel.__init__(self, engine)


class Mock_subprocess_fixture(test_framework.Fixture):
    """Fixture for using Mock_subprocess_gtp_channel.

    While this fixture is active, attempts to instantiate a
    Subprocess_gtp_channel will produce a Testing_gtp_channel.

    Use command name 'test', or a name registered using register_engine()

    """
    def __init__(self, tc):
        self.engine_registry = {}
        self._patch()
        tc.addCleanup(self._unpatch)

    def _patch(self):
        self._sgc = gtp_controller.Subprocess_gtp_channel
        gtp_controller.Subprocess_gtp_channel = Mock_subprocess_gtp_channel

    def _unpatch(self):
        gtp_controller.Subprocess_gtp_channel = self._sgc

    def register_engine(self, name, engine):
        """Specify an engine for a mock subprocess channel to run.

        name   -- string
        engine -- Gtp_engine_protocol

        After this is called, attempts to instantiate a Subprocess_gtp_channel
        with command name 'name' will return a Testing_gtp_channel based on the
        specified engine.

        """
        Mock_subprocess_gtp_channel.engine_registry[name] = engine

