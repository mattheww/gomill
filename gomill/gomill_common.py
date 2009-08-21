"""Common utility functions for gomill.

This module is designed to be used with 'from gomill_common import *'.

"""

__all__ = ["opponent_of"]

_opponents = {"b":"w", "w":"b"}
def opponent_of(colour):
    """Return the opponent colour.

    colour -- 'b' or 'w'

    Returns 'b' or 'w'.

    """
    try:
        return _opponents[colour]
    except KeyError:
        return ValueError
