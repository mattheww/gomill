"""Tests for gtp_proxy.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support

from gomill import gtp_controller
from gomill import gtp_proxy

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def _make_proxy():
    channel = gtp_controller_test_support.get_test_channel()
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_controller(controller)
    return proxy

def test_proxy(tc):
    proxy = _make_proxy()
    tc.assertEqual(
        proxy.engine.run_command('test', ['ab', 'cd']),
        (False, 'args: ab cd', False))
    proxy.close()

def test_passthrough(tc):
    proxy = _make_proxy()
    tc.assertEqual(
        proxy.engine.run_command(
            'known_command', ['gomill-passthrough']),
        (False, 'true', False))
    tc.assertEqual(
        proxy.engine.run_command(
            'test', ['ab', 'cd']),
        (False, 'args: ab cd', False))
    tc.assertEqual(
        proxy.engine.run_command(
            'gomill-passthrough', ['known_command', 'gomill-passthrough']),
        (False, 'false', False))
    tc.assertEqual(
        proxy.engine.run_command('gomill-passthrough', []),
        (True, 'invalid arguments', False))

