"""FIXME"""

def escape_text(s):
    """Convert a string to a raw Text property value that represents it.

    s -- 8-bit string

    Returns an 8-bit string which passes is_valid_property_value().

    Normally text_value(escape_text(s)) == s, but there are the following
    exceptions:
     - all linebreaks are are normalised to \n
     - whitespace other than line breaks is converted to a single space

    """
    return s.replace("\\", "\\\\").replace("]", "\\]")

class Serialisable_game_tree(object):
    """FIXME

    """
    def __init__(self):
        self.sequence = []
        self.children = []

def make_serialisable_tree(root, get_children, get_properties):
    """Construct a Serialisable_game_tree from a node tree.

    root           -- node
    get_children   -- function taking a node, returning a sequence of nodes
    get_properties -- function taking a node, returning a property map

    Returns a Serialisable_game_tree.

    Walks the node tree using get_children(), and uses get_properties() to
    extract the raw properties.

    Makes no further assumptions about the node type.

    """
    result = Serialisable_game_tree()
    to_serialise = [(result, root)]
    while to_serialise:
        game_tree, node = to_serialise.pop()
        while True:
            game_tree.sequence.append(get_properties(node))
            children = get_children(node)
            if len(children) != 1:
                break
            node = children[0]
        for child in children:
            child_tree = Serialisable_game_tree()
            game_tree.children.append(child_tree)
            to_serialise.append((child_tree, child))
    return result

def block_format(pieces, width=79):
    """Concatenate strings, adding newlines.

    pieces -- iterable of strings
    width  -- int (default 79)

    Returns "".join(pieces), with added newlines between pieces as necessary to
    avoid lines longer than 'width'.

    Leaves newlines inside 'pieces' untouched, and ignores them in its width
    calculation. If a single piece is longer than 'width', it will become a
    single long line in the output.

    """
    lines = []
    line = ""
    for s in pieces:
        if len(line) + len(s) > width:
            lines.append(line)
            line = ""
        line += s
    if line:
        lines.append(line)
    return "\n".join(lines)

def serialise_sgf_game(game_tree):
    """Serialise an SGF game as a string.

    game_tree -- Serialisable_game_tree

    Returns an 8-bit string, ending with a newline.

    """
    l = []
    to_serialise = [game_tree]
    while to_serialise:
        game_tree = to_serialise.pop()
        if game_tree is None:
            l.append(")")
            continue
        l.append("(")
        for properties in game_tree.sequence:
            l.append(";")
            for prop_ident, prop_values in sorted(properties.iteritems()):
                # Make a single string for each property, to get prettier
                # block_format output.
                m = [prop_ident]
                for value in prop_values:
                    m.append("[%s]" % value)
                l.append("".join(m))
        to_serialise.append(None)
        to_serialise.extend(reversed(game_tree.children))
    l.append("\n")
    return block_format(l)

