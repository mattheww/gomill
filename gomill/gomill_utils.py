"""Domain-independent utility functions for gomill.

This module is designed to be used with 'from gomill_utils import *'.

This is for generic utilities; see gomill_common for Go-specific utility
functions.

"""

__all__ = ["format_float"]

def format_float(f):
    """Format a Python float in a friendly way.

    This is intended for values like komi or win counts, which will be either
    integers or half-integers.

    """
    if f == int(f):
        return str(int(f))
    else:
        return str(f)

