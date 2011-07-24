"""Represent SGF games.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

import datetime

from gomill import sgf_grammar
from gomill import sgf_properties


class Node(object):
    """An SGF node.

    Instantiate with a raw property map (see sgf_grammar) and an
    sgf_properties.Presenter.

    A Node doesn't belong to a particular game (cf Tree_node below), but it
    knows its board size (in order to interpret move values) and the encoding
    to use for the raw property strings.

    Changing the SZ or CA property isn't allowed.

    """
    __slots__ = ('_property_map', '_presenter')

    def __init__(self, property_map, presenter):
        # Map identifier (PropIdent) -> nonempty list of raw values
        self._property_map = property_map
        self._presenter = presenter

    def get_size(self):
        """Return the board size used to interpret property values."""
        return self._presenter.size

    def get_encoding(self):
        """Return the encoding used for raw property values.

        Returns a string (a valid Python codec name, eg "UTF-8").

        """
        return self._presenter.encoding

    def get_presenter(self):
        """Return the node's sgf_properties.Presenter."""
        return self._presenter

    def has_property(self, identifier):
        """Check whether the node has the specified property."""
        return identifier in self._property_map

    def properties(self):
        """Find the properties defined for the node.

        Returns a list of property identifiers, in unspecified order.

        """
        return self._property_map.keys()

    def get_raw_list(self, identifier):
        """Return the raw values of the specified property.

        Returns a list of 8-bit strings, in the raw property encoding.

        The strings contain the exact bytes that go between the square brackets
        (without interpreting escapes or performing any whitespace conversion).

        Raises KeyError if there was no property with the given identifier.

        (If the property is an empty elist, this returns a list containing a
        single empty string.)

        """
        return self._property_map[identifier]

    def get_raw(self, identifier):
        """Return a single raw value of the specified property.

        Returns an 8-bit string, in the raw property encoding.

        The string contains the exact bytes that go between the square brackets
        (without interpreting escapes or performing any whitespace conversion).

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
        if identifier == "SZ" and values != [str(self._presenter.size)]:
            raise ValueError("changing size is not permitted")
        if identifier == "CA":
            try:
                s = sgf_properties.normalise_charset_name(values[0])
            except LookupError:
                s = None
            if len(values) != 1 or s != self._presenter.encoding:
                raise ValueError("changing charset is not permitted")
        self._property_map[identifier] = values

    def unset(self, identifier):
        """Remove the specified property.

        Raises KeyError if the property isn't currently present.

        """
        if identifier == "SZ" and self._presenter.size != 19:
            raise ValueError("changing size is not permitted")
        if identifier == "CA" and self._presenter.encoding != "ISO-8859-1":
            raise ValueError("changing charset is not permitted")
        del self._property_map[identifier]


    def set_raw_list(self, identifier, values):
        """Set the raw values of the specified property.

        identifier -- ascii string passing is_valid_property_identifier()
        values     -- nonempty iterable of 8-bit strings in the raw property
                      encoding

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
        value      -- 8-bit string in the raw property encoding

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

        See sgf_properties.Presenter.interpret() for details.

        """
        return self._presenter.interpret(
            identifier, self._property_map[identifier])

    def set(self, identifier, value):
        """Set the value of the specified property.

        identifier -- ascii string passing is_valid_property_identifier()
        value      -- new property value (in its Python representation)

        For properties with value type 'none', use value True.

        Raises ValueError if it cannot represent the value.

        See sgf_properties.Presenter.serialise() for details.

        """
        self._set_raw_list(
            identifier, self._presenter.serialise(identifier, value))

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
        return (colour,
                sgf_properties.interpret_go_point(raw, self._presenter.size))

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
        Node.__init__(self, properties, parent._presenter)

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
    """Variant of Tree_node used for a game root."""
    def __init__(self, owner):
        self.owner = owner
        self.parent = None
        self._children = []
        Node.__init__(self, {}, owner.presenter)

class Sgf_game(object):
    """An SGF game.

    Instantiate with
      size     -- int (board size), in range 1 to 26
      encoding -- the raw property encoding (default "UTF-8")

    'encoding' must be a valid Python codec name.

    The following root node properties are initially set:
      FF[4]
      GM[1]
      SZ[size]
      CA[encoding]

    Changing FF and GM is permitted (but this library will carry on using the
    FF[4] and GM[1] rules). Changing SZ and CA is not allowed (unless the
    change leaves the effective value unchanged).

    """
    def _initialise_presenter(self, size, encoding):
        # This is split out for the sake of _Parsed_sgf_game.__init__
        if not 1 <= size <= 26:
            raise ValueError("size out of range: %s" % size)
        self.size = size
        self.presenter = sgf_properties.Presenter(size, encoding)

    def __init__(self, size, encoding="UTF-8"):
        self._initialise_presenter(size, encoding)
        self.root = _Root_tree_node(self)
        self.root.set_raw('FF', "4")
        self.root.set_raw('GM', "1")
        self.root.set_raw('SZ', str(size))
        # Read the encoding back so we get the normalised form
        self.root.set_raw('CA', self.presenter.encoding)

    def get_property_presenter(self):
        """Return the property presenter.

        Returns an sgf_properties.Presenter.

        This can be used to customise how property values are interpreted and
        serialised.

        """
        return self.presenter

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

        Returns 0.0 if the KM property isn't present in the root node.

        Raises ValueError if the KM property is malformed.

        """
        try:
            return self.root.get("KM")
        except KeyError:
            return 0.0

    def get_handicap(self):
        """Return the number of handicap stones as a small integer.

        Returns None if the HA property isn't present, or has (illegal) value
        zero.

        Raises ValueError if the HA property is otherwise malformed.

        """
        try:
            handicap = self.root.get("HA")
        except KeyError:
            return None
        if handicap == 0:
            handicap = None
        elif handicap == 1:
            raise ValueError
        return handicap

    def get_player(self, colour):
        """Return the name of the specified player.

        Returns None if there is no corresponding 'PB' or 'PW' property.

        """
        try:
            return self.root.get({'b' : 'PB', 'w' : 'PW'}[colour])
        except KeyError:
            return None

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
        """Set the DT property to a single date.

        date -- datetime.date (defaults to today)

        (SGF allows dates to be rather more complicated than this, so there's
         no corresponding get_date() method.)

        """
        if date is None:
            date = datetime.date.today()
        self.root.set('DT', date.strftime("%Y-%m-%d"))


