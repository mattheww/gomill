"""Construct and run the gomill testsuite."""

import sys
from optparse import OptionParser

from gomill_tests.test_framework import unittest2

test_modules = [
    'gomill_common_tests',
    'board_tests',
    'sgf_writer_tests',
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

def run_testsuite(failfast, buffer):
    """Run the gomill testsuite.

    failfast -- bool (stop at first failing test)
    buffer   -- bool (show stderr/stdout only for failing tests)

    Output is to stderr

    """
    try:
        # This gives 'catchbreak' behaviour
        unittest2.signals.installHandler()
    except Exception:
        pass
    suite = unittest2.TestSuite()
    for mdl in get_test_modules():
        mdl.make_tests(suite)
    runner = unittest2.TextTestRunner(failfast=failfast, buffer=buffer)
    runner.run(suite)

def run(argv):
    parser = OptionParser()
    parser.add_option("-f", "--failfast", action="store_true",
                      help="stop after first test")
    parser.add_option("--nobuffer", action="store_true",
                      help="show stderr/stdout for successful tests")
    (options, args) = parser.parse_args(argv)
    if args:
        parser.error("too many arguments")
    run_testsuite(options.failfast, not options.nobuffer)

def main():
    run(sys.argv[1:])

if __name__ == "__main__":
    main()

