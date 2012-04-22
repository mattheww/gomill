SGF support
-----------

.. module:: gomill.sgf
   :synopsis: High level SGF interface.

.. versionadded:: 0.7

Gomill's |sgf| support is intended for use with version FF[4], which is
specified at http://www.red-bean.com/sgf/index.html. It has support for the
game-specific properties for Go, but not those of other games. Point, Move and
Stone values are interpreted as Go points.

The :mod:`gomill.sgf` module provides the main support. This module is
independent of the rest of Gomill.

The :mod:`gomill.sgf_moves` module contains some higher-level functions for
processing moves and positions, and provides a link to the
:mod:`.boards` module.

The :mod:`!gomill.sgf_grammar` and :mod:`!gomill.sgf_properties` modules are
used to implement the :mod:`!sgf` module, and are not currently documented.


.. contents:: Page contents
   :local:
   :backlinks: none

Examples
^^^^^^^^

Reading and writing::

  >>> from gomill import sgf
  >>> g = sgf.Sgf_game.from_string("(;FF[4]GM[1]SZ[9];B[ee];W[ge])")
  >>> g.get_size()
  9
  >>> root_node = g.get_root()
  >>> root_node.get("SZ")
  9
  >>> root_node.get_raw("SZ")
  '9'
  >>> root_node.set("RE", "B+R")
  >>> new_node = g.extend_main_sequence()
  >>> new_node.set_move("b", (2, 3))
  >>> [node.get_move() for node in g.get_main_sequence()]
  [(None, None), ('b', (4, 4)), ('w', (4, 6)), ('b', (2, 3))]
  >>> g.serialise()
  '(;FF[4]GM[1]RE[B+R]SZ[9];B[ee];W[ge];B[dg])\n'


Recording a game::

  g = sgf.Sgf_game(size=13)
  for move_info in ...:
      node = g.extend_main_sequence()
      node.set_move(move_info.colour, move_info.move)
      if move_info.comment is not None:
          node.set("C", move_info.comment)
  with open(pathname, "w") as f:
      f.write(g.serialise())

See also the :script:`show_sgf.py` and :script:`split_sgf_collection.py`
example scripts.


Sgf_game objects
^^^^^^^^^^^^^^^^

|sgf| data is represented using :class:`!Sgf_game` objects. Each object
represents the data for a single |sgf| file (corresponding to a ``GameTree``
in the |sgf| spec). This is typically used to represent a single game,
possibly with variations (but it could be something else, such as a problem
set).

An :class:`!Sgf_game` can either be created from scratch or loaded from a
string.

To create one from scratch, instantiate an :class:`!Sgf_game` object directly:

.. class:: Sgf_game(size, encoding="UTF-8"])

   *size* is an integer from 1 to 26, indicating the board size.

   The optional *encoding* parameter specifies the :ref:`raw property encoding
   <raw_property_encoding>` to use for the game.

When a game is created this way, the following root properties are initially
set: :samp:`FF[4]`, :samp:`GM[1]`, :samp:`SZ[{size}]`, and
:samp:`CA[{encoding}]`.

To create a game from existing |sgf| data, use the
:func:`!Sgf_game.from_string` classmethod:

.. classmethod:: Sgf_game.from_string(s[, override_encoding=None])

   :rtype: :class:`!Sgf_game`

   Creates an :class:`!Sgf_game` from the |sgf| data in *s*, which must be an
   8-bit string.

   The board size and :ref:`raw property encoding <raw_property_encoding>` are
   taken from the ``SZ`` and ``CA`` properties in the root node (defaulting to
   ``19`` and ``"ISO-8859-1"``, respectively). Board sizes greater than ``26``
   are rejected.

   If *override_encoding* is present, the source data is assumed to be in the
   encoding it specifies (no matter what the ``CA`` property says), and the
   ``CA`` property and raw property encoding are changed to match.

   Raises :exc:`ValueError` if it can't parse the string, or if the ``SZ`` or
   ``CA`` properties are unacceptable. No error is reported for other
   malformed property values. See also :ref:`parsing_details` below.

   Example::

     g = sgf.Sgf_game.from_string(
         "(;FF[4]GM[1]SZ[9]CA[UTF-8];B[ee];W[ge])",
         override_encoding="iso8859-1")


