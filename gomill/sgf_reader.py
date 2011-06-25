"""Read sgf files."""

import re

from gomill import boards


def escape_text(s):
    """Apply the escaping rules for Text."""
    return s.replace("\\", "\\\\").replace("]", "\\]")


_newline_re = re.compile("\n\r|\r\n|\n|\r")

def unescape_text(s):
    """Convert a raw Text value to the string it represents.

    This interprets escape characters, and does whitespace mapping.

    Linebreaks (LF, CR, LFCR, CRLF) are converted to \n.

    """
    s = _newline_re.sub("\n", s)
    is_escaped = False
    result = []
    i = 0
    try:
        while True:
            c = s[i]
            if c != "\n" and c.isspace():
                c = " "
            if is_escaped:
                if c != "\n":
                    result.append(c)
                i += 1
                is_escaped = False
                continue
            if c == "\\":
                is_escaped = True
                i += 1
                continue
            if c == "]":
                raise AssertionError
            result.append(c)
            i += 1
    except IndexError:
        pass
    return "".join(result)

def interpret_point(s, size):
    """Interpret an SGF Point or Move value.

    s -- string

    Returns a pair (row, col), or None for a pass.

    Raises ValueError if the string is malformed or the coordinates are out of
    range.

    """
    s = s.lower()
    if s == "" or (s == "tt" and size <= 19):
        return None
    try:
        col_s, row_s = s
    except TypeError:
        raise ValueError
    col = ord(col_s) - ord("a")
    if not 0 <= col < size:
        raise ValueError
    row = ord(row_s) - ord("a")
    row = size - row - 1
    if not 0 <= row < size:
        raise ValueError
    return row, col

def interpret_compressed_point_list(values, size):
    """Interpret an SGF list or elist of Points.

    values -- list of strings

    Returns a set of pairs (row, col).

    Raises ValueError if the data is malformed.

    Doesn't complain if there is overlap.

    """
    result = set()
    for s in values:
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


class Prop(object):
    """An SGF property.

    'values' is a nonempty list of property values. (An elist specified as [] is
    represented as a single empty string.)

    Property values are 8-bit strings in the source encoding. They haven't been
    'unescaped'.

    """

    def __init__(self, identifier, values):
        self.identifier = identifier
        self.values = values

    def __str__(self):
        return self.identifier + "".join("[%s]" % s for s in self.values)

class Node(object):
    """An SGF node.

    This doesn't know the types of different properties; the escaping rules for
    Text are applied to all values.

    """

    def __init__(self, owner):
        # Owning SGF file: used to find board size to interpret moves.
        self.owner = owner
        self.prop_list = []
        self.props_by_id = {}

    def add(self, prop):
        self.prop_list.append(prop)
        self.props_by_id[prop.identifier] = prop

    def get(self, identifier):
        """Return the scalar value of the specified property.

        Raises KeyError if there was no property with the given identifier.

        If the property had multiple values, this returns the first. If the
        property was an empty elist, this returns an empty string.

        """
        return unescape_text(self.props_by_id[identifier].values[0])

    def get_list(self, identifier):
        """Return the list value of the specified property.

        Raises KeyError if there was no property with the given identifier.

        If the property had a single value, this returns a single-element list.

        If the property had value [], returns an empty list (as appropriate for
        an elist).

        """
        l = self.props_by_id[identifier].values
        if l == [""]:
            return []
        else:
            return map(unescape_text, l)

    def has_prop(self, identifier):
        return identifier in self.props_by_id

    def get_props(self):
        return self.prop_list[:]

    def get_move(self):
        """Retrieve the move from a node.

        Returns a pair (colour, coords)

        colour is 'b' or 'w'.

        coords are (row, col), or None for a pass.

        Returns None, None if the node contains no B or W property.

        """
        size = self.owner.get_size()
        prop = self.props_by_id.get("B")
        if prop is not None:
            colour = "b"
        else:
            prop = self.props_by_id.get("W")
            if prop is not None:
                colour = "w"
            else:
                return None, None
        return colour, interpret_point(prop.values[0], size)

    def get_setup_commands(self):
        """Retrieve Add Black / Add White / Add Empty properties from a node.

        Returns a tuple (black_points, white_points, empty_points)

        Each value is a set of pairs (row, col).

        """
        size = self.owner.get_size()
        try:
            bp = interpret_compressed_point_list(self.get_list("AB"), size)
        except KeyError:
            bp = set()
        try:
            wp = interpret_compressed_point_list(self.get_list("AW"), size)
        except KeyError:
            wp = set()
        try:
            ep = interpret_compressed_point_list(self.get_list("AE"), size)
        except KeyError:
            ep = set()
        return bp, wp, ep

    def has_setup_commands(self):
        """Check whether the node has any AB/AW/AE properties."""
        return self.has_prop("AB") or self.has_prop("AW") or self.has_prop("AE")

    def __str__(self):
        return "\n".join(str(p) for p in self.prop_list)


