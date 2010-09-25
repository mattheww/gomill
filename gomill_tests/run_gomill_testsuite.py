import unittest2

from gomill_tests import board_tests

def main():
    suite = unittest2.TestSuite()
    board_tests.make_tests(suite)
    runner = unittest2.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    main()

