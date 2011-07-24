SGF support
-----------

.. module:: gomill.sgf

.. versionadded:: 0.7

The :mod:`gomill.sgf` module is the main interface to gomill's |SGF| support.

It is intended for use with |SGF| version FF[4], which is specified at
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



Sgf_games
^^^^^^^^^

.. class:: Sgf_game

   An Sgf_game object represents the information for a single |SGF| file (a
   GameTree in the |SGF| spec).

   This is typically used to represent a single game, possibly with
   variations.

An Sgf_game can either be created from scratch or loaded from a string.

To create a game from scratch, instantiate an :class:`Sgf_game` object
directly:

.. class:: Sgf_game(size, encoding="UTF-8"])

   The *size* parameter is an integer from 1 to 26, indicating the board size.
   The optional *encoding* parameter FIXME ((( say it's a string, link to
   encoding stuff ))).


To create a game from |SGF| data, use :func:`sgf_game_from_string`:

.. function:: sgf_game_from_string(s[, override_encoding=None])

   :rtype: :class:`Sgf_game`

   Creates an Sgf_game from the |SGF| data in *s*, which must be an 8-bit
   string.

   The board size and raw property encoding are taken from the ``SZ`` and
   ``CA`` properties in the root node (defaulting to ``19`` and
   ``"ISO-8859-1"``, respectively).

   If *override_encoding* is specified, the source data is assumed to be in
   the specified encoding (no matter what the ``CA`` property says), and the
   ``CA`` property is set to match.

   Example::

     g = sgf.sgf_game_from_string(
         "(;FF[4]GM[1]SZ[9]CA[UTF-8];B[ee];W[ge])",
         override_encoding="iso8859-1")


Character encoding support
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo:: Character encoding support; define 'raw property encoding'

