"""Organise multiple GTP games.

"""

import sys

def log_to_stdout(s):
    print s

NoGameAvailable = object()

class Competition(object):
    """A resumable processing job based on playing many GTP games.

    FIXME: This is base class for Tournament (and later tuners).

    """
    def __init__(self, competition_code):
        self.competition_code = competition_code
        self.logger = log_to_stdout

    def set_logger(self, logger):
        self.logger = logger

    def log(self, s):
        self.logger(s)