To retrieve the |sgf| data as a string, use the :meth:`!serialise` method:

.. method:: Sgf_game.serialise([wrap])

   :rtype: string

   Produces the |sgf| representation of the data in the :class:`!Sgf_game`.

   Returns an 8-bit string, in the encoding specified by the ``CA`` root
   property (defaulting to ``"ISO-8859-1"``).

   See :ref:`transcoding <transcoding>` below for details of the behaviour if
   the ``CA`` property is changed from its initial value.

   This makes some effort to keep the output line length to no more than 79
   bytes. Pass ``None`` in the *wrap* parameter to disable this behaviour, or
   pass an integer to specify a different limit.


The complete game tree is represented using :class:`Tree_node` objects, which
are used to access the |sgf| properties. An :class:`!Sgf_game` always has at
least one node, the :dfn:`root node`.

.. method:: Sgf_game.get_root()

   :rtype: :class:`Tree_node`

   Returns the root node of the game tree.

The root node contains global properties for the game tree, and typically also
contains *game-info* properties. It sometimes also contains *setup* properties
(for example, if the game does not begin with an empty board).

Changing the ``FF`` and ``GM`` properties is permitted, but Gomill will carry
on using the FF[4] and GM[1] (Go) rules. Changing ``SZ`` is not permitted (but
if the size is 19 you may remove the property). Changing ``CA`` is permitted
(this controls the encoding used by :meth:`~Sgf_game.serialise`).


.. rubric:: Convenience methods for tree access

The complete game tree can be accessed through the root node, but the
following convenience methods are also provided. They return the same
:class:`Tree_node` objects that would be reached via the root node.

Some of the convenience methods are for accessing the :dfn:`leftmost`
variation of the game tree. This is the variation which appears first in the
|sgf| ``GameTree``, often shown in graphical editors as the topmost horizontal
line of nodes. In a game tree without variations, the leftmost variation is
just the whole game.


.. method:: Sgf_game.get_last_node()

   :rtype: :class:`Tree_node`

   Returns the last (leaf) node in the leftmost variation.

.. method:: Sgf_game.get_main_sequence()

   :rtype: list of :class:`Tree_node` objects

   Returns the complete leftmost variation. The first element is the root
   node, and the last is a leaf.

.. method:: Sgf_game.get_main_sequence_below(node)

   :rtype: list of :class:`Tree_node` objects

   Returns the leftmost variation beneath the :class:`Tree_node` *node*. The
   first element is the first child of *node*, and the last is a leaf.

   Note that this isn't necessarily part of the leftmost variation of the
   game as a whole.

.. method:: Sgf_game.get_main_sequence_above(node)

   :rtype: list of :class:`Tree_node` objects

   Returns the partial variation leading to the :class:`Tree_node` *node*. The
   first element is the root node, and the last is the parent of *node*.

.. method:: Sgf_game.extend_main_sequence()

   :rtype: :class:`Tree_node`

   Creates a new :class:`Tree_node`, adds it to the leftmost variation, and
   returns it.

   This is equivalent to
   :meth:`get_last_node`\ .\ :meth:`~Tree_node.new_child`


.. rubric:: Convenience methods for root properties

The following methods provide convenient access to some of the root node's
|sgf| properties. The main difference between using these methods and using
:meth:`~Tree_node.get` on the root node is that these methods return the
appropriate default value if the property is not present.

