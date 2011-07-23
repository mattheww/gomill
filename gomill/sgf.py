"""Represent SGF games.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

import codecs
import datetime

from gomill import boards
from gomill import sgf_grammar
from gomill import sgf_properties


def normalise_charset_name(s):
    """Convert an encoding name to the form implied in the SGF spec.

    In particular, normalises to 'ISO-8859-1' and 'UTF-8'.

    Raises LookupError if the encoding name isn't known to Python.

    """
    return (codecs.lookup(s).name.replace("_", "-").upper()
            .replace("ISO8859", "ISO-8859"))


class Node(object):
    """An SGF node.

    Instantiate with size and property map encoding.

    A Node doesn't belong to a particular game (cf Tree_node below), but it
    knows its board size (in order to interpret move values) and property map
    encoding.

    Changing the SZ or CA property isn't allowed.

    """
    __slots__ = ('_property_map', 'size', 'encoding')

    def __init__(self, property_map, size, encoding):
        # Map identifier (PropIdent) -> list of raw values
        self._property_map = property_map
        self.size = size
        # Encoding of Text and SimpleText raw values
        # (the 'property map encoding')
        # This is always normalised (see normalise_charset_name())
        self.encoding = encoding

    def has_property(self, identifier):
        """Check whether the node has the specified property."""
        return identifier in self._property_map

    def get_raw_list(self, identifier):
        """Return the raw values of the specified property.

        Returns a list of 8-bit strings, containing the exact bytes that were
        between the square brackets (without interpreting escapes or performing
        any whitespace conversion).

        Raises KeyError if there was no property with the given identifier.

        (If the property is an empty elist, this returns a list containing a
        single empty string.)

        """
        return self._property_map[identifier]

    def get_raw(self, identifier):
        """Return a single raw value of the specified property.

        Returns an 8-bit string, containing the exact bytes that were between
        the square brackets (without interpreting escapes or performing any
        whitespace conversion).

        Raises KeyError if there was no property with the given identifier.

        If the property has multiple values, this returns the first (if the
        value is an empty elist, this returns an empty string).

        """
        return self._property_map[identifier][0]

    def get_raw_property_map(self):
        """Return the raw values of all properties as a dict.

        Returns a dict mapping property identifiers to lists of raw values
        (see get_raw_list()).

        Returns the same dict each time it's called.

        Treat the returned dict as read-only.

        """
        return self._property_map


    def _set_raw_list(self, identifier, values):
        if identifier == "SZ" and values != [str(self.size)]:
            raise ValueError("changing size is not permitted")
        if identifier == "CA":
            try:
                s = normalise_charset_name(values[0])
            except LookupError:
                s = None
            if len(values) != 1 or s != self.encoding:
                raise ValueError("changing charset is not permitted")
        self._property_map[identifier] = values

    def unset(self, identifier):
        """Remove the specified property.

        Raises KeyError if the property isn't currently present.

        """
        if identifier == "SZ" and self.size != 19:
            raise ValueError("changing size is not permitted")
        if identifier == "CA" and self.encoding != "ISO-8859-1":
            raise ValueError("changing charset is not permitted")
        del self._property_map[identifier]


    def set_raw_list(self, identifier, values):
        """Set the raw values of the specified property.

        identifier -- ascii string passing is_valid_property_identifier()
        values     -- nonempty iterable of 8-bit strings

        The values specify the exact bytes to appear between the square
        brackets in the SGF file; you must perform any necessary escaping
        first.

        (To specify an empty elist, pass a list containing a single empty
        string.)

        """
        if not sgf_grammar.is_valid_property_identifier(identifier):
            raise ValueError("ill-formed property identifier")
        values = list(values)
        if not values:
            raise ValueError("empty property list")
        for value in values:
            if not sgf_grammar.is_valid_property_value(value):
                raise ValueError("ill-formed raw property value")
        self._set_raw_list(identifier, values)

    def set_raw(self, identifier, value):
        """Set the specified property to a single raw value.

        identifier -- ascii string passing is_valid_property_identifier()
        value      -- 8-bit string

        The value specifies the exact bytes to appear between the square
        brackets in the SGF file; you must perform any necessary escaping
        first.

        """
        if not sgf_grammar.is_valid_property_identifier(identifier):
            raise ValueError("ill-formed property identifier")
        if not sgf_grammar.is_valid_property_value(value):
            raise ValueError("ill-formed raw property value")
        self._set_raw_list(identifier, [value])


    def get(self, identifier):
        """Return the interpreted value of the specified property.

        Returns the value as a suitable Python representation.

        Raises KeyError if the node does not have a property with the given
        identifier.

        Raises ValueError if it cannot interpret the value.

        See sgf_properties.interpret_value() for details.

        """
        return sgf_properties.interpret_value(
            identifier, self._property_map[identifier],
            self.size, self.encoding)

    def set(self, identifier, value):
        """Set the value of the specified property.

        identifier -- ascii string passing is_valid_property_identifier()
        value      -- new property value (in its Python representation)

        For properties with value type 'none', use value True.

        Raises ValueError if it cannot represent the value.

        See sgf_properties.serialise_value() for details.

        """
        self._set_raw_list(identifier, sgf_properties.serialise_value(
            identifier, value, self.size, self.encoding))

    def get_raw_move(self):
        """Return the raw value of the move from a node.

        Returns a pair (colour, raw value)

        colour is 'b' or 'w'.

        Returns None, None if the node contains no B or W property.

        """
        values = self._property_map.get("B")
        if values is not None:
            colour = "b"
        else:
            values = self._property_map.get("W")
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
        return colour, sgf_properties.decode_point(raw, self.size)

    def get_setup_stones(self):
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

    def has_setup_stones(self):
        """Check whether the node has any AB/AW/AE properties."""
        d = self._property_map
        return ("AB" in d or "AW" in d or "AE" in d)

    def set_move(self, colour, coords):
        """Set the B or W property.

        colour -- 'b' or 'w'.
        coords -- (row, col), or None for a pass.

        Replaces any existing B or W property in the node.

        """
        if colour not in ('b', 'w'):
            raise ValueError
        if 'B' in self._property_map:
            del self._property_map['B']
        if 'W' in self._property_map:
            del self._property_map['W']
        self.set(colour.upper(), coords)

    def set_setup_stones(self, black, white, empty=None):
        """Set Add Black / Add White / Add Empty properties.

        black, white, empty -- list or set of pairs (row, col)

        Removes any existing AB/AW/AE properties from the node.

        """
        if 'AB' in self._property_map:
            del self._property_map['AB']
        if 'AW' in self._property_map:
            del self._property_map['AW']
        if 'AE' in self._property_map:
            del self._property_map['AE']
        if black:
            self.set('AB', black)
        if white:
            self.set('AW', white)
        if empty:
            self.set('AE', empty)

    def add_comment_text(self, text):
        """Add or extend the node's comment.

        If the node doesn't have a C property, adds one with the specified
        text.

        Otherwise, adds the specified text to the existing C property value
        (with two newlines in front).

        """
        if self.has_property('C'):
            self.set('C', self.get('C') + "\n\n" + text)
        else:
            self.set('C', text)

    def __str__(self):
        def format_property(ident, values):
            return ident + "".join("[%s]" % s for s in values)
        return "\n".join(
            format_property(ident, values)
            for (ident, values) in sorted(self._property_map.items())) \
            + "\n"


class Tree_node(Node):
    """A node embedded in an SGF game.

    A Tree_node is a Node that also knows its position within an Sgf_game.

    Do not instantiate directly; retrieve from an Sgf_game or another Tree_node.

    A Tree_node is a list-like container of its children: it can be indexed,
    sliced, and iterated over like a list, and supports index().

    A Tree_node with no children is treated as having truth value false.

    Public attributes (treat as read-only):
      owner  -- the node's Sgf_game
      parent -- the nodes's parent Tree_node (None for the root node)

    """
    def __init__(self, parent, properties):
        self.owner = parent.owner
        self.parent = parent
        self._children = []
        Node.__init__(self, properties, parent.size, parent.encoding)

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

    def index(self, child):
        return self._children.index(child)

    def new_child(self):
        """Create a new Tree_node and add it as this node's last child.

        Returns the new node.

        """
        child = Tree_node(self, {})
        self._children.append(child)
        return child

    def delete(self):
        """Remove this node from its parent."""
        if self.parent is None:
            raise ValueError("can't remove the root node")
        self.parent._children.remove(self)

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

class _Root_tree_node(Tree_node):
    """Variant of Tree_node used for a game root.

    Enforces the restrictions on changing SZ and CA.

    """
    def __init__(self, owner, properties, size, encoding):
        self.owner = owner
        self.parent = None
        self._children = []
        Node.__init__(self, properties, size, encoding)

class Sgf_game(object):
    """An SGF game.

    Instantiate with the board size, and optionally the property map encoding.

    FIXME: document property map encoding.

    """
    def _set_size(self, size):
        # This is split out for the sake of _Parsed_sgf_game.__init__
        if not 1 <= size <= 26:
            raise ValueError("size out of range: %s" % size)
        self.size = size

    def __init__(self, size, encoding="UTF-8"):
        try:
            encoding = normalise_charset_name(encoding)
        except LookupError:
            raise ValueError("unknown encoding: %s" % encoding)
        self._set_size(size)
        initial_properties = {
            'FF' : ["4"],
            'GM' : ["1"],
            'SZ' : [str(size)],
            'CA' : [encoding],
            }
        self.root = _Root_tree_node(self, initial_properties, size, encoding)

    def get_root(self):
        """Return the root node (as a Tree_node)."""
        return self.root

    def get_last_node(self):
        """Return the last node in the 'leftmost' variation (as a Tree_node)."""
        node = self.root
        while node:
            node = node[0]
        return node

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

        It's OK to use these Node instances to modify properties: even if they
        are not the same objects as returned by the main tree navigation
        methods, they share the underlying property maps.

        If you know the game has no variations, or you're only interested in
        the 'leftmost' variation, you can use this function to retrieve the
        nodes without building the entire game tree.

        """
        return self.get_main_sequence()

    def extend_main_sequence(self):
        """Create a new Tree_node and add to the 'leftmost' variation.

        Returns the new node.

        """
        return self.get_last_node().new_child()

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

    def set_date(self, date=None):
        """Set the DT property.

        date -- datetime.date (defaults to today)

        """
        if date is None:
            date = datetime.date.today()
        self.root.set('DT', date.strftime("%Y-%m-%d"))


