"""Live display for ringmasters."""

import os
import sys

class Box(object):
    def __init__(self, name, heading, limit):
        self.name = name
        self.heading = heading
        self.limit = limit
        self.contents = []

    def layout(self):
        return "\n".join(self.contents[-self.limit:])


class Clearing_presenter(object):

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

class Quiet_presenter(object):

    def clear(self, box):
        pass

    def say(self, box, s):
        if box == 'warnings':
            print >>sys.stderr, s

    def refresh(self):
        pass
