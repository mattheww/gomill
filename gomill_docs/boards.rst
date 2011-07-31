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

   This method doesn't enforce any :term:`ko <simple ko>` rule.

   The return value indicates whether, immediately following this move, any
   point would be forbidden by the :term:`simple ko` rule. If so, that point
   is returned; otherwise the return value is ``None``.



.. method:: Board.is_empty()

   :rtype: bool

   Returns ``True`` if all points on the board are empty.


