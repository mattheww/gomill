"""Interpret SGF property values.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

This supports all generic properties and Go-specific properties, but not
properties for other games. Point, Move and Stone values are interpreted as
Go points.

"""

from gomill import sgf_parser
from gomill import sgf_serialiser

def interpret_none(s):
    """Convert a raw None value to a boolean.

    That is, unconditionally returns True.

    """
    return True

def serialise_none(b):
    """Serialise a None value.

    Ignores its parameter.

    """
    return ""


def interpret_number(s):
    """Convert a raw Number value to the integer it represents.

    This is a little more lenient than the SGF spec: it permits leading and
    trailing spaces, and spaces between the sign and the numerals.

    """
    return int(s, 10)

def serialise_number(i):
    """Serialise a Number value.

    i -- integer

    """
    return "%d" % i


def interpret_real(s):
    """Convert a raw Real value to the float it represents.

    This is more lenient than the SGF spec: it accepts strings accepted as a
    float by the platform libc.

    """
    # Would be nice to at least reject Inf and NaN, but Python 2.5 is deficient
    # here.
    return float(s)

def serialise_real(f):
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


def interpret_double(s):
    """Convert a raw Double value to an integer.

    Returns 1 or 2 (unknown values are treated as 1).

    """
    if s.strip() == "2":
        return 2
    else:
        return 1

def serialise_double(i):
    """Serialise a Double value.

    i -- integer (1 or 2)

    (unknown values are treated as 1)

    """
    if i == 2:
        return "2"
    return "1"


def interpret_colour(s):
    """Convert a raw Color value to a gomill colour.

    Returns 'b' or 'w'.

    """
    colour = s.lower()
    if colour not in ('b', 'w'):
        raise ValueError
    return colour

def serialise_colour(colour):
    """Serialise a Colour value.

    colour -- 'b' or 'w'

    """
    if colour not in ('b', 'w'):
        raise ValueError
    return colour.upper()


def interpret_simpletext(s):
    """Convert a raw SimpleText value to a string.

    See sgf_parser.simpletext_value() for details.

    Returns an 8-bit string.

    """
    return sgf_parser.simpletext_value(s)

def serialise_simpletext(s):
    """Serialise a SimpleText value."""
    return sgf_serialiser.escape_text(s)


def interpret_text(s):
    """Convert a raw Text value to a string.

    See sgf_parser.text_value() for details.

    Returns an 8-bit string.

    """
    return sgf_parser.text_value(s)

def serialise_text(s):
    """Serialise a Text value."""
    return sgf_serialiser.escape_text(s)


def interpret_point(s, size):
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

def serialise_point(move, size):
    """Serialise a Point, Move, or Stone value.

    move -- pair (row, col), or None for a pass
    size -- board size (int)

    The move coordinates are in the GTP coordinate system (as in the rest of
    gomill), where (0, 0) is the lower left.

    Only supports board sizes up to 26.

    """
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


