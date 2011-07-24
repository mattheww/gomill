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


To create a game from existing |sgf| data, use :func:`sgf_game_from_string`:

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

   Raises :exc:`ValueError` if it can't parse the string.

   .. todo:: Document details of parsing (elsewhere); see parse_sgf_game()

   Example::

     g = sgf.sgf_game_from_string(
         "(;FF[4]GM[1]SZ[9]CA[UTF-8];B[ee];W[ge])",
         override_encoding="iso8859-1")


Sgf_games
^^^^^^^^^

.. class:: Sgf_game

   An Sgf_game object represents the information for a single |sgf| file (a
   ``GameTree`` in the |sgf| spec).

   This is typically used to represent a single game, possibly with
   variations.

   The complete game tree is represented using :class:`Tree_node` objects,
   which are used to access the |sgf| properties.


The following methods provide access to the |sgf| nodes. They will always
return the same :class:`Tree_node` object for the same node.

.. method:: get_root()

   :rtype: :class:`Tree_node`

   Return the root node of the game tree.

   The root node contains global properties for the game tree, and typically
   also contains 'game-info' properties. It sometimes also contains 'setup'
   properties (for example, if the game does not begin with an empty board).


The following methods provide convenient access to some of the root node's
|sgf| properties. The main difference between using these methods and using
:meth:`~Tree_node.get` on the root node is that these methods return the
appropriate default value if the property is not present.

.. method:: get_size()

   :rtype: integer

   Returns the board size (``19`` if the ``SZ`` root node property isn't
   present).

.. method:: get_komi()

   :rtype: float

   Returns the :term:`komi` (``0.0`` if the ``KM`` root node property isn't
   present).

   Raises :exc:`ValueError` if the ``KM`` root node property is present but
   malformed.

.. method:: get_handicap()

   :rtype: integer or ``None``

   Returns the number of handicap stones.

   Returns ``None`` if the ``HA`` root node property isn't present, or if it
   has (illegal) value zero.

   Raises :exc:`ValueError` if the ``HA`` property is otherwise malformed.

.. method:: get_player_name(colour)

   :rtype: string or ``None``

   Returns the name of the specified player, or ``None`` if the required
   ``PB`` or ``PW`` root node property isn't present.

.. method:: get_winner()

   :rtype: colour

   Returns the colour of the winning player.

   Returns ``None`` if the ``RE`` root node property isn't present, or if
   neither player won.

.. method:: set_date([date])

   Sets the ``DT`` root node property, to a single date.

   If *date* is specified, it should be a :class:`datetime.date`. Otherwise
   the current date is used.

   (|sgf| allows ``DT`` to be rather more complicated than a single date, so
   there's no corresponding get_date() method.)



Character encoding handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo:: Character encoding support; define 'raw property encoding'

