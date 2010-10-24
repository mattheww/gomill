"""Run the gomill testsuite against an installed gomill package."""

import imp
import os
import sys

# Remove the distribution directory from sys.path
if os.path.abspath(sys.path[0]) == os.path.abspath(os.path.dirname(__file__)):
    del sys.path[0]

try:
    import gomill
except ImportError:
    sys.exit("test_installed_gomill: can't find the gomill package")

PACKAGE_NAME = "gomill_tests"

# Make gomill_tests importable without the sibling gomill
def _make_newtests():
    dirpath = os.path.abspath(
        os.path.join(os.path.dirname(__file__), PACKAGE_NAME))
    filepath = os.path.join(dirpath, "__init__.py")
    # imp.load_source sets __name__ and __file__
    # __init__.py won't see its own __path__ set, but it doesn't contain any
    # code, so it doesn't matter.
    mdl = imp.load_source(PACKAGE_NAME, filepath)
    assert mdl.__name__ == PACKAGE_NAME
    mdl.__path__ = [dirpath]
    mdl.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = mdl
_make_newtests()

dirname = os.path.abspath(os.path.dirname(gomill.__file__))
print >>sys.stderr, "testing gomill package in %s" % dirname
from gomill_tests import run_gomill_testsuite
run_gomill_testsuite.main()

