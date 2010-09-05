"""Live display for ringmasters."""

import os
import sys


class Presenter(object):
    """Abstract base class for presenters.

    This accepts messages on four _channels_, with codes
      warnings
      status
      screen_report
      results

    Some presenters will delay display until refresh() is called; some will
    display them immediately.

    """

    # If this is true, ringmaster needn't bother doing the work to prepare most
    # of the display.
    shows_warnings_only = False

    def clear(self, channel):
        """Clear the contents of the specified channel."""
        raise NotImplementedError

    def say(self, channel, s):
        """Add a message to the specified channel.

        channel -- channel code
        s       -- string to display (no trailing newline)

        """
        raise NotImplementedError

    def refresh(self):
        """Re-render the current screen."""
        raise NotImplementedError


class Quiet_presenter(object):
    """Presenter which shows only warnings.

    Warnings are displayed immediately, and go to stderr.

    """
    shows_warnings_only = True

    def clear(self, channel):
        pass

    def say(self, channel, s):
        if channel == 'warnings':
            print >>sys.stderr, s

    def refresh(self):
        pass


class Box(object):
    """Description of screen layout for the clearing presenter."""
    def __init__(self, name, heading, limit):
        self.name = name
        self.heading = heading
        self.limit = limit
        self.contents = []

    def layout(self):
        return "\n".join(self.contents[-self.limit:])

class Clearing_presenter(object):
    """Low-tech full-screen presenter.

    This shows all channels.

    """

    shows_warnings_only = False

    box_specs = (
        ('status', None, 999),
        ('screen_report', None, 999),
        ('warnings', "Warnings", 6),
        ('results', "Results", 8),
        )

    def __init__(self):
        self.boxes = {}
        self.box_list = []
        for t in self.box_specs:
            box = Box(*t)
            self.boxes[box.name] = box
            self.box_list.append(box)

    def clear(self, box):
        self.boxes[box].contents = []

    def say(self, box, s):
        self.boxes[box].contents.append(s)

    def refresh(self):
        self.clear_screen()
        for box in self.box_list:
            if not box.contents:
                continue
            if box.heading:
                print "= %s = " % box.heading
            print box.layout()
            print

    @staticmethod
    def clear_screen():
        """Try to clear the terminal screen (if stdout is a terminal)."""
        try:
            if os.isatty(sys.stdout.fileno()):
                os.system("clear")
        except StandardError:
            pass