class _Root_tree_node_for_game_tree(Tree_node):
    """Variant of _Root_tree_node used for _Parsed_sgf_game."""
    def __init__(self, owner, game_tree, size, encoding):
        self.owner = owner
        self.parent = None
        self._game_tree = game_tree
        self._children = None
        Node.__init__(self, game_tree.sequence[0], size, encoding)

    def _ensure_expanded(self):
        if self._children is None:
            self._children = []
            sgf_grammar.make_tree(
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

    def index(self, child):
        self._ensure_expanded()
        return self._children.index(child)

    def new_child(self):
        self._ensure_expanded()
        return Tree_node.new_child(self)

    def _main_sequence_iter(self):
        size = self.size
        encoding = self.encoding
        for properties in sgf_grammar.main_sequence_iter(self._game_tree):
            yield Node(properties, size, encoding)

class _Parsed_sgf_game(Sgf_game):
    """An Sgf_game which was loaded from serialised form.

    Do not instantiate directly; use sgf_game_from_string() or
    sgf_game_from_parsed_game_tree().

    """
    # This doesn't build the Tree_nodes (other than the root) until required.

    # It provides an implementation of main_sequence_iter() which reads
    # directly from the original Parsed_game_tree; this stops being used as
    # soon as the tree is expanded.

    def __init__(self, parsed_game):
        try:
            size_s = parsed_game.sequence[0]['SZ'][0]
        except KeyError:
            size = 19
        else:
            try:
                size = int(size_s)
            except ValueError:
                raise ValueError("bad SZ property: %s" % size_s)
        self._set_size(size)
        try:
            encoding = parsed_game.sequence[0]['CA'][0]
        except KeyError:
            encoding = "ISO-8859-1"
        else:
            try:
                encoding = normalise_charset_name(encoding)
            except LookupError:
                raise ValueError("unknown encoding: %s" % encoding)

        self.root = _Root_tree_node_for_game_tree(
            self, parsed_game, size, encoding)

    def main_sequence_iter(self):
        if self.root._game_tree is None:
            return self.get_main_sequence()
        return self.root._main_sequence_iter()

def sgf_game_from_parsed_game_tree(parsed_game):
    """Create an SGF game from the parser output.

    parsed_game -- Parsed_game_tree

    Returns an Sgf_game.

    The nodes' property maps (as returned by get_raw_property_map()) will be
    the same objects as the ones from the Parsed_game_tree.

    """
    return _Parsed_sgf_game(parsed_game)

def sgf_game_from_string(s):
    """Read a single SGF game from a string.

    s -- 8-bit string

    Returns an Sgf_game.

    Raises ValueError if it can't parse the string. See parse_sgf_game() for
    details.

    """
    return _Parsed_sgf_game(sgf_grammar.parse_sgf_game(s))


def serialise_sgf_game(sgf_game):
    """Serialise an SGF game as a string.

    Returns an 8-bit string.

    """
    game_tree = sgf_grammar.make_parsed_game_tree(
        sgf_game.get_root(), lambda node:node, Node.get_raw_property_map)
    return sgf_grammar.serialise_game_tree(game_tree)


def get_setup_and_moves(sgf_game):
    """Return the initial setup and the following moves from an Sgf_game.

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
    size = sgf_game.get_size()
    board = boards.Board(size)
    ab, aw, ae = sgf_game.get_root().get_setup_stones()
    if ab or aw:
        is_legal = board.apply_setup(ab, aw, ae)
        if not is_legal:
            raise ValueError("setup position not legal")
    moves = []
    nodes = iter(sgf_game.main_sequence_iter())
    nodes.next()
    for node in nodes:
        if node.has_setup_stones():
            raise ValueError("setup properties after the root node")
        colour, raw = node.get_raw_move()
        if colour is not None:
            moves.append((colour, sgf_properties.decode_point(raw, size)))
    return board, moves

def set_initial_position(sgf_game, board):
    """Add setup stones to an Sgf_game reflecting a board position.

    sgf_game -- Sgf_game
    board    -- boards.Board

    Replaces any existing setup stones in the Sgf_game's root node.

    """
    stones = {'b' : set(), 'w' : set()}
    for (colour, coords) in board.list_occupied_points():
        stones[colour].add(coords)
    sgf_game.get_root().set_setup_stones(stones['b'], stones['w'])

def indicate_first_player(sgf_game):
    """Add a PL property to the root node if appropriate.

    Looks at the first child of the root to see who the first player is, and
    sets PL it isn't the expected player (ie, black normally, but white if
    there is a handicap), or if there are non-handicap setup stones.

    """
    root = sgf_game.get_root()
    if not root:
        return
    first_player, move = root[0].get_move()
    if first_player is None:
        return
    has_handicap = root.has_property("HA")
    if root.has_property("AW"):
        specify_pl = True
    elif root.has_property("AB") and not has_handicap:
        specify_pl = True
    elif not has_handicap and first_player == 'w':
        specify_pl = True
    elif has_handicap and first_player == 'b':
        specify_pl = True
    else:
        specify_pl = False
    if specify_pl:
        root.set('PL', first_player)

