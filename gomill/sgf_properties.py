"""Interpret SGF property values.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

This supports all generic properties and Go-specific properties, but not
properties for other games. Point, Move and Stone values are interpreted as
Go points.

"""

from gomill import sgf_grammar

def decode_point(s, size):
    """Convert a raw SGF Point, Move, or Stone value to coordinates.

    s    -- string
    size -- board size (int)

    Returns a pair (row, col), or None for a pass.

    Raises ValueError if the string is malformed or the coordinates are out of
    range.

    Only supports board sizes up to 26.

    The returned coordinates are in the GTP coordinate system (as in the rest of
    gomill), where (0, 0) is the lower left.

    """
    if s == "" or (s == "tt" and size <= 19):
        return None
    # May propagate ValueError
    col_s, row_s = s
    col = ord(col_s) - 97 # 97 == ord("a")
    row = size - ord(row_s) + 96
    if not ((0 <= col < size) and (0 <= row < size)):
        raise ValueError
    return row, col


class _Context(object):
    def __init__(self, size, encoding):
        self.size = size
        self.encoding = encoding

def interpret_none(s, context=None):
    """Convert a raw None value to a boolean.

    That is, unconditionally returns True.

    """
    return True

def serialise_none(b, context=None):
    """Serialise a None value.

    Ignores its parameter.

    """
    return ""


def interpret_number(s, context=None):
    """Convert a raw Number value to the integer it represents.

    This is a little more lenient than the SGF spec: it permits leading and
    trailing spaces, and spaces between the sign and the numerals.

    """
    return int(s, 10)

def serialise_number(i, context=None):
    """Serialise a Number value.

    i -- integer

    """
    return "%d" % i


def interpret_real(s, context=None):
    """Convert a raw Real value to the float it represents.

    This is more lenient than the SGF spec: it accepts strings accepted as a
    float by the platform libc.

    """
    # Would be nice to at least reject Inf and NaN, but Python 2.5 is deficient
    # here.
    return float(s)

def serialise_real(f, context=None):
    """Serialise a Real value.

    f -- real number (int or float)

    If the value is too small to conveniently express as a decimal, returns "0"
    (this currently happens if f is less than 0.0001).

    """
    f = float(f)
    try:
        i = int(f)
    except OverflowError:
        # infinity
        raise ValueError
    if f == i:
        # avoid trailing '.0'; also avoid scientific notation for large numbers
        return str(i)
    s = repr(f)
    if 'e-' in s:
        return "0"
    return s


def interpret_double(s, context=None):
    """Convert a raw Double value to an integer.

    Returns 1 or 2 (unknown values are treated as 1).

    """
    if s.strip() == "2":
        return 2
    else:
        return 1

def serialise_double(i, context=None):
    """Serialise a Double value.

    i -- integer (1 or 2)

    (unknown values are treated as 1)

    """
    if i == 2:
        return "2"
    return "1"


def interpret_colour(s, context=None):
    """Convert a raw Color value to a gomill colour.

    Returns 'b' or 'w'.

    """
    colour = s.lower()
    if colour not in ('b', 'w'):
        raise ValueError
    return colour

def serialise_colour(colour, context=None):
    """Serialise a Colour value.

    colour -- 'b' or 'w'

    """
    if colour not in ('b', 'w'):
        raise ValueError
    return colour.upper()


def interpret_simpletext(s, context):
    """Convert a raw SimpleText value to a string.

    See sgf_grammar.simpletext_value() for details.

    s -- raw value

    Returns an 8-bit utf-8 string.

    """
    s = sgf_grammar.simpletext_value(s)
    if context.encoding != "UTF-8":
        s = s.decode(context.encoding).encode("utf-8")
    return s

def serialise_simpletext(s, context):
    """Serialise a SimpleText value.

    See sgf_grammar.escape_text() for details.

    s -- 8-bit utf-8 string

    """
    if context.encoding != "UTF-8":
        s = s.decode("utf-8").encode(context.encoding)
    return sgf_grammar.escape_text(s)


