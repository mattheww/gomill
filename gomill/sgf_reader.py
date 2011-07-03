"""Interpret SGF data.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

from gomill import boards
from gomill import sgf_parser


def interpret_none(s):
    """Convert a raw None value to a boolean.

    That is, unconditionally returns True.

    """
    return True

def interpret_number(s):
    """Convert a raw Number value to the integer it represents."""
    return int(s)

def interpret_real(s):
    """Convert a raw Real value to the float it represents.

    This is more lenient than the SGF spec: it accepts strings accepted as a
    float by the platform libc.

    """
    # Would be nice to at least reject Inf and NaN, but Python 2.5 is deficient
    # here.
    return float(s)

def interpret_double(s):
    """Convert a raw Double value to an integer.

    Returns 1 or 2 (unknown values are treated as 1).

    """
    if s.strip() == "2":
        return 2
    else:
        return 1

def interpret_colour(s):
    """Convert a raw Color value to a gomill colour.

    Returns 'b' or 'w'.

    """
    colour = s.lower()
    if colour not in ('b', 'w'):
        raise ValueError
    return colour

def interpret_simpletext(s):
    """Convert a raw SimpleText value to a string.

    See sgf_parser.simpletext_value() for details.

    Returns an 8-bit string.

    """
    return sgf_parser.simpletext_value(s)

def interpret_text(s):
    """Convert a raw Text value to a string.

    See sgf_parser.text_value() for details.

    Returns an 8-bit string.

    """
    return sgf_parser.text_value(s)

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
    if not (0 <= col < size) and (0 <= row < size):
        raise ValueError
    return row, col

def interpret_compressed_point_list(values, size):
    """Convert a raw SGF list or elist of Points to a set of coordinates.

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

def interpret_AP(s):
    """Interpret an AP (application) property value.

    Returns a pair of strings (but if there is no delimiter, the second value
    is None)

    """
    application, version = sgf_parser.parse_compose(s)
    if version is not None:
        version = interpret_simpletext(version)
    return interpret_simpletext(application), version

def interpret_ARLN(values, size):
    """Interpret an AR (arrow) or LN (line) property value.

    Returns a list of pairs (coords, coords).

    """
    result = []
    for s in values:
        p1, p2 = sgf_parser.parse_compose(s)
        result.append((interpret_point(p1, size), interpret_point(p2, size)))
    return result

def interpret_FG(s):
    """Interpret a FG (figure) property value.

    Returns a pair (flags, string), or None.

    flags is an integer; see http://www.red-bean.com/sgf/properties.html#FG

    """
    if s == "":
        return None
    flags, name = sgf_parser.parse_compose(s)
    return int(flags), interpret_simpletext(name)

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

class _Property(object):
    """Description of a property type."""
    def __init__(self, interpreter, uses_list=False):
        self.interpreter = interpreter
        self.uses_list = uses_list
        self.uses_size = (interpreter.func_code.co_argcount == 2)

P = _Property
LIST = ELIST = True
_properties = {
  'AB' : P(interpret_compressed_point_list, LIST),  # setup      Add Black
  'AE' : P(interpret_compressed_point_list, LIST),  # setup      Add Empty
  'AN' : P(interpret_simpletext),                   # game-info  Annotation
  'AP' : P(interpret_AP),                           # root       Application
  'AR' : P(interpret_ARLN, LIST),                   # -          Arrow
  'AW' : P(interpret_compressed_point_list, LIST),  # setup      Add White
  'B'  : P(interpret_point),                        # move       Black
  'BL' : P(interpret_real),                         # move       Black time left
  'BM' : P(interpret_double),                       # move       Bad move
  'BR' : P(interpret_simpletext),                   # game-info  Black rank
  'BT' : P(interpret_simpletext),                   # game-info  Black team
  'C'  : P(interpret_text),                         # -          Comment
  'CA' : P(interpret_simpletext),                   # root       Charset
  'CP' : P(interpret_simpletext),                   # game-info  Copyright
  'CR' : P(interpret_compressed_point_list, LIST),  # -          Circle
  'DD' : P(interpret_compressed_point_list, ELIST), # - (inherit)Dim points
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
  'MA' : P(interpret_compressed_point_list, LIST),  # -          Mark
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
  'SL' : P(interpret_compressed_point_list, LIST),  # -          Selected
  'SO' : P(interpret_simpletext),                   # game-info  Source
  'SQ' : P(interpret_compressed_point_list, LIST),  # -          Square
  'ST' : P(interpret_number),                       # root       Style
  'SZ' : P(interpret_number),                       # root       Size
  'TB' : P(interpret_compressed_point_list, ELIST), # -          Territory Black
  'TE' : P(interpret_double),                       # move       Tesuji
  'TM' : P(interpret_real),                         # game-info  Timelimit
  'TR' : P(interpret_compressed_point_list, LIST),  # -          Triangle
  'TW' : P(interpret_compressed_point_list, ELIST), # -          Territory White
  'UC' : P(interpret_double),                       # -          Unclear pos
  'US' : P(interpret_simpletext),                   # game-info  User
  'V'  : P(interpret_real),                         # -          Value
  'VW' : P(interpret_compressed_point_list, ELIST), # - (inherit)View
  'W'  : P(interpret_point),                        # move       White
  'WL' : P(interpret_real),                         # move       White time left
  'WR' : P(interpret_simpletext),                   # game-info  White rank
  'WT' : P(interpret_simpletext),                   # game-info  White team
}
_private_property = P(interpret_text)
del P, LIST, ELIST


