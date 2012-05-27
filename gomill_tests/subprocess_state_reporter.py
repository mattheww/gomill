"""Fake GTP engine that reports info about cwd and environment.

This is used by gtp_controller_tests.test_subprocess_channel

This mustn't import any gomill or gomill_tests code.

"""
import sys
import os

LOG_FILE = "/home/mjw/kiai/tmp/ssr.log"

def main():
    logfile = open(LOG_FILE, "w")
    def log(s):
        logfile.write(s)
        logfile.flush()
    try:
        sys.stderr.write("subprocess_state_reporter: testing\n")
        # Read the GTP command
        sys.stdin.readline()
        if "--extra-stderr" in sys.argv:
            for i in xrange(500):
                sys.stderr.write("blah\n")
        sys.stdout.write("= cwd: %s\nGOMILL_TEST:%s\n\n" %
                         (os.getcwd(), os.environ.get("GOMILL_TEST")))
    except Exception, e:
        #log(str(e))
        sys.stderr = logfile
        raise

if __name__ == "__main__":
    main()
