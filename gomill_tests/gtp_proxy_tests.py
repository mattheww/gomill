"""Tests for gtp_proxy.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support

from gomill import gtp_controller
from gomill import gtp_proxy

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def check_engine(tc, engine, command, args, expected,
                 expect_failure=False, expect_end=False):
    """Send a command to an engine and check its response.

    tc             -- testcase
    engine         -- Gtp_engine_protocol
    command        -- gtp command to send
    args           -- list of gtp arguments to send
    expected       -- expected response string
    expect_failure -- expect a GTP failure response
    expect_end     -- expect the engine to report 'end session'

    If the response isn't as expected, uses 'tc' to report this.

    """
    failure, response, end = engine.run_command(command, args)
    if expect_failure:
        tc.assertTrue(failure,
                      "unexpected GTP success response: %s" % response)
    else:
        tc.assertFalse(failure,
                       "unexpected GTP failure response: %s" % response)
    tc.assertEqual(response, expected, "GTP response not as expected")
    if expect_end:
        tc.assertTrue(end, "expected end-session not seen")
    else:
        tc.assertFalse(end, "unexpected end-session")


def _make_proxy():
    channel = gtp_controller_test_support.get_test_channel()
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_controller(controller)
    return proxy

def test_proxy(tc):
    proxy = _make_proxy()
    check_engine(tc, proxy.engine, 'test', ['ab', 'cd'], "args: ab cd")
    proxy.close()

def test_list_commands(tc):
    proxy = _make_proxy()
    tc.assertListEqual(
        proxy.engine.list_commands(),
        ['error', 'fatal', 'gomill-passthrough', 'known_command',
         'list_commands', 'multiline', 'protocol_version', 'quit', 'test'])
    proxy.close()

def test_back_end_has_command(tc):
    proxy = _make_proxy()
    tc.assertTrue(proxy.back_end_has_command('test'))
    tc.assertFalse(proxy.back_end_has_command('xyzzy'))
    tc.assertFalse(proxy.back_end_has_command('gomill-passthrough'))

def test_passthrough(tc):
    proxy = _make_proxy()
    check_engine(tc, proxy.engine,
                 'known_command', ['gomill-passthrough'], "true")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', ['test', 'ab', 'cd'], "args: ab cd")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', ['known_command', 'gomill-passthrough'],
                 "false")
    check_engine(tc, proxy.engine,
                 'gomill-passthrough', [],
                 "invalid arguments", expect_failure=True)

def test_handle_command(tc):
    def handle_xyzzy(args):
        return proxy.handle_command("test", ["nothing", "happens"])
    proxy = _make_proxy()
    proxy.engine.add_command("xyzzy", handle_xyzzy)
    check_engine(tc, proxy.engine, 'xyzzy', [], "args: nothing happens")

