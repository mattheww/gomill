"""Construct and run the gomill testsuite."""

import sys
from optparse import OptionParser

test_modules = [
    'utils_tests',
    'common_tests',
    'board_tests',
    'sgf_grammar_tests',
    'sgf_properties_tests',
    'sgf_tests',
    'sgf_moves_tests',
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
    'allplayall_tests',
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

def run_testsuite(module_names, failfast, buffer):
    """Run the gomill testsuite.

    module_names -- names of modules from gomill_tests, or None for all
    failfast     -- bool (stop at first failing test)
    buffer       -- bool (show stderr/stdout only for failing tests)

    Output is to stderr

    """
    try:
        # This gives 'catchbreak' behaviour
        unittest2.signals.installHandler()
    except Exception:
        pass
    if module_names is None:
        modules = get_test_modules()
    else:
        modules = [get_test_module(name) for name in module_names]
    suite = unittest2.TestSuite()
    for mdl in modules:
        mdl.make_tests(suite)
    runner = unittest2.TextTestRunner(failfast=failfast, buffer=buffer)
    runner.run(suite)

def run(argv):
    parser = OptionParser(usage="%prog [options] [module] ...")
    parser.add_option("-f", "--failfast", action="store_true",
                      help="stop after first test")
    parser.add_option("-p", "--nobuffer", action="store_true",
                      help="show stderr/stdout for successful tests")
    (options, args) = parser.parse_args(argv)
    if args:
        module_names = args
        for module_name in module_names:
            if module_name not in test_modules:
                parser.error("unknown module: %s" % module_name)
    else:
        module_names = None
    run_testsuite(module_names, options.failfast, not options.nobuffer)

def import_unittest():
    """Import unittest2 into global scope.

    Raises NameError if it isn't available.

    Call this before using the functions in this module other than main().

    """
    global unittest2
    try:
        from gomill_tests.test_framework import unittest2
    except ImportError, e:
        if hasattr(e, 'unittest2_missing'):
            raise NameError("unittest2")
        raise

def main():
    try:
        import_unittest()
    except NameError:
        sys.exit("gomill_tests: requires either Python 2.7 or "
                 "the 'unittest2' package")
    run(sys.argv[1:])

if __name__ == "__main__":
    main()