class Node(object):
    """An SGF node."""
    __slots__ = ('props_by_id', 'size')

    def __init__(self, properties, size):
        # Map identifier (PropIdent) -> list of raw values
        self.props_by_id = properties
        self.size = size

    def has_property(self, identifier):
        """Check whether the node has the specified property."""
        return identifier in self.props_by_id

    def get_raw(self, identifier):
        """Return the raw scalar value of the specified property.

        Returns the raw bytes that were between the square brackets, without
        interpreting escapes or performing any whitespace conversion.

        Raises KeyError if there was no property with the given identifier.

        If the property had multiple values, this returns the first. If the
        property was an empty elist, this returns an empty string.

        """
        return self.props_by_id[identifier][0]

    def get_raw_list(self, identifier):
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
        """Return the interpreted value of the specified property.

        Treats unknown (private) properties as if they had type Text.

        Raises KeyError if there was no property with the given identifier.

        Raises ValueError if it cannot interpret the value.

        See the interpret... functions above for details of how values are
        represented as Python types. Note that in some cases these functions
        accept values which are not strictly permitted by the specification.

        FIXME: Doc what the known properties and their types are?

        """
        prop = _properties.get(identifier, _private_property)
        interpreter = prop.interpreter
        if prop.uses_list:
            raw = self.props_by_id[identifier]
            if raw == [""]:
                raw = []
        else:
            raw = self.props_by_id[identifier][0]
        if prop.uses_size:
            return interpreter(raw, self.size)
        else:
            return interpreter(raw)

    def get_raw_move(self):
        """Return the raw value of the move from a node.

        Returns a pair (colour, raw value)

        colour is 'b' or 'w'.

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
        return colour, values[0]

    def get_move(self):
        """Retrieve the move from a node.

        Returns a pair (colour, coords)

        colour is 'b' or 'w'.

        coords are (row, col), or None for a pass.

        Returns None, None if the node contains no B or W property.

        """
        colour, raw = self.get_raw_move()
        if colour is None:
            return None, None
        return colour, interpret_point(raw, self.size)

    def get_setup_commands(self):
        """Retrieve Add Black / Add White / Add Empty properties from a node.

        Returns a tuple (black_points, white_points, empty_points)

        Each value is a set of pairs (row, col).

        """
        try:
            bp = self.get("AB")
        except KeyError:
            bp = set()
        try:
            wp = self.get("AW")
        except KeyError:
            wp = set()
        try:
            ep = self.get("AE")
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


class Tree_node(Node):
    """A node embedded in an SGF game.

    A Tree_node is a Node that also knows its position within an Sgf_game.

    Do not instantiate directly; retrieve from an Sgf_game or another node.

    A Tree_node is a list-like container of its children: it can be indexed,
    sliced, and iterated over like a list. A node with no children is treated
    as having truth value false.

    Public attributes (treat as read-only):
      owner  -- the node's Sgf_game
      parent -- the nodes's parent Tree_node (None for the root node)

    """
    def __init__(self, parent, properties):
        self.owner = parent.owner
        self.parent = parent
        self._children = []
        Node.__init__(self, properties, parent.size)

    def children(self):
        """Return the children of this node.

        Returns a list of Tree_nodes (the same node objects each time you
        call it, but not the same list).

        """
        return self._children[:]

    def _add_child(self, node):
        self._children.append(node)

    def __len__(self):
        return len(self._children)

    def __getitem__(self, key):
        return self._children[key]

    def find(self, identifier):
        """Find the nearest ancestor-or-self containing the specified property.

        Returns a Tree_node, or None if there is no such node.

        """
        node = self
        while node is not None:
            if node.has_property(identifier):
                return node
            node = node.parent
        return None

    def find_property(self, identifier):
        """Return the value of a property, defined at this node or an ancestor.

        This is intended for use with properties of type 'game-info', and with
        properties with the 'inherit' attribute.

        This returns the interpreted value, in the same way as get().

        It searches up the tree, in the same way as find().

        Raises KeyError if no node defining the property is found.

        """
        node = self.find(identifier)
        if node is None:
            raise KeyError
        return node.get(identifier)

class Root_tree_node(Tree_node):
    """Variant of Tree_node used for a game root."""
    def __init__(self, owner, game_tree, size):
        self.owner = owner
        self.parent = None
        self._game_tree = game_tree
        self._children = None
        Node.__init__(self, game_tree.sequence[0], size)

    def _ensure_expanded(self):
        if self._children is None:
            self._children = []
            sgf_parser.make_tree(
                self._game_tree, self, Tree_node, Tree_node._add_child)
            self._game_tree = None

    def children(self):
        self._ensure_expanded()
        return self._children[:]

    def __len__(self):
        self._ensure_expanded()
        return len(self._children)

    def __getitem__(self, key):
        self._ensure_expanded()
        return self._children[key]


class Sgf_game(object):
    """An SGF game.

    Instantiate with a Parsed_game_tree.

    The nodes' property maps will be the same objects as the ones from the
    Parsed_game_tree.

    """
    def __init__(self, parsed_game):
        self._parsed_game = parsed_game
        try:
            size = int(parsed_game.sequence[0]['SZ'][0])
        except KeyError:
            size = 19
        self.size = size
        self.root = Root_tree_node(self, parsed_game, size)

    def get_root(self):
        """Return the root node (as a Tree_node)."""
        return self.root

    def get_main_sequence(self):
        """Return the 'leftmost' variation.

        Returns a list of Tree_nodes, from the root to a leaf.

        """
        node = self.root
        result = [node]
        while node:
            node = node[0]
            result.append(node)
        return result

    def get_main_sequence_below(self, node):
        """Return the 'leftmost' variation below the specified node.

        node -- Tree_node

        Returns a list of Tree_nodes, from the first child of 'node' to a leaf.

        """
        if node.owner is not self:
            raise ValueError("node doesn't belong to this game")
        result = []
        while node:
            node = node[0]
            result.append(node)
        return result

    def get_sequence_above(self, node):
        """Return the partial variation leading to the specified node.

        node -- Tree_node

        Returns a list of Tree_nodes, from the root to the parent of 'node'.

        """
        if node.owner is not self:
            raise ValueError("node doesn't belong to this game")
        result = []
        while node.parent is not None:
            node = node.parent
            result.append(node)
        result.reverse()
        return result

    def main_sequence_iter(self):
        """Provide the 'leftmost' variation as an iterable.

        Returns an iterable of Node instances, from the root to a leaf.

        The Node instances may or may not be Tree_nodes.

        If you know the game has no variations, or you're only interested in
        the 'leftmost' variation, you can use this function to retrieve the
        nodes without building the entire game tree.

        """
        size = self.size
        for properties in sgf_parser.main_sequence_iter(self._parsed_game):
            yield Node(properties, size)

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

        The moves are from the game's 'leftmost' variation.

        Raises ValueError if this position isn't legal.

        Raises ValueError if there are any AB/AW/AE properties after the root
        node.

        Doesn't check whether the moves are legal.

        """
        size = self.get_size()
        board = boards.Board(size)
        ab, aw, ae = self.root.get_setup_commands()
        if ab or aw:
            is_legal = board.apply_setup(ab, aw, ae)
            if not is_legal:
                raise ValueError("setup position not legal")
        moves = []
        nodes = self.main_sequence_iter()
        nodes.next()
        for node in nodes:
            if node.has_setup_commands():
                raise ValueError("setup commands after the root node")
            colour, raw = node.get_raw_move()
            if colour is not None:
                moves.append((colour, interpret_point(raw, size)))
        return board, moves

def sgf_game_from_string(s):
    """Read a single SGF game from a string.

    s -- 8-bit string

    Returns an Sgf_game.

    Raises ValueError if it can't parse the string. See parse_sgf_game() for
    details.

    """
    return Sgf_game(sgf_parser.parse_sgf_game(s))

