"""Tests for gtp_proxy.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support

from gomill import gtp_controller
from gomill import gtp_proxy

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def test_proxy(tc):
    channel = gtp_controller_test_support.get_test_channel()
    controller = gtp_controller.Gtp_controller(channel, 'testbackend')
    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_controller(controller)
    tc.assertEqual(
        proxy.engine.run_command('test', ['ab', 'cd']),
        (False, 'args: ab cd', False))