def interpret_point_list(values, size):
    """Convert a raw SGF list or elist of Points to a set of coordinates.

    values -- list of strings
    size   -- board size (int)

    Returns a set of pairs (row, col).

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
                top, left = interpret_point(p1, size)
                bottom, right = interpret_point(p2, size)
            except TypeError:
                raise ValueError
            if not (bottom <= top and left <= right):
                raise ValueError
            for row in xrange(bottom, top+1):
                for col in xrange(left, right+1):
                    result.add((row, col))
        else:
            pt = interpret_point(p1, size)
            if pt is None:
                raise ValueError
            result.add(pt)
    return result

def serialise_point_list(points, size):
    """Serialise a list of Points, Moves, or Stones.

    points -- iterable of pairs (row, col)
    size   -- board size (int)

    Returns a list of strings.

    If 'points' is empty, returns an empty list.

    Doesn't produce a compressed point list.

    """
    result = [serialise_point(point, size) for point in points]
    result.sort()
    return result


def interpret_AP(s):
    """Interpret an AP (application) property value.

    Returns a pair of strings (name, version number)

    Permits the version number to be missing (which is forbidden by the SGF
    spec), in which case the second returned value is an empty string.

    """
    application, version = sgf_parser.parse_compose(s)
    if version is None:
        version = ""
    return interpret_simpletext(application), interpret_simpletext(version)

def serialise_AP(value):
    """Serialise an AP (application) property value.

    value -- pair (application, version)
      application -- string
      version     -- string

    Note this takes a single parameter (which is a pair).

    """
    application, version = value
    return sgf_serialiser.compose(sgf_serialiser.escape_text(application),
                                  sgf_serialiser.escape_text(version))


def interpret_ARLN(values, size):
    """Interpret an AR (arrow) or LN (line) property value.

    Returns a list of pairs (coords, coords).

    """
    result = []
    for s in values:
        p1, p2 = sgf_parser.parse_compose(s)
        result.append((interpret_point(p1, size), interpret_point(p2, size)))
    return result

def serialise_ARLN(values, size):
    """Serialise an AR (arrow) or LN (line) property value.

    values -- list of pairs (coords, coords)

    """
    return ["%s:%s" % (serialise_point(p1, size),
                       serialise_point(p2, size))
            for p1, p2 in values]


def interpret_FG(s):
    """Interpret an FG (figure) property value.

    Returns a pair (flags, string), or None.

    flags is an integer; see http://www.red-bean.com/sgf/properties.html#FG

    """
    if s == "":
        return None
    flags, name = sgf_parser.parse_compose(s)
    return int(flags), interpret_simpletext(name)

def serialise_FG(value):
    """Serialise an FG (figure) property value.

    value -- pair (flags, name), or None
      flags -- int
      name  -- string

    Use serialise_FG(None) to produce an empty value.

    """
    if value is None:
        return ""
    flags, name = value
    return "%d:%s" % (flags, sgf_serialiser.escape_text(name))


def interpret_LB(values, size):
    """Interpret an LB (label) property value.

    Returns a list of pairs (coords, string).

    """
    result = []
    for s in values:
        point, label = sgf_parser.parse_compose(s)
        result.append((interpret_point(point, size),
                       interpret_simpletext(label)))
    return result

def serialise_LB(values, size):
    """Serialise an LB (label) property value.

    values -- list of pairs (coords, string)

    """
    return ["%s:%s" % (serialise_point(point, size),
                       sgf_serialiser.escape_text(text))
            for point, text in values]


class Property(object):
    """Description of a property type."""
    def __init__(self, interpreter, uses_list=False):
        self.interpreter = interpreter
        self.uses_list = uses_list
        self.uses_size = (interpreter.func_code.co_argcount == 2)
        self.serialiser = globals()[
            interpreter.func_name.replace("interpret_", "serialise_")]

P = Property
LIST = ELIST = True
properties_by_ident = {
  'AB' : P(interpret_point_list, LIST),             # setup      Add Black
  'AE' : P(interpret_point_list, LIST),             # setup      Add Empty
  'AN' : P(interpret_simpletext),                   # game-info  Annotation
  'AP' : P(interpret_AP),                           # root       Application
  'AR' : P(interpret_ARLN, LIST),                   # -          Arrow
  'AW' : P(interpret_point_list, LIST),             # setup      Add White
  'B'  : P(interpret_point),                        # move       Black
  'BL' : P(interpret_real),                         # move       Black time left
  'BM' : P(interpret_double),                       # move       Bad move
  'BR' : P(interpret_simpletext),                   # game-info  Black rank
  'BT' : P(interpret_simpletext),                   # game-info  Black team
  'C'  : P(interpret_text),                         # -          Comment
  'CA' : P(interpret_simpletext),                   # root       Charset
  'CP' : P(interpret_simpletext),                   # game-info  Copyright
  'CR' : P(interpret_point_list, LIST),             # -          Circle
  'DD' : P(interpret_point_list, ELIST),            # - (inherit)Dim points
  'DM' : P(interpret_double),                       # -          Even position
  'DO' : P(interpret_none),                         # move       Doubtful
  'DT' : P(interpret_simpletext),                   # game-info  Date
  'EV' : P(interpret_simpletext),                   # game-info  Event
  'FF' : P(interpret_number),                       # root       Fileformat
  'FG' : P(interpret_FG),                           # -          Figure
  'GB' : P(interpret_double),                       # -          Good for Black
  'GC' : P(interpret_text),                         # game-info  Game comment
  'GM' : P(interpret_number),                       # root       Game
  'GN' : P(interpret_simpletext),                   # game-info  Game name
  'GW' : P(interpret_double),                       # -          Good for White
  'HA' : P(interpret_number),                       # game-info  Handicap
  'HO' : P(interpret_double),                       # -          Hotspot
  'IT' : P(interpret_none),                         # move       Interesting
  'KM' : P(interpret_real),                         # game-info  Komi
  'KO' : P(interpret_none),                         # move       Ko
  'LB' : P(interpret_LB, LIST),                     # -          Label
  'LN' : P(interpret_ARLN, LIST),                   # -          Line
  'MA' : P(interpret_point_list, LIST),             # -          Mark
  'MN' : P(interpret_number),                       # move       set move number
  'N'  : P(interpret_simpletext),                   # -          Nodename
  'OB' : P(interpret_number),                       # move       OtStones Black
  'ON' : P(interpret_simpletext),                   # game-info  Opening
  'OT' : P(interpret_simpletext),                   # game-info  Overtime
  'OW' : P(interpret_number),                       # move       OtStones White
  'PB' : P(interpret_simpletext),                   # game-info  Player Black
  'PC' : P(interpret_simpletext),                   # game-info  Place
  'PL' : P(interpret_colour),                       # setup      Player to play
  'PM' : P(interpret_number),                       # - (inherit)Print move mode
  'PW' : P(interpret_simpletext),                   # game-info  Player White
  'RE' : P(interpret_simpletext),                   # game-info  Result
  'RO' : P(interpret_simpletext),                   # game-info  Round
  'RU' : P(interpret_simpletext),                   # game-info  Rules
  'SL' : P(interpret_point_list, LIST),             # -          Selected
  'SO' : P(interpret_simpletext),                   # game-info  Source
  'SQ' : P(interpret_point_list, LIST),             # -          Square
  'ST' : P(interpret_number),                       # root       Style
  'SZ' : P(interpret_number),                       # root       Size
  'TB' : P(interpret_point_list, ELIST),            # -          Territory Black
  'TE' : P(interpret_double),                       # move       Tesuji
  'TM' : P(interpret_real),                         # game-info  Timelimit
  'TR' : P(interpret_point_list, LIST),             # -          Triangle
  'TW' : P(interpret_point_list, ELIST),            # -          Territory White
  'UC' : P(interpret_double),                       # -          Unclear pos
  'US' : P(interpret_simpletext),                   # game-info  User
  'V'  : P(interpret_real),                         # -          Value
  'VW' : P(interpret_point_list, ELIST),            # - (inherit)View
  'W'  : P(interpret_point),                        # move       White
  'WL' : P(interpret_real),                         # move       White time left
  'WR' : P(interpret_simpletext),                   # game-info  White rank
  'WT' : P(interpret_simpletext),                   # game-info  White team
}
private_property = P(interpret_text)

del P, LIST, ELIST


def interpret_value(identifier, raw_values, size):
    """Return a Python representation of a property value.

    identifier -- PropIdent
    raw_values -- nonempty list of 8-bit strings
    size       -- board size (int)

    See the interpret_... functions above for details of how values are
    represented as Python types.

    Raises ValueError if it cannot interpret the value.

    Note that in some cases the interpret_... functions accept values which are
    not strictly permitted by the specification.

    Doesn't enforce range restrictions on values with type Number.

    See the properties_by_ident table above for a list of known properties.

    Treats unknown (private) properties as if they had type Text.

    """
    prop = properties_by_ident.get(identifier, private_property)
    interpreter = prop.interpreter
    if prop.uses_list:
        if raw_values == [""]:
            raw = []
        else:
            raw = raw_values
    else:
        raw = raw_values[0]
    if prop.uses_size:
        return interpreter(raw, size)
    else:
        return interpreter(raw)

def serialise_value(identifier, value, size):
    """Serialise a Python representation of a property value.

    identifier -- PropIdent
    value      -- corresponding Python value
    size       -- board size (int)

    Returns a nonempty list of 8-bit strings, suitable for use as raw
    PropValues.

    See the serialise_... functions above for details of the acceptable values
    for each type.

    Raises ValueError if it cannot serialise the value.

    See the properties_by_ident table above for a list of known properties.

    Treats unknown (private) properties as if they had type Text.

    In general, the serialise_... functions try not to produce an invalid
    result, but do not try to prevent garbage input happening to produce a
    valid result.

    """
    prop = properties_by_ident.get(identifier, private_property)
    serialiser = prop.serialiser
    if prop.uses_size:
        result = serialiser(value, size)
    else:
        result = serialiser(value)
    if prop.uses_list:
        if result == []:
            return [""]
        return result
    else:
        return [result]

