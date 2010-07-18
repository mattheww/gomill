"""Support for implementing proxy GTP engines.

That is, engines which implement some or all of their commands by sending them
on to another engine (the _back end_).

"""

from gomill import gtp_controller
from gomill import gtp_engine
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)
from gomill.gtp_engine import GtpError, GtpQuit, GtpFatalError


class BackEndError(StandardError):
    """Difficulty communicating with the back end."""

class Gtp_proxy(object):
    """FIXME

    Public attributes:
      engine     -- Gtp_engine_protocol
      controller -- Gtp_controller_protocol
      channel_id -- string

    The 'engine' attribute is the proxy engine. Initially it supports all the
    commands reported by the back end's 'list_commands'. You can add commands to
    it in the usual way; new commands will override any commands with the same
    names in the back end.

    Sample use:
      proxy = gtp_proxy.Gtp_proxy()
      proxy.set_back_end_subprocss([<command>])
      proxy.engine.add_command(...)
      gtp_engine.run_interactive_gtp_session(proxy.engine)

    """
    def __init__(self):
        self.controller = None
        self.channel_id = None
        self.engine = None

    def _back_end_is_set(self):
        return self.controller is not None

    def set_back_end_controller(self, channel_id, controller):
        """Specify the back end using a Gtp_controller_protocol.

        channel_id -- string
        controller -- Gtp_controller_protocol

        Raises BackEndError if it can't communicate with the back end.

        """
        if self._back_end_is_set():
            raise StandardError("back end already set")
        try:
            response = controller.do_command(channel_id, 'list_commands')
        except GtpProtocolError, e:
            raise BackEndError("back end command isn't speaking GTP\n%s" % e)
        except GtpTransportError, e:
            raise BackEndError(
                "can't communicate with back end command:\n%s" % e)
        # FIXME: What if list_commands isn't supported?
        self.channel_id = channel_id
        self.controller = controller
        # FIXME: Be more lenient in what we accept? Ignore blank lines?
        self.back_end_commands = response.split("\n")
        self._make_engine()

    def set_back_end_subprocess(self, command):
        """Specify the back end as a subprocess.

        command -- list of strings (as for subprocess.Popen)

        Raises BackEndError if it can't communicate with the back end.

        """
        try:
            channel = gtp_controller.Subprocess_gtp_channel(command)
        except GtpTransportError, e:
            # Probably means exec failure
            raise BackEndError("can't launch back end command\n%s" % e)
        controller = gtp_controller.Gtp_controller_protocol()
        controller.add_channel("back-end", channel)
        self.set_back_end_controller('back-end', controller)


    def _make_engine(self):
        """FIXME

        returns a Gtp_engine_protocol

        """
        self.engine = gtp_engine.Gtp_engine_protocol()
        self.engine.add_commands(self._make_back_end_handlers())
        # FIXME: This overrides proxying for the protocol commands, but better
        # not to make proxy handlers in the first place.
        self.engine.add_protocol_commands()

    def _make_back_end_handlers(self):
        """FIXME"""
        result = {}
        for command in self.back_end_commands:
            def handler(args, _command=command):
                return self.pass_command(_command, args)
            result[command] = handler
        return result

    def pass_command(self, command, args):
        """Pass a command to the back end, and return its response.

        This method is intended to be used directly in a command handler. In
        particular, error responses from the back end are reported by raising
        GtpError.

        The response (or error response) is unchanged, except for whitespace
        normalisation.

        This passes the command to the back end even if it isn't included in the
        back end's list_commands output; the back end will presumably return an
        'unknown command' error.

        Raises BackEndError if there is a protocol or transport error
        communicating with the back end.

        FIXME: But if you do that in a handler, it'll just get converted to
        GtpError anyway. Is that what we want?

        """
        if not self._back_end_is_set():
            raise StandardError("back end isn't set")
        try:
            return self.controller.do_command(self.channel_id, command, *args)
        except GtpEngineError, e:
            raise GtpError(str(e))
        except GtpProtocolError, e:
            raise BackEndError(
                "protocol error communicating with back end:\n%s" % e)
        except GtpTransportError, e:
            raise BackEndError("error communicating with back end:\n%s" % e)

    def back_end_has_command(self, command):
        """Say whether the back end supports the specified command.

        This uses known_command, not list_commands.

        """
        if not self._back_end_is_set():
            raise StandardError("back end isn't set")
        # FIXME: What exceptions can this raise?
        return self.controller.known_command(self.channel_id, command)

