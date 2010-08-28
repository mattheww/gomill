"""Support for describing configurable values."""

__all__ = ['Setting', 'interpret_float', 'interpret_int', 'interpret_enum']

def interpret_enum(*values):
    def interpreter(value):
        if value not in values:
            raise ValueError("unknown value")
        return value
    return interpreter

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