class _Root_tree_node_for_game_tree(Tree_node):
    """Variant of _Root_tree_node used for _Parsed_sgf_game."""
    def __init__(self, owner, game_tree):
        self.owner = owner
        self.parent = None
        self._game_tree = game_tree
        self._children = None
        Node.__init__(self, game_tree.sequence[0], owner.presenter)

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
        presenter = self._presenter
        for properties in sgf_grammar.main_sequence_iter(self._game_tree):
            yield Node(properties, presenter)

class _Parsed_sgf_game(Sgf_game):
    """An Sgf_game which was loaded from serialised form.

    Do not instantiate directly; use sgf_game_from_string() or
    sgf_game_from_parsed_game_tree().

    """
    # This doesn't build the Tree_nodes (other than the root) until required.

    # It provides an implementation of main_sequence_iter() which reads
    # directly from the original Parsed_game_tree; this stops being used as
    # soon as the tree is expanded.

    def __init__(self, parsed_game, override_encoding=None):
        try:
            size_s = parsed_game.sequence[0]['SZ'][0]
        except KeyError:
            size = 19
        else:
            try:
                size = int(size_s)
            except ValueError:
                raise ValueError("bad SZ property: %s" % size_s)
        if override_encoding is None:
            try:
                encoding = parsed_game.sequence[0]['CA'][0]
            except KeyError:
                encoding = "ISO-8859-1"
        else:
            encoding = override_encoding
        self._initialise_presenter(size, encoding)
        self.root = _Root_tree_node_for_game_tree(self, parsed_game)
        if override_encoding is not None:
            self.root.set_raw("CA", self.presenter.encoding)

    def main_sequence_iter(self):
        if self.root._game_tree is None:
            return self.get_main_sequence()
        return self.root._main_sequence_iter()

def sgf_game_from_parsed_game_tree(parsed_game, override_encoding=None):
    """Create an SGF game from the parser output.

    parsed_game       -- Parsed_game_tree
    override_encoding -- encoding name, eg "UTF-8" (optional)

    Returns an Sgf_game.

    The nodes' property maps (as returned by get_raw_property_map()) will be
    the same objects as the ones from the Parsed_game_tree.

    The board size and raw property encoding are taken from the SZ and CA
    properties in the root node (defaulting to 19 and "ISO-8859-1",
    respectively).

    If override_encoding is specified, the source data is assumed to be in the
    specified encoding (no matter what the CA property says), and the CA
    property is set to match.

    """
    return _Parsed_sgf_game(parsed_game, override_encoding)

def sgf_game_from_string(s, override_encoding=None):
    """Read a single SGF game from a string.

    s -- 8-bit string

    Returns an Sgf_game.

    Raises ValueError if it can't parse the string. See parse_sgf_game() for
    details.

    See sgf_game_from_parsed_game_tree for details of size and encoding
    handling.

    """
    return _Parsed_sgf_game(sgf_grammar.parse_sgf_game(s), override_encoding)


def serialise_sgf_game(sgf_game):
    """Serialise an SGF game as a string.

    Returns an 8-bit string, in the encoding specified by the CA property in
    the root node (defaulting to "ISO-8859-1").

    """
    # We can use the raw properties directly, because at present the raw
    # property encoding always matches the CA property.
    game_tree = sgf_grammar.make_parsed_game_tree(
        sgf_game.get_root(), lambda node:node, Node.get_raw_property_map)
    return sgf_grammar.serialise_game_tree(game_tree)

