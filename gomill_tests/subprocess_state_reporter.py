"""Fake GTP engine that reports info about cwd and environment.

This is used by gtp_controller_tests.test_subprocess_channel

This mustn't import any gomill or gomill_tests code.

"""
import sys
import os

def main():
    sys.stderr.write("subprocess_state_reporter: testing\n")
    # Read the GTP command
    sys.stdin.readline()
    sys.stdout.write("= cwd: %s\nGOMILL_TEST:%s\n\n" %
                     (os.getcwd(), os.environ.get("GOMILL_TEST")))

if __name__ == "__main__":
    main()
