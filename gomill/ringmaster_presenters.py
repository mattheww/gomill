"""Live display for ringmasters."""

import os
import sys

class Presenter(object):

    box_names = (
        'screen_report',
        'warnings',
        'status',
        'events',
        )

    def __init__(self):
        self.boxes = {}
        for box in self.box_names:
            self.boxes[box] = []

    def clear(self, box):
        self.boxes[box] = []

    def say(self, box, s):
        self.boxes[box].append(s)

    def refresh(self):
        self.clear_screen()
        for box in self.box_names:
            print "[[%s]]" % box
            print "\n".join(self.boxes[box])
            print

    @staticmethod
    def clear_screen():
        """Try to clear the terminal screen (if stdout is a terminal)."""
        try:
            if os.isatty(sys.stdout.fileno()):
                os.system("clear")
        except StandardError:
            pass

