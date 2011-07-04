"""Represent SGF games.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

from gomill import boards
from gomill import sgf_parser
from gomill import sgf_values


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

    def get_raw_list(self, identifier):
        """Return the raw values of the specified property.

        Returns a list of 8-bit strings, containing the exact bytes that were
        between the square brackets (without interpreting escapes or performing
        any whitespace conversion).

        Raises KeyError if there was no property with the given identifier.

        (If the property is an empty elist, this returns a list containing a
        single empty string.)

        """
        return self.props_by_id[identifier]

    def get_raw(self, identifier):
        """Return a single raw value of the specified property.

        Returns an 8-bit string, containing the exact bytes that were between
        the square brackets (without interpreting escapes or performing any
        whitespace conversion).

        Raises KeyError if there was no property with the given identifier.

        If the property has multiple values, this returns the first (if the
        value is an empty elist, this returns an empty string).

        """
        return self.props_by_id[identifier][0]

    def get(self, identifier):
        """Return the interpreted value of the specified property.

        Returns the value as a suitable Python representation.

        Raises KeyError if the node does not have a property with the given
        identifier.

        Raises ValueError if it cannot interpret the value.

        See sgf_values.get_interpreted_value() for details.


        """
        return sgf_values.get_interpreted_value(
            identifier, self.props_by_id[identifier], self.size)

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
        return colour, sgf_values.interpret_point(raw, self.size)

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

    Do not instantiate directly; retrieve from an Sgf_game or another Tree_node.

    A Tree_node is a list-like container of its children: it can be indexed,
    sliced, and iterated over like a list. A Tree_node with no children is
    treated as having truth value false.

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

def sgf_game_from_string(s):
    """Read a single SGF game from a string.

    s -- 8-bit string

    Returns an Sgf_game.

    Raises ValueError if it can't parse the string. See parse_sgf_game() for
    details.

    """
    return Sgf_game(sgf_parser.parse_sgf_game(s))



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
    ab, aw, ae = sgf_game.get_root().get_setup_commands()
    if ab or aw:
        is_legal = board.apply_setup(ab, aw, ae)
        if not is_legal:
            raise ValueError("setup position not legal")
    moves = []
    nodes = sgf_game.main_sequence_iter()
    nodes.next()
    for node in nodes:
        if node.has_setup_commands():
            raise ValueError("setup commands after the root node")
        colour, raw = node.get_raw_move()
        if colour is not None:
            moves.append((colour, sgf_values.interpret_point(raw, size)))
    return board, moves

