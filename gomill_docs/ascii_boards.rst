The :mod:`~gomill.ascii_boards` module
--------------------------------------

.. module:: gomill.ascii_boards
   :synopsis: ASCII Go board diagrams.

The :mod:`!gomill.ascii_boards` module contains functions for producing and
interpreting ASCII diagrams of Go board positions.


.. function:: render_board(board)

   :rtype: string

   Returns an ASCII diagram of the position on the :class:`.Board` *board*.

   The returned string does not end with a newline.

   ::

      >>> b = boards.Board(9)
      >>> b.play(2, 5, 'b')
      >>> b.play(3, 6, 'w')
      >>> print ascii_boards.render_board(b)
      9  .  .  .  .  .  .  .  .  .
      8  .  .  .  .  .  .  .  .  .
      7  .  .  .  .  .  .  .  .  .
      6  .  .  .  .  .  .  .  .  .
      5  .  .  .  .  .  .  .  .  .
      4  .  .  .  .  .  .  o  .  .
      3  .  .  .  .  .  #  .  .  .
      2  .  .  .  .  .  .  .  .  .
      1  .  .  .  .  .  .  .  .  .
         A  B  C  D  E  F  G  H  J

   See also the :script:`show_sgf.py` example script.


.. function:: interpret_diagram(diagram, size[, board])

   :rtype: :class:`.Board`

   Returns the position given in an ASCII diagram.

   *diagram* must be a string in the format returned by :func:`render_board`,
   representing a position with the specified size.

   Raises :exc:`ValueError` if it can't interpret the diagram.

   If the optional *board* parameter is provided, it must be an empty
   :class:`.Board` of the right size; the same object will be returned (this
   option is provided so you can use a different Board class).
