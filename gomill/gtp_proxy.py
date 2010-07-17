"""Support for implementing proxy GTP engines.

That is, engines which implement some or all of their commands by sending them
on to another engine.

"""

from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)
from gomill.gtp_engine import GtpError, GtpQuit, GtpFatalError

class Gtp_proxy(object):
    """FIXME

    Instantiate with
      channel_id -- string
      controller -- Gtp_controller_protocol
    These define the underlying engine.

    Public attributes:
      channel_id -- string
      controller -- Gtp_controller_protocol
      engine     -- Gtp_engine_protocol

    The 'engine' attribute is the proxy engine. Initially it supports all the
    commands reported by 'list_commands' on the underlying engine. You can add
    commands to it in the usual way; new commands will override any commands
    with the same names in the underlying engine.

    FIXME: Explain proxy.add_command.

    Sample use:
      channel = gtp_controller.Subprocess_gtp_channel([<command>])
      controller = gtp_controller.Gtp_controller_protocol()
      controller.add_channel('sub', channel)
      proxy = gtp_proxy.Gtp_proxy('sub', controller)
      proxy.add_command(...)
      proxy.engine.add_command(...)
      gtp_engine.run_interactive_gtp_session(proxy.engine)

    """
    def __init__(self, channel_id, controller):
        self._set_controller(channel_id, controller)
        self._make_engine()

    def _set_controller(self, channel_id, controller):
        """FIXME

        channel_id -- string
        controller -- Gtp_controller_protocol

        This creates the engine, and sets the controller, channel_id, and engine
        attributes.

        """
        self.channel_id = channel_id
        self.controller = controller
        # FIXME: Be more lenient in what we accept? Ignore blank lines?
        client_commands = controller.do_command(channel_id, 'list_commands')\
                          .split("\n")
        self.client_commands = client_commands

    def _make_engine(self):
        """FIXME

        returns a Gtp_engine_protocol

        """
        assert self.client_commands is not None
        self.engine = gtp_engine.Gtp_engine_protocol()
        self.engine.add_commands(self.get_handlers())
        # FIXME: This overrides proxying for the protocol commands, but better
        # not to make proxy handlers in the first place.
        self.engine.add_protocol_commands()

    def pass_command(self, command, args):
        """FIXME"""
        try:
            return self.controller.do_command(self.channel_id, command, *args)
        except GtpEngineError, e:
            raise GtpError(str(e))
        except GtpProtocolError, e:
            raise GtpError("protocol error:\n%s" % e)
        except GtpTransportError, e:
            raise GtpFatalError("transport error, exiting:\n%s" % e)

    def get_handlers(self):
        """FIXME"""
        result = {}
        for command in self.client_commands:
            def handler(args, _command=command):
                return self.pass_command(_command, args)
            result[command] = handler
        return result

    def add_command(self, command, handler):
        """Register a proxying handler function for a command.

        FIXME: Describe handler requirements: extra argument

        """
        def _handler(args):
            return handler(self, args)
        self.engine.add_command(command, _handler)

    def add_commands(self, handlers):
        """Register multiple proxying handler functions.

        handlers -- dict command name -> handler

        """
        for command, handler in handlers.iteritems():
            self.add_command(command, handler)