def interpret_text(s, context):
    """Convert a raw Text value to a string.

    See sgf_grammar.text_value() for details.

    s -- raw value

    Returns an 8-bit utf-8 string.

    """
    s = sgf_grammar.text_value(s)
    if context.encoding != "UTF-8":
        s = s.decode(context.encoding).encode("utf-8")
    return s

def serialise_text(s, context):
    """Serialise a Text value.

    See sgf_grammar.escape_text() for details.

    s -- 8-bit utf-8 string

    """
    if context.encoding != "UTF-8":
        s = s.decode("utf-8").encode(context.encoding)
    return sgf_grammar.escape_text(s)



def interpret_point(s, context):
    """Convert a raw SGF Point, Move, or Stone value to coordinates.

    See decode_point() above for details.

    Returns a pair (row, col), or None for a pass.

    """
    return decode_point(s, context.size)

def serialise_point(move, context):
    """Serialise a Point, Move, or Stone value.

    move -- pair (row, col), or None for a pass

    The move coordinates are in the GTP coordinate system (as in the rest of
    gomill), where (0, 0) is the lower left.

    Only supports board sizes up to 26.

    """
    size = context.size
    if not 1 <= size <= 26:
        raise ValueError
    if move is None:
        # Prefer 'tt' where possible, for the sake of older code
        if size <= 19:
           return "tt"
        else:
            return ""
    row, col = move
    if not ((0 <= col < size) and (0 <= row < size)):
        raise ValueError
    col_s = "abcdefghijklmnopqrstuvwxy"[col]
    row_s = "abcdefghijklmnopqrstuvwxy"[size - row - 1]
    return col_s + row_s


def interpret_point_list(values, context):
    """Convert a raw SGF list of Points to a set of coordinates.

    values -- list of strings

    Returns a set of pairs (row, col).

    If 'values' is empty, returns an empty set.

    This interprets compressed point lists.

    Doesn't complain if there is overlap, or if a single point is specified as
    a 1x1 rectangle.

    Raises ValueError if the data is otherwise malformed.

    """
    result = set()
    for s in values:
        # No need to use parse_compose(), as \: would always be an error.
        p1, is_rectangle, p2 = s.partition(":")
        if is_rectangle:
            try:
                top, left = interpret_point(p1, context)
                bottom, right = interpret_point(p2, context)
            except TypeError:
                raise ValueError
            if not (bottom <= top and left <= right):
                raise ValueError
            for row in xrange(bottom, top+1):
                for col in xrange(left, right+1):
                    result.add((row, col))
        else:
            pt = interpret_point(p1, context)
            if pt is None:
                raise ValueError
            result.add(pt)
    return result

def serialise_point_list(points, context):
    """Serialise a list of Points, Moves, or Stones.

    points -- iterable of pairs (row, col)

    Returns a list of strings.

    If 'points' is empty, returns an empty list.

    Doesn't produce a compressed point list.

    """
    result = [serialise_point(point, context) for point in points]
    result.sort()
    return result


def interpret_AP(s, context):
    """Interpret an AP (application) property value.

    Returns a pair of strings (name, version number)

    Permits the version number to be missing (which is forbidden by the SGF
    spec), in which case the second returned value is an empty string.

    """
    application, version = sgf_grammar.parse_compose(s)
    if version is None:
        version = ""
    return (interpret_simpletext(application, context),
            interpret_simpletext(version, context))

def serialise_AP(value, context):
    """Serialise an AP (application) property value.

    value -- pair (application, version)
      application -- string
      version     -- string

    Note this takes a single parameter (which is a pair).

    """
    application, version = value
    return sgf_grammar.compose(serialise_simpletext(application, context),
                               serialise_simpletext(version, context))


def interpret_ARLN(values, context):
    """Interpret an AR (arrow) or LN (line) property value.

    Returns a list of pairs (coords, coords).

    """
    result = []
    for s in values:
        p1, p2 = sgf_grammar.parse_compose(s)
        result.append((interpret_point(p1, context),
                       interpret_point(p2, context)))
    return result

