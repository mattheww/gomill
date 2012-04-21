"""Engines (and channels) provided for the use of controller-side testing."""

import os

from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError
from gomill.gtp_controller import GtpChannelError
from gomill.common import *

from gomill_tests import test_framework
from gomill_tests import gtp_controller_test_support
from gomill_tests.test_framework import SupporterError


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
    passes. It pays no attention to its opponent's moves, and doesn't maintain a
    board position.

    (This means that if two Test_players play each other on 9x9, black will win
    by 18 on the board; on 13x13, white will win by 26.)

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
            result = format_vertex((self.row_to_play, col))
            self.row_to_play += 1
            return result
        else:
            return "pass"

    def handle_fail(self, args):
        raise GtpError("test player forced to fail")

    def get_handlers(self):
        return {
            'boardsize'   : self.handle_boardsize,
            'clear_board' : self.handle_clear_board,
            'komi'        : self.handle_komi,
            'play'        : self.handle_play,
            'genmove'     : self.handle_genmove,
            'fail'        : self.handle_fail,
            }

class Programmed_player(object):
    """Player that follows a preset sequence of moves.

    Instantiate with
      moves  -- a sequence of pairs (colour, vertex)
      reject -- pair (vertex, message) [optional]

    The sequence can have moves for both colours; genmove goes through the
    moves in order and ignores ones for the colour that wasn't requested (the
    idea is that you can create two players with the same move list).

    Passes when it runs out of moves.

    If 'vertex' is a tuple, it's interpreted as (row, col) and converted to a
    gtp vertex. The special value 'fail' causes a GtpError. Otherwise it's
    returned literally.

    Public attributes:
      seen_played -- list of the vertices passed to 'play' commands

    If 'reject' is passed, the handler for 'play' raises a GtpError with the
    specified message if it is given the specified vertex.

    """
    def __init__(self, moves, reject=None):
        self.moves = []
        self.seen_played = []
        for colour, vertex in moves:
            if isinstance(vertex, tuple):
                vertex = format_vertex(vertex)
            self.moves.append((colour, vertex))
        self.reject = reject
        self._reset()

    def _reset(self):
        self.iter = iter(self.moves)

    def handle_boardsize(self, args):
        pass

    def handle_clear_board(self, args):
        self._reset()

    def handle_komi(self, args):
        pass

    def handle_play(self, args):
        self.seen_played.append(args[1].upper())
        if self.reject is None:
            return
        vertex, msg = self.reject
        if args[1].lower() == vertex.lower():
            raise GtpError(msg)

    def handle_genmove(self, args):
        colour = gtp_engine.interpret_colour(args[0])
        for move_colour, vertex in self.iter:
            if move_colour == colour:
                if vertex == 'fail':
                    raise GtpError("forced to fail")
                return vertex
        return "pass"

    def get_handlers(self):
        return {
            'boardsize'   : self.handle_boardsize,
            'clear_board' : self.handle_clear_board,
            'komi'        : self.handle_komi,
            'play'        : self.handle_play,
            'genmove'     : self.handle_genmove,
            }


def make_player_engine(player):
    """Return a Gtp_engine_protocol based on a specified player object.

    Actually returns a Test_gtp_engine_protocol.

    It has an additional 'player' attribute, which gives access to the
    player object.

    """
    engine = Test_gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_commands(player.get_handlers())
    engine.player = player
    return engine

def get_test_player_engine():
    """Return a Gtp_engine_protocol based on a Test_player.

    Actually returns a Test_gtp_engine_protocol.

    It has an additional 'player' attribute, which gives access to the
    Test_player.

    """
    return make_player_engine(Test_player())

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

    This accepts the following 'command line arguments' in the 'command' list:
        id=<string>     -- id to use in the channels registry
        engine=<string> -- look up engine in the engine registry
        init=<string>   -- look up initialisation fn in the callback registry
        fail=startup    -- simulate exec failure

    By default, the underlying engine is a newly-created test player engine.
    You can override this using 'engine=xxx'.

    If you want to get at the channel object after creating it, pass 'id=xxx'
    and find it using the 'channels' class attribute.

    If you want to modify the returned channel object, pass 'init=xxx' and
    register a callback function taking a channel parameter.

    Class attributes:
        engine_registry   -- map engine code -> Gtp_engine_protocol
        callback_registry -- map callback code -> function
        channels          -- map id string -> Mock_subprocess_gtp_channel

    Instance attributes:
        id                -- string or None
        requested_command -- list of strings
        requested_stderr
        requested_cwd
        requested_env

    """
    engine_registry = {}
    callback_registry = {}
    channels = {}

    def __init__(self, command, stderr=None, cwd=None, env=None):
        self.requested_command = command
        self.requested_stderr = stderr
        self.requested_cwd = cwd
        self.requested_env = env
        self.id = None
        engine = None
        callback = None
        for arg in command[1:]:
            key, eq, value = arg.partition("=")
            if not eq:
                raise SupporterError("Mock_subprocess_gtp_channel: "
                                     "bad command-line argument: %s" % arg)
            if key == 'id':
                self.id = value
                self.channels[value] = self
            elif key == 'engine':
                try:
                    engine = self.engine_registry[value]
                except KeyError:
                    raise SupporterError(
                        "Mock_subprocess_gtp_channel: unregistered engine '%s'"
                        % value)
            elif key == 'init':
                try:
                    callback = self.callback_registry[value]
                except KeyError:
                    raise SupporterError(
                        "Mock_subprocess_gtp_channel: unregistered init '%s'"
                        % value)
            elif key == 'fail' and value == 'startup':
                raise GtpChannelError("exec forced to fail")
            else:
                raise SupporterError("Mock_subprocess_gtp_channel: "
                                     "bad command-line argument: %s" % arg)

        if engine is None:
            engine = get_test_player_engine()
        gtp_controller_test_support.Testing_gtp_channel.__init__(self, engine)
        if callback is not None:
            callback(self)


class Mock_subprocess_fixture(test_framework.Fixture):
    """Fixture for using Mock_subprocess_gtp_channel.

    While this fixture is active, attempts to instantiate a
    Subprocess_gtp_channel will produce a Testing_gtp_channel.

    """
    def __init__(self, tc):
        self._patch()
        tc.addCleanup(self._unpatch)

    def _patch(self):
        self._sgc = gtp_controller.Subprocess_gtp_channel
        gtp_controller.Subprocess_gtp_channel = Mock_subprocess_gtp_channel

    def _unpatch(self):
        Mock_subprocess_gtp_channel.engine_registry.clear()
        Mock_subprocess_gtp_channel.channels.clear()
        gtp_controller.Subprocess_gtp_channel = self._sgc

    def register_engine(self, code, engine):
        """Specify an engine for a mock subprocess channel to run.

        code   -- string
        engine -- Gtp_engine_protocol

        After this is called, attempts to instantiate a Subprocess_gtp_channel
        with an 'engine=code' argument will return a Testing_gtp_channel based
        on the specified engine.

        """
        Mock_subprocess_gtp_channel.engine_registry[code] = engine

    def register_init_callback(self, code, fn):
        """Specify an initialisation callback for the mock subprocess channel.

        code -- string
        fn   -- function

        After this is called, attempts to instantiate a Subprocess_gtp_channel
        with an 'init=code' argument will call the specified function, passing
        the Testing_gtp_channel as its parameter.

        """
        Mock_subprocess_gtp_channel.callback_registry[code] = fn

    def get_channel(self, id):
        """Retrieve a channel via its 'id' command-line argument."""
        return Mock_subprocess_gtp_channel.channels[id]
