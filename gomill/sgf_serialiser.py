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

def make_serialisable_tree(root_node):
    """FIXME"""
    result = Serialisable_game_tree()
    to_serialise = [(result, root_node)]
    while to_serialise:
        game_tree, node = to_serialise.pop()
        property_map = node.props_by_id # FIXME
        game_tree.sequence.append(property_map)
        while len(node) == 1:
            node = node[0]
            property_map = node.props_by_id # FIXME
            game_tree.sequence.append(property_map)
        for child in node:
            child_tree = Serialisable_game_tree()
            game_tree.children.append(child_tree)
            to_serialise.append((child_tree, child))
    return result

def block_format(l, width=79):
    """FIXME"""
    lines = []
    line = ""
    for s in l:
        if len(line) + len(s) > width:
            lines.append(line)
            line = ""
        line += s
    if line:
        lines.append(line)
    return "\n".join(lines)


def serialise_sgf_game(game_tree):
    """FIXME

    game_tree -- Serialisable_game_tree

    Returns an 8-bit string

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
                l.append(prop_ident)
                for value in prop_values:
                    l.append("[%s]" % value)
        to_serialise.append(None)
        to_serialise.extend(reversed(game_tree.children))

    return block_format(l)

