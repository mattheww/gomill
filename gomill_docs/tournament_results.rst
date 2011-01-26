Tournament results API
----------------------

.. class:: Matchup_description

   A Matchup_description describes a series of games which had the same
   players and settings.

   Matchup_descriptions are normally retrieved from
   :class:`Tournament_results` objects, not created directly.

   Matchup_descriptions have the following attributes (which should be treated
   as read-only):

   .. attribute:: id

      The :ref:`matchup id <matchup id>` (a string, usually 1 to 3 characters)

   .. attribute:: p1

      The :ref:`player code <player codes>` of the first player

   .. attribute:: p2

      The :ref:`player code <player codes>` of the second player

   :attr:`!p1` and :attr:`!p2` are always different.

   .. todo:: Explain that they match the Game_results. Explain about #2 stuff.


   .. attribute:: name

      String describing the matchup (eg ``xxx v yyy``)

   .. attribute:: board_size

      Integer (eg ``19``)

   .. attribute:: komi

      Float (eg ``7.0``)

   .. attribute:: alternating

      Bool. If this is False, :attr:`p1` played black and :attr:`p2` played
      white; otherwise they alternated.

   .. attribute:: handicap

      Integer or ``None``

   .. attribute:: handicap_style

      String: ``fixed`` or ``free``

   .. attribute:: move_limit

      Integer or ``None``. See :ref:`playing games`.

   .. attribute:: scorer

      String: ``internal`` or ``players``. See :ref:`scoring`.

   .. attribute:: number_of_games

      Integer or ``None``. This is the number of games requested in the
      control file; it may not match the number of game results that are
      available.


   Matchup_descriptions have the following method:

   .. method:: describe_details()

      Return a text description of the matchup's game settings.

      This covers the most important game settings which can't be observed in
      the results table (board size, handicap, and komi).