def serialise_ARLN(values, context):
    """Serialise an AR (arrow) or LN (line) property value.

    values -- list of pairs (coords, coords)

    """
    return ["%s:%s" % (serialise_point(p1, context),
                       serialise_point(p2, context))
            for p1, p2 in values]


def interpret_FG(s, context):
    """Interpret an FG (figure) property value.

    Returns a pair (flags, string), or None.

    flags is an integer; see http://www.red-bean.com/sgf/properties.html#FG

    """
    if s == "":
        return None
    flags, name = sgf_grammar.parse_compose(s)
    return int(flags), interpret_simpletext(name, context)

def serialise_FG(value, context):
    """Serialise an FG (figure) property value.

    value -- pair (flags, name), or None
      flags -- int
      name  -- string

    Use serialise_FG(None) to produce an empty value.

    """
    if value is None:
        return ""
    flags, name = value
    return "%d:%s" % (flags, serialise_simpletext(name, context))


def interpret_LB(values, context):
    """Interpret an LB (label) property value.

    Returns a list of pairs (coords, string).

    """
    result = []
    for s in values:
        point, label = sgf_grammar.parse_compose(s)
        result.append((interpret_point(point, context),
                       interpret_simpletext(label, context)))
    return result

def serialise_LB(values, context):
    """Serialise an LB (label) property value.

    values -- list of pairs (coords, string)

    """
    return ["%s:%s" % (serialise_point(point, context),
                       serialise_simpletext(text, context))
            for point, text in values]


class Property_type(object):
    """Description of a property type."""
    def __init__(self, value_type, uses_list=False):
        self.interpreter = globals()["interpret_" + value_type]
        self.serialiser = globals()["serialise_" + value_type]
        self.uses_list = bool(uses_list)
        self.allows_empty_list = (uses_list == 'elist')

P = Property_type
LIST = 'list'
ELIST = 'elist'

_property_types_by_ident = {
  'AB' : P('point_list', LIST),             # setup       Add Black
  'AE' : P('point_list', LIST),             # setup       Add Empty
  'AN' : P('simpletext'),                   # game-info   Annotation
  'AP' : P('AP'),                           # root        Application
  'AR' : P('ARLN', LIST),                   # -           Arrow
  'AW' : P('point_list', LIST),             # setup       Add White
  'B'  : P('point'),                        # move        Black
  'BL' : P('real'),                         # move        Black time left
  'BM' : P('double'),                       # move        Bad move
  'BR' : P('simpletext'),                   # game-info   Black rank
  'BT' : P('simpletext'),                   # game-info   Black team
  'C'  : P('text'),                         # -           Comment
  'CA' : P('simpletext'),                   # root        Charset
  'CP' : P('simpletext'),                   # game-info   Copyright
  'CR' : P('point_list', LIST),             # -           Circle
  'DD' : P('point_list', ELIST),            # - (inherit) Dim points
  'DM' : P('double'),                       # -           Even position
  'DO' : P('none'),                         # move        Doubtful
  'DT' : P('simpletext'),                   # game-info   Date
  'EV' : P('simpletext'),                   # game-info   Event
  'FF' : P('number'),                       # root        Fileformat
  'FG' : P('FG'),                           # -           Figure
  'GB' : P('double'),                       # -           Good for Black
  'GC' : P('text'),                         # game-info   Game comment
  'GM' : P('number'),                       # root        Game
  'GN' : P('simpletext'),                   # game-info   Game name
  'GW' : P('double'),                       # -           Good for White
  'HA' : P('number'),                       # game-info   Handicap
  'HO' : P('double'),                       # -           Hotspot
  'IT' : P('none'),                         # move        Interesting
  'KM' : P('real'),                         # game-info   Komi
  'KO' : P('none'),                         # move        Ko
  'LB' : P('LB', LIST),                     # -           Label
  'LN' : P('ARLN', LIST),                   # -           Line
  'MA' : P('point_list', LIST),             # -           Mark
  'MN' : P('number'),                       # move        set move number
  'N'  : P('simpletext'),                   # -           Nodename
  'OB' : P('number'),                       # move        OtStones Black
  'ON' : P('simpletext'),                   # game-info   Opening
  'OT' : P('simpletext'),                   # game-info   Overtime
  'OW' : P('number'),                       # move        OtStones White
  'PB' : P('simpletext'),                   # game-info   Player Black
  'PC' : P('simpletext'),                   # game-info   Place
  'PL' : P('colour'),                       # setup       Player to play
  'PM' : P('number'),                       # - (inherit) Print move mode
  'PW' : P('simpletext'),                   # game-info   Player White
  'RE' : P('simpletext'),                   # game-info   Result
  'RO' : P('simpletext'),                   # game-info   Round
  'RU' : P('simpletext'),                   # game-info   Rules
  'SL' : P('point_list', LIST),             # -           Selected
  'SO' : P('simpletext'),                   # game-info   Source
  'SQ' : P('point_list', LIST),             # -           Square
  'ST' : P('number'),                       # root        Style
  'SZ' : P('number'),                       # root        Size
  'TB' : P('point_list', ELIST),            # -           Territory Black
  'TE' : P('double'),                       # move        Tesuji
  'TM' : P('real'),                         # game-info   Timelimit
  'TR' : P('point_list', LIST),             # -           Triangle
  'TW' : P('point_list', ELIST),            # -           Territory White
  'UC' : P('double'),                       # -           Unclear pos
  'US' : P('simpletext'),                   # game-info   User
  'V'  : P('real'),                         # -           Value
  'VW' : P('point_list', ELIST),            # - (inherit) View
  'W'  : P('point'),                        # move        White
  'WL' : P('real'),                         # move        White time left
  'WR' : P('simpletext'),                   # game-info   White rank
  'WT' : P('simpletext'),                   # game-info   White team
}
private_property = P('text')

