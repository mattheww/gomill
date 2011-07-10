"""Parse SGF data.

This is intended for use with SGF FF[4]; see http://www.red-bean.com/sgf/

Nothing in this module is Go-specific.

"""

import re
import string


_propident_re = re.compile(r"\A[A-Z]{1,8}\Z")
_propvalue_re = re.compile(r"\A [^\\\]]* (?: \\. [^\\\]]* )* \Z",
                           re.VERBOSE | re.DOTALL)
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


def is_valid_property_identifier(s):
    """Check whether 's' is a well-formed PropIdent.

    s -- 8-bit string

    This accepts the same values as the tokeniser.

    Details:
     - it doesn't permit lower-case letters (these are allowed in some ancient
       SGF variants)
     - it accepts at most 8 letters (there is no limit in the spec; no standard
       property has more than 2)

    """
    return bool(_propident_re.search(s))

def is_valid_property_value(s):
    """Check whether 's' is a well-formed PropValue.

    s -- 8-bit string

    This accepts the same values as the tokeniser: any string that doesn't
    contain an unescaped ] or end with an unescaped \ .

    """
    return bool(_propvalue_re.search(s))

def tokenise(s, start_position=0):
    """Tokenise a string containing SGF data.

    s              -- 8-bit string
    start_position -- index into 's'

    Skips leading junk.

    Returns a list of pairs of strings (token type, contents), and also the
    index in 's' of the start of the unprocessed 'tail'.

    token types and contents:
      I -- PropIdent: upper-case letters
      V -- PropValue: raw value, without the enclosing brackets
      D -- delimiter: ';', '(', or ')'

    Stops when it has seen as many closing parens as open ones, at the end of
    the string, or when it first finds something it can't tokenise.

    The first two tokens are always '(' and ';' (otherwise it won't find the
    start of the content).

    """
    result = []
    m = _find_start_re.search(s, start_position)
    if not m:
        return [], 0
    i = m.start()
    depth = 0
    while True:
        m = _tokenise_re.match(s, i)
        if not m:
            break
        group = m.lastgroup
        token = m.group(m.lastindex)
        result.append((group, token))
        i = m.end()
        if group == 'D':
            if token == '(':
                depth += 1
            elif token == ')':
                depth -= 1
                if depth == 0:
                    break
    return result, i

class Parsed_game_tree(object):
    """An SGF GameTree.

    This is a direct representation of the SGF parse tree. The 'children'
    represent variations, not individual nodes.

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

def _parse_sgf_game(s, start_position):
    """Common implementation for parse_sgf_game and parse_sgf_games."""
    tokens, end_position = tokenise(s, start_position)
    if not tokens:
        return None, None
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
    assert index == len(tokens)
    return variation, end_position

def parse_sgf_game(s):
    """Read a single SGF game from a string, returning the parse tree.

    s -- 8-bit string

    Returns a Parsed_game_tree.

    Applies the rules for FF[4].

    Raises ValueError if can't parse the string.

    If a property appears more than once in a node (which is not permitted by
    the spec), treats it the same as a single property with multiple values.


    Identifies the start of the SGF content by looking for '(;' (with possible
    whitespace between); ignores everything preceding that. Ignores everything
    following the first game.

    """
    game_tree, _ = _parse_sgf_game(s, 0)
    if game_tree is None:
        raise ValueError("no SGF data found")
    return game_tree

def parse_sgf_collection(s):
    """Read an SGF game collection, returning the parse trees.

    s -- 8-bit string

    Returns a nonempty list of Parsed_game_trees.

    Raises ValueError if no games were found in the string.

    Raises ValueError if there is an error parsing a game. See
    parse_sgf_game() for details.


    Ignores non-SGF data before the first game, between games, and after the
    final game. Identifies the start of each game in the same way as
    parse_sgf_game().

    """
    position = 0
    result = []
    while True:
        try:
            game_tree, position = _parse_sgf_game(s, position)
        except ValueError, e:
            raise ValueError("error parsing game %d: %s" % (len(result), e))
        if game_tree is None:
            break
        result.append(game_tree)
    if not result:
        raise ValueError("no SGF data found")
    return result


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


_split_compose_re = re.compile(
    r"( (?: [^\\:] | \\. )* ) :",
    re.VERBOSE | re.DOTALL)

def parse_compose(s):
    """Split the parts of an SGF Compose value.

    If the value is a well-formed Compose, returns a pair of strings.

    If it isn't (ie, there is no delimiter), returns the complete string and
    None.

    Interprets backslash escapes in order to find the delimiter, but leaves
    backslash escapes unchanged in the returned strings.

    """
    m = _split_compose_re.match(s)
    if not m:
        return s, None
    return m.group(1), s[m.end():]


_newline_re = re.compile(r"\n\r|\r\n|\n|\r")
_whitespace_table = string.maketrans("\t\f\v", "   ")
_chunk_re = re.compile(r" [^\n\\]+ | [\n\\] ", re.VERBOSE)

def simpletext_value(s):
    """Convert a raw SimpleText property value to the string it represents.

    Returns an 8-bit string, in the encoding of the original SGF string.

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

def text_value(s):
    """Convert a raw Text property value to the string it represents.

    Returns an 8-bit string, in the encoding of the original SGF string.

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

