The :mod:`~gomill.handicap_layout` module
-----------------------------------------

.. module:: gomill.handicap_layout
   :synopsis: Standard layout of fixed handicap stones.

The :mod:`!gomill.handicap_layout` module describes the standard layout used
for fixed handicap stones. It follows the rules from the :term:`GTP`
specification.


.. function:: handicap_points(number_of_stones, board_size)

   :rtype: list of *points*

   Returns the handicap points for a given number of stones and board size.

   Raises :exc:`ValueError` if there isn't a standard placement pattern for
   the specified number of handicap stones and board size.

   The result's length is always exactly *number_of_stones*.

.. function:: max_fixed_handicap_for_board_size(board_size)

   :rtype: int

   Returns the maximum number of stones permitted for the |gtp|
   :gtp:`!fixed_handicap` command, given the specified board size.

.. function:: max_free_handicap_for_board_size(board_size)

   :rtype: int

   Returns the maximum number of stones permitted for the |gtp|
   :gtp:`!place_free_handicap` command, given the specified board size.

