"""Construct and run the gomill testsuite."""

import sys

from test_framework import unittest2

test_modules = [
    'board_tests',
    'ascii_board_tests',
    ]

def get_test_modules():
    """Import all _tests modules in the specified order.

    Returns a list of module objects.

    """
    result = []
    for name in test_modules:
        dotted_name = "gomill_tests." + name
        __import__(dotted_name)
        result.append(sys.modules[dotted_name])
    return result

def main():
    suite = unittest2.TestSuite()
    for mdl in get_test_modules():
        mdl.make_tests(suite)
    runner = unittest2.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    main()