.. method:: Sgf_game.get_size()

   :rtype: integer

   Returns the board size (``19`` if the ``SZ`` root property isn't present).

.. method:: Sgf_game.get_charset()

   :rtype: string

   Returns the effective value of the ``CA`` root property (``ISO-8859-1`` if
   the ``CA`` root property isn't present).

   The returned value is a codec name in normalised form, which may not be
   identical to the string returned by ``get_root().get("CA")``. Raises
   :exc:`ValueError` if the property value doesn't identify a Python codec.

   This gives the encoding that would be used by :meth:`serialise`. It is not
   necessarily the same as the :ref:`raw property encoding
   <raw_property_encoding>` (use :meth:`~Tree_node.get_encoding` on the root
   node to retrieve that).


.. method:: Sgf_game.get_komi()

   :rtype: float

   Returns the :term:`komi` (``0.0`` if the ``KM`` root property isn't
   present).

   Raises :exc:`ValueError` if the ``KM`` root property is present but
   malformed.

.. method:: Sgf_game.get_handicap()

   :rtype: integer or ``None``

   Returns the number of handicap stones.

   Returns ``None`` if the ``HA`` root property isn't present, or if it has
   value zero (which isn't strictly permitted).

   Raises :exc:`ValueError` if the ``HA`` property is otherwise malformed.

.. method:: Sgf_game.get_player_name(colour)

   :rtype: string or ``None``

   Returns the name of the specified player, or ``None`` if the required
   ``PB`` or ``PW`` root property isn't present.

.. method:: Sgf_game.get_winner()

   :rtype: *colour*

   Returns the colour of the winning player.

   Returns ``None`` if the ``RE`` root property isn't present, or if neither
   player won.

.. method:: Sgf_game.set_date([date])

   Sets the ``DT`` root property, to a single date.

   If *date* is specified, it should be a :class:`datetime.date`. Otherwise
   the current date is used.

   (|sgf| allows ``DT`` to be rather more complicated than a single date, so
   there's no corresponding get_date() method.)


Tree_node objects
^^^^^^^^^^^^^^^^^

.. class:: Tree_node

   A Tree_node object represents a single node from an |sgf| file.

   Don't instantiate Tree_node objects directly; retrieve them from
   :class:`Sgf_game` objects.

   Tree_node objects have the following attributes (which should be treated as
   read-only):

   .. attribute:: owner

      The :class:`Sgf_game` that the node belongs to.

   .. attribute:: parent

      The node's parent :class:`!Tree_node` (``None`` for the root node).


.. rubric:: Tree navigation

A :class:`!Tree_node` acts as a list-like container of its children: it can be
indexed, sliced, and iterated over like a list, and it supports the `index`__
method. A :class:`!Tree_node` with no children is treated as having truth
value false. For example, to find all leaf nodes::

  def print_leaf_comments(node):
      if node:
          for child in node:
              print_leaf_comments(child)
      else:
          if node.has_property("C"):
              print node.get("C")
          else:
              print "--"

.. __: http://docs.python.org/release/2.7/library/stdtypes.html#mutable-sequence-types


.. rubric:: Property access

Each node holds a number of :dfn:`properties`. Each property is identified by
a short string called the :dfn:`PropIdent`, eg ``"SZ"`` or ``"B"``. See
:ref:`sgf_property_list` below for a list of the standard properties. See the
:term:`SGF` specification for full details. See :ref:`parsing_details` below
for restrictions on well-formed *PropIdents*.

Gomill doesn't enforce |sgf|'s restrictions on where properties can appear
(eg, the distinction between *setup* and *move* properties).

The principal methods for accessing the node's properties are:

.. method:: Tree_node.get(identifier)

   Returns a native Python representation of the value of the property whose
   *PropIdent* is *identifier*.

   Raises :exc:`KeyError` if the property isn't present.

   Raises :exc:`ValueError` if it detects that the property value is
   malformed.

   See :ref:`sgf_property_types` below for details of how property values are
   represented in Python.

   See :ref:`sgf_property_list` below for a list of the known properties.
   Setting nonstandard properties is permitted; they are treated as having
   type Text.

.. method:: Tree_node.set(identifier, value)

   Sets the value of the property whose *PropIdent* is *identifier*.

   *value* should be a native Python representation of the required property
   value (as returned by :meth:`get`).

   Raises :exc:`ValueError` if the property value isn't acceptable.

   See :ref:`sgf_property_types` below for details of how property values
   should be represented in Python.

   See :ref:`sgf_property_list` below for a list of the known properties. Any
   other property is treated as having type Text.

.. method:: Tree_node.unset(identifier)

   Removes the property whose *PropIdent* is *identifier* from the node.

   Raises :exc:`KeyError` if the property isn't currently present.

.. method:: Tree_node.has_property(identifier)

   :rtype: bool

   Checks whether the property whose *PropIdent* is *identifier* is present.

.. method:: Tree_node.properties()

   :rtype: list of strings

   Lists the properties which are present in the node.

   Returns a list of *PropIdents*, in unspecified order.

.. method:: Tree_node.find_property(identifier)

   Returns the value of the property whose *PropIdent* is *identifier*,
   looking in the node's ancestors if necessary.

   This is intended for use with properties of type *game-info*, and with
   properties which have the *inherit* attribute.

   It looks first in the node itself, then in its parent, and so on up to the
   root, returning the first value it finds. Otherwise the behaviour is the
   same as :meth:`get`.

   Raises :exc:`KeyError` if no node defining the property is found.


.. method:: Tree_node.find(identifier)

   :rtype: :class:`!Tree_node` or ``None``

   Returns the nearest node defining the property whose *PropIdent* is
   *identifier*.

   Searches in the same way as :meth:`find_property`, but returns the node
   rather than the property value. Returns ``None`` if no node defining the
   property is found.


.. rubric:: Convenience methods for properties

The following convenience methods are also provided, for more flexible access
to a few of the most important properties:

.. method:: Tree_node.get_move()

   :rtype: tuple (*colour*, *move*)

   Indicates which of the the ``B`` or ``W`` properties is present, and
   returns its value.

   Returns (``None``, ``None``) if neither property is present.

.. method:: Tree_node.set_move(colour, move)

   Sets the ``B`` or ``W`` property. If the other property is currently
   present, it is removed.

   Gomill doesn't attempt to ensure that moves are legal.

.. method:: Tree_node.get_setup_stones()

   :rtype: tuple (set of *points*, set of *points*, set of *points*)

   Returns the settings of the ``AB``, ``AW``, and ``AE`` properties.

   The tuple elements represent black, white, and empty points respectively.
   If a property is missing, the corresponding set is empty.

.. method:: Tree_node.set_setup_stones(black, white[, empty])

   Sets the ``AB``, ``AW``, and ``AE`` properties.

   Each parameter should be a sequence or set of *points*. If a parameter
   value is empty (or, in the case of *empty*, if the parameter is
   omitted) the corresponding property will be unset.

.. method:: Tree_node.has_setup_stones()

   :rtype: bool

   Returns ``True`` if the ``AB``, ``AW``, or ``AE`` property is present.

.. method:: Tree_node.add_comment_text(text)

   If the ``C`` property isn't already present, adds it with the value given
   by the string *text*.

   Otherwise, appends *text* to the existing ``C`` property value, preceded by
   two newlines.


.. rubric:: Board size and raw property encoding

Each :class:`!Tree_node` knows its game's board size, and its :ref:`raw
property encoding <raw_property_encoding>` (because these are needed to
interpret property values). They can be retrieved using the following methods:

.. method:: Tree_node.get_size()

   :rtype: int

.. method:: Tree_node.get_encoding()

   :rtype: string

   This returns the name of the raw property encoding (in a normalised form,
   which may not be the same as the string originally used to specify the
   encoding).

An attempt to change the value of the ``SZ`` property so that it doesn't match
the board size will raise :exc:`ValueError` (even if the node isn't the root).


.. rubric:: Access to raw property values

Raw property values are 8-bit strings, containing the exact bytes that go
between the ``[`` and ``]`` in the |sgf| file. They should be treated as being
encoded in the node's :ref:`raw property encoding <raw_property_encoding>`
(but there is no guarantee that they hold properly encoded data).

The following methods are provided for access to raw property values. They can
be used to access malformed values, or to avoid the standard escape processing
and whitespace conversion for Text and SimpleText values.

When setting raw property values, any string that is a well formed |sgf|
*PropValue* is accepted: that is, any string that that doesn't contain an
unescaped ``]`` or end with an unescaped ``\``. There is no check that the
string is properly encoded in the raw property encoding.

.. method:: Tree_node.get_raw_list(identifier)

   :rtype: nonempty list of 8-bit strings

   Returns the raw values of the property whose *PropIdent* is *identifier*.

   Raises :exc:`KeyError` if the property isn't currently present.

   If the property value is an empty elist, returns a list containing a single
   empty string.

.. method:: Tree_node.get_raw(identifier)

   :rtype: 8-bit string

   Returns the raw value of the property whose *PropIdent* is *identifier*.

   Raises :exc:`KeyError` if the property isn't currently present.

   If the property has multiple `PropValue`\ s, returns the first. If the
   property value is an empty elist, returns an empty string.

.. method:: Tree_node.get_raw_property_map(identifier)

   :rtype: dict: string → list of 8-bit strings

   Returns a dict mapping *PropIdents* to lists of raw values.

   Returns the same dict object each time it's called.

   Treat the returned dict object as read-only.

.. method:: Tree_node.set_raw_list(identifier, values)

   Sets the raw values of the property whose *PropIdent* is *identifier*.

   *values* must be a nonempty list of 8-bit strings. To specify an empty
   elist, pass a list containing a single empty string.

   Raises :exc:`ValueError` if the identifier isn't a well-formed *PropIdent*,
   or if any value isn't a well-formed *PropValue*.

.. method:: Tree_node.set_raw(identifier, value)

   Sets the raw value of the property whose *PropIdent* is *identifier*.

   Raises :exc:`ValueError` if the identifier isn't a well-formed *PropIdent*,
   or if the value isn't a well-formed *PropValue*.


.. rubric:: Tree manipulation

The following methods are provided for manipulating the tree:

.. method:: Tree_node.new_child([index])

   :rtype: :class:`!Tree_node`

   Creates a new :class:`!Tree_node` and adds it to the tree as this node's
   last child.

   If the optional integer *index* parameter is present, the new node is
   inserted in the list of children at the specified index instead (with the
   same behaviour as :meth:`!list.insert`).

   Returns the new node.

.. method:: Tree_node.delete()

   Removes the node from the tree (along with all its descendents).

   Raises :exc:`ValueError` if called on the root node.

   You should not continue to use a node which has been removed from its tree.

.. method:: Tree_node.reparent(new_parent[, index])

   Moves the node from one part of the tree to another (along with all its
   descendents).

   *new_parent* must be a node belonging to the same game.

   Raises :exc:`ValueError` if the operation would create a loop in the tree
   (ie, if *new_parent* is the node being moved or one of its descendents).

   If the optional integer *index* parameter is present, the new node is
   inserted in the new parent's list of children at the specified index;
   otherwise it is placed at the end.

   This method can be used to reorder variations. For example, to make a node
   the leftmost variation of its parent::

     node.reparent(node.parent, 0)


.. _sgf_property_types:

Property types
^^^^^^^^^^^^^^

The :meth:`~Tree_node.get` and :meth:`~Tree_node.set` node methods convert
between raw |sgf| property values and suitable native Python types.

The following table shows how |sgf| property types are represented as Python
values:

=========== ========================
|sgf| type   Python representation
=========== ========================
None         ``True``
Number       int
Real         float
Double       ``1`` or ``2`` (int)
Colour       *colour*
SimpleText   8-bit UTF-8 string
Text         8-bit UTF-8 string
Stone        *point*
Point        *point*
Move         *move*
=========== ========================

Gomill doesn't distinguish the Point and Stone |sgf| property types. It
rejects representations of 'pass' for the Point and Stone types, but accepts
them for Move (this is not what is described in the |sgf| specification, but
it does correspond to the properties in which 'pass' makes sense).

Values of list or elist types are represented as Python lists. An empty elist
is represented as an empty Python list (in contrast, the raw value is a list
containing a single empty string).

Values of compose types are represented as Python pairs (tuples of length
two). ``FG`` values are either a pair (int, string) or ``None``.

For Text and SimpleText values, :meth:`~Tree_node.get` and
:meth:`~Tree_node.set` take care of escaping. You can store arbitrary strings
in a Text value and retrieve them unchanged, with the following exceptions:

* all linebreaks are are normalised to ``\n``

* whitespace other than line breaks is converted to a single space

:meth:`~Tree_node.get` accepts compressed point lists, but
:meth:`~Tree_node.set` never produces them (some |sgf| viewers still don't
support them).

In some cases, :meth:`~Tree_node.get` will accept values which are not
strictly permitted in |sgf|, if there's a sensible way to interpret them. In
particular, empty lists are accepted for all list types (not only elists).

In some cases, :meth:`~Tree_node.set` will accept values which are not exactly
in the Python representation listed, if there's a natural way to convert them
to the |sgf| representation.

Both :meth:`~Tree_node.get` and :meth:`~Tree_node.set` check that Point values
are in range for the board size. Neither :meth:`~Tree_node.get` nor
:meth:`~Tree_node.set` pays attention to range restrictions for values of type
Number.

Examples::

   >>> node.set('KO', True)
   >>> node.get_raw('KO')
   ''
   >>> node.set('HA', 3)
   >>> node.set('KM', 5.5)
   >>> node.set('GB', 2)
   >>> node.set('PL', 'w')
   >>> node.set('RE', 'W+R')
   >>> node.set('GC', 'Example game\n[for documentation]')
   >>> node.get_raw('GC')
   'Example game\n[for documentation\\]'
   >>> node.set('B', (2, 3))
   >>> node.get_raw('B')
   'dg'
   >>> node.set('LB', [((6, 0), "label 1"), ((6, 1), "label 2")])
   >>> node.get_raw_list('LB')
   ['ac:label 1', 'bc:label 2']



.. _sgf_property_list:

Property list
^^^^^^^^^^^^^

Gomill knows the types of all general and Go-specific |sgf| properties defined
in FF[4]:

======  ==========================  ===================
  Id     |sgf| type                  Meaning
======  ==========================  ===================
``AB``  list of Stone               Add Black
``AE``  list of Point               Add Empty
``AN``  SimpleText                  Annotation
``AP``  SimpleText:SimpleText       Application
``AR``  list of Point:Point         Arrow
``AW``  list of Stone               Add White
``B``   Move                        Black move
``BL``  Real                        Black time left
``BM``  Double                      Bad move
``BR``  SimpleText                  Black rank
``BT``  SimpleText                  Black team
``C``   Text                        Comment
``CA``  SimpleText                  Charset
``CP``  SimpleText                  Copyright
``CR``  list of Point               Circle
``DD``  elist of Point              Dim Points
``DM``  Double                      Even position
``DO``  None                        Doubtful
``DT``  SimpleText                  Date
``EV``  SimpleText                  Event
``FF``  Number                      File format
``FG``  None | Number:SimpleText    Figure
``GB``  Double                      Good for Black
``GC``  Text                        Game comment
``GM``  Number                      Game
``GN``  SimpleText                  Game name
``GW``  Double                      Good for White
``HA``  Number                      Handicap
``HO``  Double                      Hotspot
``IT``  None                        Interesting
``KM``  Real                        Komi
``KO``  None                        Ko
``LB``  list of Point:SimpleText    Label
``LN``  list of Point:Point         Line
``MA``  list of Point               Mark
``MN``  Number                      Set move number
``N``   SimpleText                  Node name
``OB``  Number                      Overtime stones left for Black
``ON``  SimpleText                  Opening
``OT``  SimpleText                  Overtime description
``OW``  Number                      Overtime stones left for White
``PB``  SimpleText                  Black player name
``PC``  SimpleText                  Place
``PL``  Colour                      Player to play
``PM``  Number                      Print move mode
``PW``  SimpleText                  White player name
``RE``  SimpleText                  Result
``RO``  SimpleText                  Round
``RU``  SimpleText                  Rules
``SL``  list of Point               Selected
``SO``  SimpleText                  Source
``SQ``  list of Point               Square
``ST``  Number                      Style
``SZ``  Number                      Size
``TB``  elist of Point              Black territory
``TE``  Double                      Tesuji
``TM``  Real                        Time limit
``TR``  list of Point               Triangle
``TW``  elist of Point              White territory
``UC``  Double                      Unclear position
``US``  SimpleText                  User
``V``   Real                        Value
``VW``  elist of Point              View
``W``   Move                        White move
``WL``  Real                        White time left
``WR``  SimpleText                  White rank
``WT``  SimpleText                  White team
======  ==========================  ===================


.. _raw_property_encoding:

Character encoding handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The |sgf| format is defined as containing ASCII-encoded data, possibly with
non-ASCII characters in Text and SimpleText property values. The Gomill
functions for loading and serialising |sgf| data work with 8-bit Python
strings.

The encoding used for Text and SimpleText property values is given by the
``CA`` root property (if that isn't present, the encoding is ``ISO-8859-1``).

In order for an encoding to be used in Gomill, it must exist as a Python
built-in codec, and it must be compatible with ASCII (at least whitespace,
``\``, ``]``, and ``:`` must be in the usual places). Behaviour is unspecified
if a non-ASCII-compatible encoding is requested.

When encodings are passed as parameters (or returned from functions), they are
represented using the names or aliases of Python built-in codecs (eg
``"UTF-8"`` or ``"ISO-8859-1"``). See `standard encodings`__ for a list.
Values of the ``CA`` property are interpreted in the same way.

  .. __: http://docs.python.org/release/2.7/library/codecs.html#standard-encodings

Each :class:`.Sgf_game` and :class:`.Tree_node` has a fixed :dfn:`raw property
encoding`, which is the encoding used internally to store the property values.
The :meth:`Tree_node.get_raw` and :meth:`Tree_node.set_raw` methods use the
raw property encoding.

When an |sgf| game is loaded from a string, the raw property encoding is taken
from the ``CA`` root property (unless overridden). Improperly encoded property
values will not be detected until they are accessed (:meth:`~Tree_node.get`
will raise :exc:`ValueError`; use :meth:`~Tree_node.get_raw` to retrieve the
actual bytes).


.. _transcoding:

.. rubric:: Transcoding

When an |sgf| game is serialised to a string, the encoding represented by the
``CA`` root property is used. This :dfn:`target encoding` will be the same as
the raw property encoding unless ``CA`` has been changed since the
:class:`.Sgf_game` was created.

When the raw property encoding and the target encoding match, the raw property
values are included unchanged in the output (even if they are improperly
encoded.)

Otherwise, if any raw property value is improperly encoded,
:exc:`UnicodeDecodeError` is raised, and if any property value can't be
represented in the target encoding, :exc:`UnicodeEncodeError` is raised.

If the target encoding doesn't identify a Python codec, :exc:`ValueError` is
raised. The behaviour of :meth:`~Sgf_game.serialise` is unspecified if the
target encoding isn't ASCII-compatible (eg, UTF-16).


.. _parsing_details:

Parsing
^^^^^^^

The parser permits non-|sgf| content to appear before the beginning and after
the end of the game. It identifies the start of |sgf| content by looking for
``(;`` (with possible whitespace between the two characters).

The parser accepts at most 8 letters in *PropIdents* (there is no formal limit
in the specification, but no standard property has more than 2).

The parser doesn't perform any checks on property values. In particular, it
allows multiple values to be present for any property.

The parser doesn't, in general, attempt to 'fix' ill-formed |sgf| content. As
an exception, if a *PropIdent* appears more than once in a node it is
converted to a single property with multiple values.

The parser doesn't permit lower-case letters in *PropIdents* (these are
allowed in some ancient |sgf| variants).


The :mod:`!sgf_moves` module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. module:: gomill.sgf_moves
   :synopsis: Higher-level processing of moves and positions from SGF games.

The :mod:`!gomill.sgf_moves` module contains some higher-level functions for
processing moves and positions, and provides a link to the :mod:`.boards`
module.


.. function:: get_setup_and_moves(sgf_game[, board])

   :rtype: tuple (:class:`.Board`, list of tuples (*colour*, *move*))

   Returns the initial setup and the following moves from an
   :class:`.Sgf_game`.

   The board represents the position described by ``AB`` and/or ``AW``
   properties in the |sgf| game's root node. :exc:`ValueError` is raised if
   this position isn't legal.

   The moves are from the game's leftmost variation. Doesn't check that the
   moves are legal.

   Raises :exc:`ValueError` if the game has structure it doesn't support.

   Currently doesn't support ``AB``/``AW``/``AE`` properties after the root
   node.

   If the optional *board* parameter is provided, it must be an empty
   :class:`.Board` of the right size; the same object will be returned (this
   option is provided so you can use a different Board class).

   See also the :script:`show_sgf.py` example script.


.. function:: set_initial_position(sgf_game, board)

   Adds ``AB``/``AW``/``AE`` properties to an :class:`.Sgf_game`'s root node,
   to reflect the position from a :class:`.Board`.

   Replaces any existing ``AB``/``AW``/``AE`` properties in the root node.


.. function:: indicate_first_player(sgf_game)

   Adds a ``PL`` property to an :class:`.Sgf_game`'s root node if appropriate,
   to indicate which colour is first to play.

   Looks at the first child of the root to see who the first player is, and
   sets ``PL`` it isn't the expected player (Black normally, but White if
   there is a handicap), or if there are non-handicap setup stones.

