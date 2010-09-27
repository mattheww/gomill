"""Proxy for making mogo a better-behaved GTP engine.

This means the controller sees gomill's GTP implementation, not mogo's.

This makes quarry willing to run mogo, for example.

"""

import sys

from gomill import gtp_engine
from gomill import gtp_proxy

def handle_version(args):
    # Override remarkably verbose version response
    return "2007 public release"

def main(executable):
    try:
        if sys.argv[1] not in ("--9", "--13", "--19"):
            raise ValueError
        size = sys.argv[1][2:]
    except Exception:
        sys.exit("mogo_wrapper: first parameter must be --9, --13, or --19")

    def handle_boardsize(args):
        # No need to pass this down to mogo.
        try:
            if args[0] != size:
                raise gtp_engine.GtpError("board size %s only please" % size)
        except IndexError:
            gtp_engine.report_bad_arguments()

    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_subprocess([executable] + sys.argv[1:])
    proxy.engine.add_command("version", handle_version)
    proxy.engine.add_command("boardsize", handle_boardsize)
    proxy.pass_command("boardsize", [size])
    try:
        proxy.run()
    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == "__main__":
    main("mogo")

