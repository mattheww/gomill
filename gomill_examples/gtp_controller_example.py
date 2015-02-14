"""Simple example of using Gtp_controller to talk to gnugo."""

import sys

from gomill import gtp_controller

def main():
    try:
        channel = gtp_controller.Subprocess_gtp_channel(["gnugo", "--mode=gtp"])
        controller = gtp_controller.Gtp_controller(channel, "gnugo")
        controller.do_command("boardsize", "19")
        controller.do_command("clear_board")
        controller.do_command("komi", "6")
        controller.do_command("play", "B", "D4")
        print controller.do_command("genmove", "W")
        print controller.do_command("showboard")
        controller.close()
    except (gtp_controller.GtpChannelError, gtp_controller.BadGtpResponse), e:
        sys.exit(str(e))

if __name__ == "__main__":
    main()

