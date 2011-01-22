"""Domain-independent utility functions for gomill.

This module is designed to be used with 'from gomill_utils import *'.

This is for generic utilities; see gomill_common for Go-specific utility
functions.

"""

from __future__ import division

__all__ = ["format_float", "format_percent", "sanitise_utf8"]

def format_float(f):
    """Format a Python float in a friendly way.

    This is intended for values like komi or win counts, which will be either
    integers or half-integers.

    """
    if f == int(f):
        return str(int(f))
    else:
        return str(f)

def format_percent(n, baseline):
    """Format a ratio as a percentage (showing two decimal places).

    Returns a string.

    Accepts baseline zero and returns '??' or '--'.

    """
    if baseline == 0:
        if n == 0:
            return "--"
        else:
            return "??"
    return "%.2f%%" % (100 * n/baseline)


def sanitise_utf8(s):
    """Ensure an 8-bit string is utf-8.

    s -- 8-bit string (or None)

    Returns the sanitised string. If the string was already valid utf-8, returns
    the same object.

    This replaces bad characters with ascii question marks (I don't want to use
    a unicode replacement character, because if this function is doing anything
    then it's likely that there's a non-unicode setup involved somewhere, so it
    probably wouldn't be helpful).

    """
    if s is None:
        return None
    try:
        u = s.decode("utf-8")
    except UnicodeDecodeError:
        return (s.decode("utf-8", 'replace')
                .replace(u"\ufffd", u"?")
                .encode("utf-8"))
    else:
        return s
