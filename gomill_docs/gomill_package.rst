The :mod:`gomill` package
-------------------------

All Gomill code is contained in modules under the :mod:`!gomill` package.

The package includes both the 'toolkit' (Go board, |sgf|, and |gtp|) code, and
the code implementing the ringmaster.

.. contents:: Page contents
   :local:
   :backlinks: none


Package module contents
^^^^^^^^^^^^^^^^^^^^^^^

The package module itself defines only a single constant:

.. module:: gomill
   :synopsis: Tools for testing and tuning Go-playing programs.

.. data:: __version__

   The library version, as a string (like ``"0.7"``).

   .. versionadded:: 0.7


Generic data representation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Unless otherwise stated, string values are 8-bit UTF-8 strings.


.. _go_related_data_representation:

Go-related data representation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Gomill represents Go colours and moves internally as follows:

======== ===========================================
 Name     Possible values
======== ===========================================
*colour* single-character string: ``'b'`` or ``'w'``
*point*  pair (*int*, *int*) of coordinates
*move*   *point* or ``None`` (for a pass)
======== ===========================================

The terms *colour*, *point*, and *move* are used as above throughout this
library documentation (in particular, when describing parameters and return
types).

*colour* values are used to represent players, as well as stones on the board.
(When a way to represent an empty point is needed, ``None`` is used.)

*point* values are treated as (row, column). The bottom left is ``(0, 0)``
(the same orientation as |gtp|, but not |sgf|). So the coordinates for a 9x9
board are as follows::

  9 (8,0)  .  .  .  .  .  (8,8)
  8  .  .  .  .  .  .  .  .  .
  7  .  .  .  .  .  .  .  .  .
  6  .  .  .  .  .  .  .  .  .
  5  .  .  .  .  .  .  .  .  .
  4  .  .  .  .  .  .  .  .  .
  3  .  .  .  .  .  .  .  .  .
  2  .  .  .  .  .  .  .  .  .
  1 (0,0)  .  .  .  .  .  (0,8)
     A  B  C  D  E  F  G  H  J

There are functions in the :mod:`~gomill.common` module to convert between
these coordinates and the conventional (``T19``\ -style) notation.

Gomill is designed to work with square boards, up to 25x25 (which is the upper
limit of the conventional notation, and the upper limit for |gtp|). Some parts
of the library can work with larger board sizes; these cases are documented
explicitly.

