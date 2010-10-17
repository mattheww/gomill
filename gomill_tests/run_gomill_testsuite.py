"""Construct and run the gomill testsuite."""

import sys
from optparse import OptionParser

from gomill_tests.test_framework import unittest2

test_modules = [
    'gomill_common_tests',
    'board_tests',
    'sgf_writer_tests',
    'gtp_engine_tests',
    'gtp_state_tests',
    'gtp_controller_tests',
    'gtp_proxy_tests',
    'gtp_game_tests',
    'game_job_tests',
    'setting_tests',
    'competition_scheduler_tests',
    'competition_tests',
    'playoff_tests',
    'mcts_tuner_tests',
    'cem_tuner_tests',
    'ringmaster_tests',
    ]

def get_test_module(name):
    """Import the specified gomill_tests module and return it."""
    dotted_name = "gomill_tests." + name
    __import__(dotted_name)
    return sys.modules[dotted_name]

def get_test_modules():
    """Import all _tests modules in the specified order.

    Returns a list of module objects.

    """
    return [get_test_module(name) for name in test_modules]

def run_testsuite(module_name, failfast, buffer):
    """Run the gomill testsuite.

    module_name -- name of a module from gomill_tests, or None for all
    failfast    -- bool (stop at first failing test)
    buffer      -- bool (show stderr/stdout only for failing tests)

    Output is to stderr

    """
    try:
        # This gives 'catchbreak' behaviour
        unittest2.signals.installHandler()
    except Exception:
        pass
    if module_name is None:
        modules = get_test_modules()
    else:
        modules = [get_test_module(module_name)]
    suite = unittest2.TestSuite()
    for mdl in modules:
        mdl.make_tests(suite)
    runner = unittest2.TextTestRunner(failfast=failfast, buffer=buffer)
    runner.run(suite)

def run(argv):
    parser = OptionParser(usage="%prog [options] [module]")
    parser.add_option("-f", "--failfast", action="store_true",
                      help="stop after first test")
    parser.add_option("-p", "--nobuffer", action="store_true",
                      help="show stderr/stdout for successful tests")
    (options, args) = parser.parse_args(argv)
    if args:
        module_name = args[0]
        if module_name not in test_modules:
            parser.error("unknown module: %s" % module_name)
    else:
        module_name = None
    run_testsuite(module_name, options.failfast, not options.nobuffer)

def main():
    run(sys.argv[1:])

if __name__ == "__main__":
    main()

