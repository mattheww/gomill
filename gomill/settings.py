"""Support for describing configurable values."""

__all__ = ['Setting', 'allow_none',
           'interpret_int', 'interpret_float',
           'interpret_as_utf8', 'interpret_enum']

def interpret_int(i):
    if not isinstance(i, int) or isinstance(i, long):
        raise ValueError("invalid integer")
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

def interpret_enum(*values):
    def interpreter(value):
        if value not in values:
            raise ValueError("unknown value")
        return value
    return interpreter

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
            raise ValueError("%s: %s" % (self.name, e))

