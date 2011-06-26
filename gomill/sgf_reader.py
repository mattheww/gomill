"""Interpret SGF data.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

import re
import string

from gomill import boards


_newline_re = re.compile(r"\n\r|\r\n|\n|\r")
_whitespace_table = string.maketrans("\t\f\v", "   ")
_chunk_re = re.compile(r" [^\n\\]+ | [\n\\] ", re.VERBOSE)

def value_as_text(s):
    """Convert a raw Text value to the string it represents.

    This interprets escape characters, and does whitespace mapping:

    - linebreak (LF, CR, LFCR, or CRLF) is converted to \n
    - any other whitespace character is replaced by a space
    - backslash followed by linebreak disappears
    - other backslashes disappear (but double-backslash -> single-backslash)

    """
    s = _newline_re.sub("\n", s)
    s = s.translate(_whitespace_table)
    is_escaped = False
    result = []
    for chunk in _chunk_re.findall(s):
        if is_escaped:
            if chunk != "\n":
                result.append(chunk)
            is_escaped = False
        elif chunk == "\\":
            is_escaped = True
        else:
            result.append(chunk)
    return "".join(result)

def value_as_simpletext(s):
    """Convert a raw SimpleText value to the string it represents.

    This interprets escape characters, and does whitespace mapping:

    - backslash followed by linebreak (LF, CR, LFCR, or CRLF) disappears
    - any other linebreak is replaced by a space
    - any other whitespace character is replaced by a space
    - other backslashes disappear (but double-backslash -> single-backslash)

    """
    s = _newline_re.sub("\n", s)
    s = s.translate(_whitespace_table)
    is_escaped = False
    result = []
    for chunk in _chunk_re.findall(s):
        if is_escaped:
            if chunk != "\n":
                result.append(chunk)
            is_escaped = False
        elif chunk == "\\":
            is_escaped = True
        elif chunk == "\n":
            result.append(" ")
        else:
            result.append(chunk)
    return "".join(result)

def interpret_point(s, size):
    """Interpret an SGF Point, Move, or Stone value.

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
    try:
        col_s, row_s = s
    except TypeError:
        raise ValueError
    col = ord(col_s) - 97 # 97 == ord("a")
    row = size - ord(row_s) + 96
    if not (0 <= col < size) and (0 <= row < size):
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


class Node(object):
    """An SGF node.

    This doesn't know the types of different properties; it stores raw values,
    and it's up to the client to specify the escaping required.

    """
    __slots__ = ('props_by_id', 'size')

    def __init__(self):
        # Map identifier (PropIdent) -> list of raw values
        self.props_by_id = {}
        # self.size is filled in by Sgf_game_tree._setup()

    def _add(self, identifier, values):
        self.props_by_id[identifier] = values

    def has_property(self, identifier):
        """Check whether the node has the specified property."""
        return identifier in self.props_by_id

    def get_raw(self, identifier):
        """Return the raw scalar value of the specified property.

        Returns the raw bytes that were between the square brakets, without
        interpreting escapes or performing any whitespace conversion.

        Raises KeyError if there was no property with the given identifier.

        If the property had multiple values, this returns the first. If the
        property was an empty elist, this returns an empty string.

        """
        return self.props_by_id[identifier][0]

    def get_list(self, identifier):
        """Return the raw list value of the specified property.

        Returns a list of strings, containing 'raw' values (see get_raw()).

        Raises KeyError if there was no property with the given identifier.

        If the property had a single value, returns a single-element list.

        If the property had value [], returns an empty list (as appropriate for
        an elist).

        """
        l = self.props_by_id[identifier]
        if l == [""]:
            return []
        else:
            return l

    def get(self, identifier):
        """Return the value of the specified property, interpreted as text.

        Applies the formatting and escaping rules defined for SGF Text (see
        value_as_text() for details).

        Returns an 8-bit string, in the encoding of the original SGF string.

        Raises KeyError if there was no property with the given identifier.

        If the property had multiple values, this returns the first. If the
        property was an empty elist, this returns an empty string.

        """
        return value_as_text(self.props_by_id[identifier][0])

    def get_move(self):
        """Retrieve the move from a node.

        Returns a pair (colour, coords)

        colour is 'b' or 'w'.

        coords are (row, col), or None for a pass.

        Returns None, None if the node contains no B or W property.

        """
        values = self.props_by_id.get("B")
        if values is not None:
            colour = "b"
        else:
            values = self.props_by_id.get("W")
            if values is not None:
                colour = "w"
            else:
                return None, None
        return colour, interpret_point(values[0], self.size)

    def get_setup_commands(self):
        """Retrieve Add Black / Add White / Add Empty properties from a node.

        Returns a tuple (black_points, white_points, empty_points)

        Each value is a set of pairs (row, col).

        """
        try:
            bp = interpret_compressed_point_list(self.get_list("AB"), self.size)
        except KeyError:
            bp = set()
        try:
            wp = interpret_compressed_point_list(self.get_list("AW"), self.size)
        except KeyError:
            wp = set()
        try:
            ep = interpret_compressed_point_list(self.get_list("AE"), self.size)
        except KeyError:
            ep = set()
        return bp, wp, ep

    def has_setup_commands(self):
        """Check whether the node has any AB/AW/AE properties."""
        d = self.props_by_id
        return ("AB" in d or "AW" in d or "AE" in d)

    def __str__(self):
        def format_property(ident, values):
            return ident + "".join("[%s]" % s for s in values)
        return "\n".join(
            format_property(ident, values)
            for (ident, values) in sorted(self.props_by_id.items())) \
            + "\n"


