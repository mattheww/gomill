"""Parse SGF data.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

"""

import re

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

def tokenise(s):
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

class Parsed_game_tree(object):
    """An SGF GameTree.

    This is a direct representation of the SGF parse tree. The 'children' are
    variations, not nodes.

    Public attributes
      sequence -- nonempty list of property maps
      children -- list of Parsed_game_trees

    The sequence represents the nodes before the variations.

    A property map is a dict mapping a PropIdent to a nonempty list of raw
    property values.

    A raw property value is an 8-bit string containing a PropValue without its
    enclosing brackets, but with backslashes and line endings left untouched.

    """
    def __init__(self):
        self.sequence = [] # must be at least one node
        self.children = [] # may be empty

def parse_sgf_game(s):
    """Read a single SGF game from a string, returning the parse tree.

    s -- 8-bit string

    Returns a Parsed_game_tree.

    Identifies the start of the SGF content by looking for '(;' (with possible
    whitespace between); ignores everything preceding that. Ignores everything
    following the first game.

    Applies the rules for FF[4].

    Raises ValueError if can't parse the string.

    """
    tokens, _ = tokenise(s)
    if not tokens:
        raise ValueError("no SGF data found")
    stack = []
    game_tree = None
    sequence = None
    properties = None
    index = 0
    try:
        while True:
            token_type, token = tokens[index]
            index += 1
            if token_type == 'V':
                raise ValueError("unexpected value")
            if token_type == 'D':
                if token == ';':
                    if sequence is None:
                        raise ValueError("unexpected node")
                    properties = {}
                    sequence.append(properties)
                else:
                    if sequence is not None:
                        if not sequence:
                            raise ValueError("empty sequence")
                        game_tree.sequence = sequence
                        sequence = None
                    if token == '(':
                        stack.append(game_tree)
                        game_tree = Parsed_game_tree()
                        sequence = []
                    else:
                        # token == ')'
                        variation = game_tree
                        game_tree = stack.pop()
                        if game_tree is None:
                            break
                        game_tree.children.append(variation)
                    properties = None
            else:
                # token_type == 'I'
                prop_ident = token
                prop_values = []
                while True:
                    token_type, token = tokens[index]
                    if token_type != 'V':
                        break
                    index += 1
                    prop_values.append(token)
                if not prop_values:
                    raise ValueError("property with no values")
                try:
                    if prop_ident in properties:
                        properties[prop_ident] += prop_values
                    else:
                        properties[prop_ident] = prop_values
                except TypeError:
                    raise ValueError("property value outside a node")
    except IndexError:
        raise ValueError("unexpected end of SGF data")
    return variation


def make_tree(game_tree, root, node_builder, node_adder):
    """Construct a node tree from a Parsed_game_tree.

    game_tree    -- Parsed_game_tree
    root         -- node
    node_builder -- function taking parameters (parent node, property map)
                    returning a node
    node_adder   -- function taking a pair (parent node, child node)

    Builds a tree of nodes corresponding to this GameTree, calling
    node_builder() to make new nodes and node_adder() to add child nodes to
    their parent.

    Makes no further assumptions about the node type.

    """
    to_build = [(root, game_tree, 0)]
    while to_build:
        node, game_tree, index = to_build.pop()
        if index < len(game_tree.sequence) - 1:
            child = node_builder(node, game_tree.sequence[index+1])
            node_adder(node, child)
            to_build.append((child, game_tree, index+1))
        else:
            node._children = []
            for child_tree in game_tree.children:
                child = node_builder(node, child_tree.sequence[0])
                node_adder(node, child)
                to_build.append((child, child_tree, 0))

def main_sequence_iter(game_tree):
    """Provide the 'leftmost' complete sequence of a Parsed_game_tree.

    game_tree -- Parsed_game_tree

    Returns an iterable of property maps.

    If the game has no variations, this provides the complete game. Otherwise,
    it chooses the first variation each time it has a choice.

    """
    while True:
        for properties in game_tree.sequence:
            yield properties
        if not game_tree.children:
            break
        game_tree = game_tree.children[0]
