"""FIXME"""

from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)
from gomill.gtp_engine import GtpError, GtpQuit, GtpFatalError

class Gtp_proxy(object):
    """FIXME

    """
    def __init__(self):
        self.controller = None
        self.channel_id = None
        self.client_commands = None

    def set_controller(self, controller, channel_id):
        """FIXME

        controller -- Gtp_controller_protocol
        channel_id -- string

        """
        self.controller = controller
        self.channel_id = channel_id
        # FIXME: Be more lenient in what we accept? Ignore blank lines?
        client_commands = controller.do_command(channel_id, 'list_commands')\
                          .split("\n")
        self.client_commands = client_commands

    def pass_command(self, command, args):
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

    def make_engine(self):
        """FIXME

        returns a Gtp_engine_protocol

        """
        assert self.client_commands is not None
        engine = gtp_engine.Gtp_engine_protocol()
        engine.add_commands(self.get_handlers())
        # FIXME: This overrides proxying for the protocol commands, but better
        # not to make proxy handlers in the first place.
        engine.add_protocol_commands()
        return engine

