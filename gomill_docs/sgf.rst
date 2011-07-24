SGF support
-----------

.. module:: gomill.sgf

.. versionadded:: 0.7

The :mod:`gomill.sgf` module is the main interface to gomill's |sgf| support.

It is intended for use with |sgf| version FF[4], which is specified at
http://www.red-bean.com/sgf/index.html.

.. contents:: Page contents
   :local:
   :backlinks: none

Example
^^^^^^^

FIXME::

  from gomill import sgf
  g = sgf.sgf_game_from_string("(;FF[4]GM[1]SZ[9];B[ee];W[ge])")
  assert g.get_size() == 9
  root = g.get_root()
  assert root.get("SZ") == 9
  root.set("RE","B+R")
  print sgf.serialise_sgf_game(g)



Loading |sgf| data
^^^^^^^^^^^^^^^^^^

|sgf| data is represented using :class:`Sgf_game` objects. A game can either
be created from scratch or loaded from a string.

To create a game from scratch, instantiate an :class:`Sgf_game` object
directly:

.. class:: Sgf_game(size, encoding="UTF-8"])

   The *size* parameter is an integer from 1 to 26, indicating the board size.

   The optional *encoding* parameter FIXME ((( say it's a string, valid Python
   codec name, link to encoding stuff ))).

When a game is created this way, the following root node properties are
initially set: :samp:`FF[4]`, :samp:`GM[1]`, :samp:`SZ[{size}]`, and
:samp:`CA[{encoding}]`.


To create a game from existing |sgf| data, use the
:func:`!sgf_game_from_string` function:

.. function:: sgf_game_from_string(s[, override_encoding=None])

   :rtype: :class:`Sgf_game`

   Creates an :class:`Sgf_game` from the |sgf| data in *s*, which must be an
   8-bit string.

   The board size and raw property encoding are taken from the ``SZ`` and
   ``CA`` properties in the root node (defaulting to ``19`` and
   ``"ISO-8859-1"``, respectively).

   If *override_encoding* is present, the source data is assumed to be in the
   encoding it specifies (no matter what the ``CA`` property says), and the
   ``CA`` property is changed to match.

   Raises :exc:`ValueError` if it can't parse the string, or if the ``SZ`` or
   ``CA`` properties are unacceptable.

   .. todo:: Document details of parsing (elsewhere); see parse_sgf_game()

   Example::

     g = sgf.sgf_game_from_string(
         "(;FF[4]GM[1]SZ[9]CA[UTF-8];B[ee];W[ge])",
         override_encoding="iso8859-1")


|sgf| output
^^^^^^^^^^^^

To output data in |sgf| format, use the :func:`!serialise_sgf_game` function:

.. function:: serialise_sgf_game(sgf_game)

   :rtype: string

   Produces the |sgf| representation of the data in the :class:`Sgf_game`
   *sgf_game*.

   Returns an 8-bit string, in the encoding specified by the ``CA`` root node
   property (defaulting to ``"ISO-8859-1"``).



Sgf_game objects
^^^^^^^^^^^^^^^^

.. class:: Sgf_game

   An :class:`!Sgf_game` object represents the data for a single |sgf| file
   (corresponding to a ``GameTree`` in the |sgf| spec).

   This is typically used to represent a single game, possibly with
   variations.

The complete game tree is represented using :class:`Tree_node` objects, which
are used to access the |sgf| properties. An :class:`!Sgf_game` always has at
least one node, the :dfn:`root node`.

.. method:: Sgf_game.get_root()

   :rtype: :class:`Tree_node`

   Returns the root node of the game tree.

   The root node contains global properties for the game tree, and typically
   also contains 'game-info' properties. It sometimes also contains 'setup'
   properties (for example, if the game does not begin with an empty board).


The complete game tree can be accessed from the root node, but the following
convenience methods are also provided. They return the same :class:`Tree_node`
objects that would be reached via the root node.

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
   :meth:`~Sgf_game.get_last_node`\ .\ :meth:`~Tree_node.new_child`


The following methods provide convenient access to some of the root node's
|sgf| properties. The main difference between using these methods and using
:meth:`~Tree_node.get` on the root node is that these methods return the
appropriate default value if the property is not present.

.. method:: Sgf_game.get_size()

   :rtype: integer

   Returns the board size (``19`` if the ``SZ`` root node property isn't
   present).

.. method:: Sgf_game.get_komi()

   :rtype: float

   Returns the :term:`komi` (``0.0`` if the ``KM`` root node property isn't
   present).

   Raises :exc:`ValueError` if the ``KM`` root node property is present but
   malformed.

.. method:: Sgf_game.get_handicap()

   :rtype: integer or ``None``

   Returns the number of handicap stones.

   Returns ``None`` if the ``HA`` root node property isn't present, or if it
   has (illegal) value zero.

   Raises :exc:`ValueError` if the ``HA`` property is otherwise malformed.

.. method:: Sgf_game.get_player_name(colour)

   :rtype: string or ``None``

   Returns the name of the specified player, or ``None`` if the required
   ``PB`` or ``PW`` root node property isn't present.

.. method:: Sgf_game.get_winner()

   :rtype: *colour*

   Returns the *colour* of the winning player.

   Returns ``None`` if the ``RE`` root node property isn't present, or if
   neither player won.

.. method:: Sgf_game.set_date([date])

   Sets the ``DT`` root node property, to a single date.

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


A node holds a number of :dfn:`properties`. Each property is identified by a
short string called the :dfn:`PropIdent`, eg ``"SZ"`` or ``"B"``. See
(((FIXME))) for a list of the standard properties. See the :term:`SGF`
specification for full details.

The principal methods for accessing the node's properties are:

.. method:: Tree_node.get(identifier)

   Returns a native Python representation of the value of the property whose
   *PropIdent* is *identifier*.

   Raises :exc:`KeyError` if the property isn't present.

   Raises :exc:`ValueError` if the property value is malformed.

   See (((FIXME))) for details of how property values are represented in
   Python. (((FIXME: also for details of list handling, range handling, ...)))

.. method:: Tree_node.set(identifier, value)

   Sets the value of the property whose *PropIdent* is *identifier*.

   *value* should be a native Python representation of the required property
   value (as returned by :func:`~get`).

   Raises :exc:`ValueError` if it the property value isn't acceptable.

   See (((FIXME))) for details.

.. method:: Tree_node.unset(identifier)

   Removes the property whose *PropIdent* is *indentifier* from the node.

   Raises :exc:`KeyError` if the property isn't currently present.

.. method:: Tree_node.has_property(identifier)

   :rtype: bool

   Checks whether the property whose *PropIdent* is *identifier* is present.

.. method:: Tree_node.properties()

   :rtype: list of strings

   Lists the properties which are present in the node.

   Returns a list of *PropIdents*, in unspecified order.




Character encoding handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo:: Character encoding support; define 'raw property encoding'