class Sgf_game_tree(object):
    """An SGF game tree.

    Do not instantiate these directly; use parse_sgf().

    """
    def __init__(self):
        self._nodes = []

    def _setup(self):
        """Finish initialisation, after loading all nodes.

        Raises ValueError if vital properties are corrupt.

        """
        self.root = self._nodes[0]
        try:
            size = int(self.root.get_raw("SZ"))
        except KeyError:
            size = 19
        self.size = size
        for node in self._nodes:
            node.size = size

    def get_root_node(self):
        """Return the root Node."""
        return self.root

    def get_main_sequence(self):
        """Return a list of Nodes representing the first Sequence in the game.

        Do not modify the returned list.

        """
        return self._nodes

    def get_size(self):
        """Return the board size as an integer."""
        return self.size

    def get_komi(self):
        """Return the komi as a float.

        Returns 0.0 if the KM property isn't present.

        Raises ValueError if the KM property is malformed.

        """
        try:
            komi_s = self.root.get_raw("KM")
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
            handicap_s = self.root.get_raw("HA")
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
        return self.root.get({'b' : 'PB', 'w' : 'PW'}[colour])

    def get_winner(self):
        """Return the colour of the winning player.

        Returns None if there is no RE property, or if neither player won.

        """
        try:
            colour = self.root.get("RE")[0].lower()
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
        ab, aw, ae = self.root.get_setup_commands()
        if ab or aw:
            is_legal = board.apply_setup(ab, aw, ae)
            if not is_legal:
                raise ValueError("setup position not legal")
        moves = []
        for node in self._nodes[1:]:
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
    \[ (?P<V> [^\\\]]* (?: \\. [^\\\]]* )* ) \]   # PropValue
    |
    (?P<I> [A-Z]{1,8} )                           # PropIdent
    |
    (?P<D> [;()] )                                # delimiter
)
""", re.VERBOSE | re.DOTALL)

def _tokenise(s):
    """Tokenise a string containing SGF data.

    Skips leading junk.

    Returns a list of pairs of strings (token type, contents), and also the
    index in 's' of the start of the unmatched 'tail'

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
        return [], 0
    i = m.start()
    while True:
        m = _tokenise_re.match(s, i)
        if not m:
            break
        result.append((m.lastgroup, m.group(m.lastindex)))
        i = m.end()
    return result, i

def parse_sgf(s):
    """Interpret SGF data from a string.

    s -- 8-bit string

    Returns an Sgf_game_tree.

    Reads only the first sequence from the first game in the string (ie, it
    reads a GameTree not a Collection, and any variations are ignored).

    Identifies the start of the SGF content by looking for '(;' (with possible
    whitespace between); ignores everything preceding that. Ignores everything
    following the first sequence from the first game.

    Doesn't pay any attention to the FF[n] property; always applies the rules
    for FF[4].

    Raises ValueError if can't parse the string.

    """
    _Node = Node
    tree = Sgf_game_tree()
    _add_node = tree._nodes.append
    tokens, _ = _tokenise(s)
    index = 0
    try:
        while True:
            token_type, contents = tokens[index]
            index += 1
            if token_type == 'V':
                raise ValueError("unexpected value")
            if token_type == 'D':
                if contents == ')':
                    break
                if contents == '(':
                    pass
                if contents == ';':
                    node = _Node()
                    _add_node(node)
            else:
                # assert token_type == 'I'
                prop_ident = contents
                prop_values = []
                while True:
                    token_type, contents = tokens[index]
                    if token_type != 'V':
                        break
                    index += 1
                    prop_values.append(contents)
                if not prop_values:
                    raise ValueError("property with no values")
                node._add(prop_ident, prop_values)
    except IndexError:
        raise ValueError("unexpected end of SGF data")
    tree._setup()
    return tree