class Sgf_game_tree(object):
    """An SGF game tree."""

    def __init__(self):
        self.nodes = []

    def new_node(self):
        node = Node(self)
        self.nodes.append(node)
        return node

    def get_root_prop(self, prop):
        """Return a root-node property as a string.

        Raises KeyError if the property isn't present.

        """
        return self.nodes[0].get(prop)

    def get_size(self):
        """Return the board size as an integer."""
        try:
            return int(self.get_root_prop("SZ"))
        except KeyError:
            return 19

    def get_komi(self):
        """Return the komi as a float.

        Returns 0.0 if the KM property isn't present.

        Raises ValueError if the KM property is malformed.

        """
        try:
            komi_s = self.get_root_prop("KM")
        except KeyError:
            return 0.0
        return float(komi_s)

    def get_handicap(self):
        """Return the number of handicap stones as a small integer.

        Returns None if the HA property isn't present, or has (illegal) value
        zero.

        Raises ValueError if the HA property is otherwise malformed.

        """
        try:
            handicap_s = self.get_root_prop("HA")
        except KeyError:
            return None
        handicap = int(handicap_s)
        if handicap == 0:
            handicap = None
        elif handicap == 1:
            raise ValueError
        return handicap

    def get_player(self, colour):
        """Return the name of the specified player."""
        return self.get_root_prop({'b' : 'PB', 'w' : 'PW'}[colour])

    def get_winner(self):
        """Return the colour of the winning player.

        Returns None if there is no RE property, or if neither player won.

        """
        try:
            colour = self.get_root_prop("RE")[0].lower()
        except LookupError:
            return None
        if colour not in ("b", "w"):
            return None
        return colour

    def get_setup_and_moves(self):
        """Return the initial setup and the following moves.

        Returns a pair (board, moves)

          board -- boards.Board
          moves -- list of pairs (colour, coords)
                   coords are (row, col), or None for a pass.

        The board represents the position described by AB and/or AW properties
        in the root node.

        Raises ValueError if this position isn't legal.

        Raises ValueError if there are any AB/AW/AE properties after the root
        node.

        Doesn't check whether the moves are legal.

        """
        board = boards.Board(self.get_size())
        ab, aw, ae = self.nodes[0].get_setup_commands()
        if ab or aw:
            is_legal = board.apply_setup(ab, aw, ae)
            if not is_legal:
                raise ValueError("setup position not legal")
        moves = []
        for node in self.nodes[1:]:
            if node.has_setup_commands():
                raise ValueError("setup commands after the root node")
            colour, coords = node.get_move()
            if colour is not None:
                moves.append((colour, coords))
        return board, moves


_find_start_re = re.compile(r"\(\s*;")
_tokenise_re = re.compile(r"""
\s*
(?:
    (?P<D> [;\(\)])                          # delimiter
    |
    (?P<I> [A-Z]{1,8})                       # PropIdent
    |
    \[ (?P<V> .*? (?<!\\) (?:\\\\)* ) \]     # PropValue
)
""", re.VERBOSE | re.DOTALL)

def _tokenise(s):
    """Tokenise a string containing SGF data.

    Skips leading junk.

    Returns a list of pairs of strings (token type, contents)

    token types and contents:
      I -- PropIdent: upper-case letters
      V -- PropValue: raw value, without the enclosing brackets
      D -- delimiter: ';', '(', or ')'

    Stops at the end of the string, or when it first finds something it can't
    tokenise.

    The first two tokens are always '(' and ';' (otherwise it won't find the
    start of the content).

    """
    result = []
    m = _find_start_re.search(s)
    if not m:
        return []
    i = m.start()
    while True:
        m = _tokenise_re.match(s, i)
        if not m:
            break
        result.append((m.lastgroup, m.group(m.lastindex)))
        i = m.end()
    return result

def read_sgf(s):
    """Interpret an SGF file from a string.

    Returns an Sgf_game_tree.

    Reads only the first sequence from the first game in the string (ie, any
    variations are ignored).

    Identifies the start of the SGF content by looking for '(;' (with possible
    whitespace between); ignores everything preceding that. Ignores everything
    following the first sequence from the first game.

    Raises ValueError if can't parse the string.

    """
    result = Sgf_game_tree()
    tokens = _tokenise(s)
    index = 0
    try:
        while True:
            token_type, contents = tokens[index]
            if token_type == 'V':
                raise ValueError("unexpected value")
            if token_type == 'D':
                if contents == ')':
                    break
                if contents == '(':
                    index += 1
                    continue
                if contents == ';':
                    index += 1
                    node = result.new_node()
                    continue
            #assert token_type == 'I'
            prop_ident = contents
            index += 1
            prop_values = []
            while True:
                token_type, contents = tokens[index]
                if token_type != 'V':
                    break
                index += 1
                prop_values.append(contents)
            if not prop_values:
                raise ValueError("property with no values")
            node.add(Prop(prop_ident, prop_values))
    except IndexError:
        raise ValueError("unexpected end of SGF data")
    return result

