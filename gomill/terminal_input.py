"""Support for non-blocking terminal input."""

import os

try:
    import termios
except ImportError:
    termios = None

class Terminal_reader(object):
    """Check for input on the controlling terminal."""

    def __init__(self):
        self.enabled = True
        self.tty = None

    def is_enabled(self):
        return self.enabled

    def disable(self):
        self.enabled = False

    def initialise(self):
        if not self.enabled:
            return
        if termios is None:
            self.enabled = False
            return
        try:
            self.tty = open("/dev/tty", "w+")
            # Check this is available
            os.tcgetpgrp(0)
            self.clean_tcattr = termios.tcgetattr(self.tty)
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = self.clean_tcattr
            new_lflag = lflag & (0xffffffff ^ termios.ICANON)
            new_cc = cc[:]
            new_cc[termios.VMIN] = 0
            self.cbreak_tcattr = [
                iflag, oflag, cflag, new_lflag, ispeed, ospeed, new_cc]
        except StandardError:
            self.enabled = False
            return

    def close(self):
        if self.tty is not None:
            self.tty.close()
            self.tty = None

    def stop_was_requested(self):
        """Check whether a 'keyboard stop' instruction has been sent.

        Returns true if ^X has been sent on the controlling terminal.

        Consumes all available input on /dev/tty.

        """
        if not self.enabled:
            return False
        # Don't try to read the terminal if we're in the background.
        # There's a race here, if we're backgrounded just after this check, but
        # I don't see a clean way to avoid it.
        if os.tcgetpgrp(0) != os.getpid():
            return False
        termios.tcsetattr(self.tty, termios.TCSANOW, self.cbreak_tcattr)
        try:
            seen_ctrl_x = False
            while True:
                c = os.read(0, 1)
                if not c:
                    break
                if c == "\x18":
                    seen_ctrl_x = True
        finally:
            termios.tcsetattr(self.tty, termios.TCSANOW, self.clean_tcattr)
        return seen_ctrl_x

    def acknowledge(self):
        """Leave an acknowledgement on the controlling terminal."""
        self.tty.write("\rCtrl-X received; halting\n")
