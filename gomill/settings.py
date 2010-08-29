"""Support for describing configurable values."""

import re

__all__ = ['Setting', 'allow_none', 'load_settings',
           'interpret_any', 'interpret_bool',
           'interpret_int', 'interpret_positive_int', 'interpret_float',
           'interpret_as_utf8', 'interpret_identifier',
           'interpret_colour', 'interpret_enum', 'interpret_callable']

def interpret_any(v):
    return v

def interpret_bool(b):
    if b is not True and b is not False:
        raise ValueError("invalid True/False value")
    return b

def interpret_int(i):
    if not isinstance(i, int) or isinstance(i, long):
        raise ValueError("invalid integer")
    return i

def interpret_positive_int(i):
    if not isinstance(i, int) or isinstance(i, long):
        raise ValueError("invalid integer")
    if i <= 0:
        raise ValueError("must be positive integer")
    return i

def interpret_float(f):
    if isinstance(f, float):
        return f
    if isinstance(f, int) or isinstance(f, long):
        return float(f)
    raise ValueError("invalid float")

def interpret_as_utf8(s):
    if isinstance(s, str):
        try:
            s.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("not a valid utf-8 string")
        return s
    if isinstance(s, unicode):
        return s.encode("utf-8")
    if s is None:
        return ""
    raise ValueError("invalid string")

# NB, tuners use '#' in player codes
_identifier_re = re.compile(r"\A[-!$%&*+-./:;<=>?^_~a-zA-Z0-9]*\Z")

def interpret_identifier(s):
    if isinstance(s, unicode):
        try:
            s = s.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("contains forbidden character")
    elif not isinstance(s, str):
        raise ValueError("not a string")
    if not s:
        raise ValueError("empty string")
    if not _identifier_re.search(s):
        raise ValueError("contains forbidden character")
    return s

_colour_dict = {
    'b' : 'b',
    'black' : 'b',
    'w' : 'w',
    'white' : 'w',
    }

def interpret_colour(s):
    if isinstance(s, basestring):
        try:
            return _colour_dict[s.lower()]
        except KeyError:
            pass
    raise ValueError("invalid colour")

def interpret_enum(*values):
    def interpreter(value):
        if value not in values:
            raise ValueError("unknown value")
        return value
    return interpreter

def interpret_callable(c):
    if not callable(c):
        raise ValueError("invalid callable")
    return c

def allow_none(fn):
    def sub(v):
        if v is None:
            return None
        return fn(v)
    return sub

_nodefault = object()

class Setting(object):
    """Describe a single setting.

    Instantiate with:
      setting name
      interpreter function
      default value (optional)

    """
    def __init__(self, name, interpreter, default=_nodefault):
        self.name = name
        self.interpreter = interpreter
        if default is _nodefault:
            self.has_default = False
            self.default = None
        else:
            self.has_default = True
            self.default = default

    def interpret(self, value):
        """Validate the value and normalise if necessary.

        Returns the normalised value (usually unchanged).

        Raises ValueError with a description if the value is invalid.

        """
        try:
            return self.interpreter(value)
        except ValueError, e:
            raise ValueError("'%s': %s" % (self.name, e))

def load_settings(settings, config):
    """Read settings values from configuration.

    settings -- list of Settings
    config   -- dict containing the values to be read

    Returns a dict: setting name -> interpreted value

    Applies defaults and

    Raises ValueError if a setting which has no default isn't present in
    'config'.

    Raises ValueError with a description if a value can't be interpreted.

    """
    result = {}
    for setting in settings:
        try:
            v = config[setting.name]
        except KeyError:
            if setting.has_default:
                v = setting.default
            else:
                raise ValueError("'%s' not specified" % setting.name)
        else:
            # May propagate ValueError
            v = setting.interpret(v)
        result[setting.name] = v
    return result

