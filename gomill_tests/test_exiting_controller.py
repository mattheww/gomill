"""Test engine behaviour when controller disappears."""

import os
import signal
import subprocess
import sys
import time

from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError

exit_status_by_mode = {
    'noisy' : 1,
    'silent' : 3,
    'sigpipe' : -13,
    }

def run_engine(args):
    if "sigpipe" in args:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def handle_wait(args):
        time.sleep(1)
        return "done waiting"
    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('wait', handle_wait)
    if "silent" in args:
        try:
            gtp_engine.run_interactive_gtp_session(engine)
        except gtp_engine.ControllerDisconnected:
            print >>sys.stderr, "[controller disconnected]"
            sys.exit(3)
    else:
        gtp_engine.run_interactive_gtp_session(engine)


def test_exiting_controller(mode):
    """Test engine behaviour when the controller unexpectedly vanishes.

    mode -- 'noisy', 'silent', 'sigpipe'

    """
    print "\n\n** Starting run in mode %s" % mode
    args = []
    if mode == "sigpipe":
        args.append("sigpipe")
    elif mode == "silent":
        args.append("silent")

    p = subprocess.Popen(
        "python gomill_tests/test_exiting_controller.py engine".split() + args,
        close_fds=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get_response():
        while True:
            line = p.stdout.readline()
            sys.stdout.write(line)
            if line == "\n":
                break

    p.stdin.write("list_commands\n")
    get_response()
    p.stdout.close()
    p.stdin.write("wait\n")
    #p.stdout.close() # should work in either place
    p.stdin.close()

    exit_status = p.wait()
    print "exit status was %s" % exit_status
    assert exit_status == exit_status_by_mode[mode]


def main(argv):
    if len(argv) > 1 and sys.argv[1] == "engine":
        run_engine(argv[1:])
    else:
        test_exiting_controller(mode='noisy')
        test_exiting_controller(mode='silent')
        test_exiting_controller(mode='sigpipe')
        print "\nTEST PASSED\n"

if __name__ == "__main__":
    main(sys.argv)
