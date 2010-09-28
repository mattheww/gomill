"""Tests for gtp_proxy.py"""

from gomill_tests import gomill_test_support
from gomill_tests import gtp_controller_test_support

from gomill import gtp_controller
from gomill import gtp_proxy

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

