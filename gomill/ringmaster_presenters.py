"""Live display for ringmasters."""

import os
import sys

class Box(object):
    def __init__(self, name, limit):
        self.name = name
        self.limit = limit
        self.contents = []

    def layout(self):
        return "\n".join(self.contents[-self.limit:])


class Presenter(object):

    box_specs = (
        ('status', 999),
        ('screen_report', 999),
        ('warnings', 6),
        ('events', 8),
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
            print "[[%s]]" % box.name
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

