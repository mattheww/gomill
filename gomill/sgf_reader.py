"""Read sgf files."""

def escape(s):
    return s.replace("\\", "\\\\").replace("]", "\\]")

def interpret_point(s, size):
    s = s.lower()
    if s == "tt":
        return None
    col_s, row_s = s
    col = ord(col_s) - ord("a")
    row = ord(row_s) - ord("a")
    row = size - row - 1
    return row, col

class Sgf_scanner(object):
    def __init__(self, s):
        self.chars = s
        self.index = 0

    def peek(self):
        return self.chars[self.index]

    def skip(self):
        self.index += 1

    def skip_space(self):
        while self.chars[self.index].isspace():
            self.index += 1

    def expect(self, c):
        self.skip_space()
        if self.chars[self.index] != c:
            raise ValueError
        self.index += 1

    def skip_until(self, c):
        while self.chars[self.index] != c:
            self.index += 1
        self.index += 1

    def scan_prop_ident(self):
        self.skip_space()
        start = self.index
        while True:
            i = self.index
            c = self.chars[i]
            if c.isspace():
                self.skip_space()
                if self.chars[self.index] == "[":
                    break
                else:
                    raise ValueError
            elif c == "[":
                break
            self.index += 1
        return self.chars[start:i]

    def scan_prop_value(self):
        start = self.index
        is_escaped = False
        result = []
        while True:
            c = self.chars[self.index]
            if is_escaped:
                if c != "\n":
                    result.append(c)
                self.index += 1
                is_escaped = False
                continue
            if c == "\\":
                is_escaped = True
                self.index += 1
                continue
            if c == "]":
                break
            if c != "\n" and c.isspace():
                c = " "
            result.append(c)
            self.index += 1
        return "".join(result)

class Prop(object):
    """An SGF property.

    Property values are 8-bit strings in the source encoding.

    """

    def __init__(self, identifier, value):
        self.identifier = identifier.upper()
        self.value = value

    def __str__(self):
        return "%s[%s]" % (self.identifier, escape(self.value))

class Node(object):
    """An SGF node."""

    def __init__(self, owner):
        # Owning SGF file: used to find board size to interpret moves.
        self.owner = owner
        self.prop_list = []
        self.props_by_id = {}

    def add(self, prop):
        self.prop_list.append(prop)
        self.props_by_id[prop.identifier] = prop

    def get(self, identifier):
        return self.props_by_id[identifier].value

    def has_prop(self, identifier):
        return identifier in self.props_by_id

    def get_props(self):
        return self.prop_list[:]

    def get_move(self):
        """Retrieve the move from a node.

        Returns a pair (colour, coords)

        colour is 'b' or 'w'.

        coords are (row, col), using GTP standard coordinates, or None for a
        pass.

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
        return colour, interpret_point(prop.value, size)

    def __str__(self):
        return "\n".join(str(p) for p in self.prop_list)


class Sgf_game_tree(object):
    """An SGF game tree.

    Public attributes:
      nodes -- list of Node objects

    """

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
        return int(self.get_root_prop("SZ"))

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

    def get_player(self, colour):
        return self.get_root_prop({'b' : 'PB', 'w' : 'PW'}[colour])

    def get_winner(self):
        try:
            colour = self.get_root_prop("RE")[0].lower()
        except LookupError:
            return None
        if colour not in ("b", "w"):
            return None
        return colour


def read_sgf(s):
    """Interpret an SGF file from a string.

    Returns an Sgf_game_tree.

    Ignores everything in the string before the first open-paren.

    Reads only the first sequence from the first game in the string (ie, any
    variations are ignored).

    Raises ValueError if can't parse the string.

    The string should use LF to represent a line break.

    This doesn't know the types of different properties; all values are
    interpreted as if they were Text.

    FIXME: Doesn't handle lists of points (eg, AB or TB).

    """
    scanner = Sgf_scanner(s)
    result = Sgf_game_tree()
    try:
        scanner.skip_until("(")
        scanner.expect(";")
        node = result.new_node()
        while True:
            scanner.skip_space()
            c = scanner.peek()
            if c == ")":
                break
            if c == "(":
                scanner.skip()
                continue
            if c == ";":
                scanner.skip()
                node = result.new_node()
            prop_ident = scanner.scan_prop_ident()
            #print "pi:", repr(prop_ident)
            scanner.expect("[")
            prop_value = scanner.scan_prop_value()
            #print "pv:", repr(prop_value)
            scanner.expect("]")
            node.add(Prop(prop_ident, prop_value))
    except IndexError:
        raise ValueError
    return result