del P, LIST, ELIST


class Coder(_Context):
    """Convert property values between Python and SGF-string representations.

    Instantiate with:
      size      -- board size (int)
      encoding  -- encoding for the SGF strings

    """

    def __init__(self, size, encoding):
        self.size = size
        self.encoding = encoding
        # FIXME
        self.property_types_by_ident = _property_types_by_ident

    def interpret(self, identifier, raw_values):
        """Return a Python representation of a property value.

        identifier -- PropIdent
        raw_values -- nonempty list of 8-bit strings in the coder's encoding

        See the interpret_... functions above for details of how values are
        represented as Python types.

        Raises ValueError if it cannot interpret the value.

        Note that in some cases the interpret_... functions accept values which
        are not strictly permitted by the specification.

        elist handling: if the property's value type is a list type and
        'raw_values' is a list containing a single empty string, passes an
        empty list to the interpret_... function (that is, this function treats
        all lists like elists).

        Doesn't enforce range restrictions on values with type Number.

        FIXME See the _property_types_by_ident table above for a list of known
        properties.

        Treats unknown (private) properties as if they had type Text.

        """
        pt = self.property_types_by_ident.get(identifier, private_property)
        if pt.uses_list:
            if raw_values == [""]:
                raw = []
            else:
                raw = raw_values
        else:
            raw = raw_values[0]
        return pt.interpreter(raw, self)

    def serialise(self, identifier, value):
        """Serialise a Python representation of a property value.

        identifier -- PropIdent
        value      -- corresponding Python value

        Returns a nonempty list of 8-bit strings in the coder's encoding,
        suitable for use as raw PropValues.

        See the serialise_... functions above for details of the acceptable
        values for each type.

        elist handling: if the property's value type is an elist type and the
        serialise_... function returns an empty list, this returns a list
        containing a single empty string.

        Raises ValueError if it cannot serialise the value.

        FIXME See the property_types_by_ident table above for a list of known
        properties.

        Treats unknown (private) properties as if they had type Text.

        In general, the serialise_... functions try not to produce an invalid
        result, but do not try to prevent garbage input happening to produce a
        valid result.

        """
        pt = self.property_types_by_ident.get(identifier, private_property)
        serialised = pt.serialiser(value, self)
        if pt.uses_list:
            if serialised == []:
                if pt.allows_empty_list:
                    return [""]
                else:
                    raise ValueError("empty list")
            return serialised
        else:
            return [serialised]
