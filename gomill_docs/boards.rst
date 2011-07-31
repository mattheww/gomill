The :mod:`~gomill.boards` module
--------------------------------

.. module:: gomill.boards
   :synopsis: Go board representation

The :mod:`!gomill.boards` module contains Gomill's Go board representation.

.. todo:: explain it's not at all designed for performance, even as Python
   code goes, and certainly not for implementing a playing engine.

The behaviour of functions in this module is unspecified if they are passed
out-of-range coordinates.


.. class:: Board(side)

   A :class:`!Board` object represents a position on a Go board.

   Instantiate with the board size, as an int >= 1. Only square boards are
   supported.

   Board objects do not maintain any history information.

   Board objects have the following attributes (which should be treated as
   read-only):

   .. attribute:: side

      The board size.

   .. attribute:: board_coords

      A list of *points*, giving all points on the board.


The principal :class:`!Board` methods are :meth:`~!Board.get` and
:meth:`~!Board.play`. Their *row* and *col* parameters should be ints giving
coordinates in the same coordinate system used for a *point*.

.. method:: Board.get(row, col)

   :rtype: *colour* or ``None``

   Returns the contents of the specified point.

.. method:: Board.play(row, col, colour)

   :rtype: *move*

   Places a stone of the specified *colour* on the specified point.

   Raises :exc:`ValueError` if the point isn't empty.

   Carries out any captures which follow from the placement, including
   self-captures.

   This method doesn't enforce any ko rule.

   The return value indicates whether, immediately following this move, any
   point would be forbidden by the :term:`simple ko` rule. If so, that point
   is returned; otherwise the return value is ``None``.


The other :class:`!Board` methods are:

.. method:: Board.is_empty()

   :rtype: bool

   Returns ``True`` if all points on the board are empty.


.. method:: Board.area_score()

   :rtype: int

   Calculates the area score of a position, assuming that all stones are
   alive. The result is the number of points controlled (occupied or
   surrounded) by Black minus the number of points controlled by White.

   Doesn't take any :term:`komi` into account.


.. method:: Board.list_occupied_points()

   :rtype: list of pairs (*colour*, *point*)

   Returns a list of all nonempty points, in unspecified order.


.. method:: Board.copy()

   :rtype: :class:`!Board`

   Returns an independent copy of this Board.

.. method:: Board.apply_setup(black_points, white_points, empty_points)

   :rtype: bool

   Adds and/or removes stones on arbitrary points. This is intended to support
   behaviour like |SGF| ``AB``/``AW``/``AE`` properties.

   Each parameter is an iterable of *points*.

   This method applies all the specified additions and removals, then removes
   any groups with no liberties (so the resulting position is always legal).

   If the same point is specified in more than one list, the order in which
   the instructions are applied is undefined.

   Returns ``True`` if the position was legal as specified.
