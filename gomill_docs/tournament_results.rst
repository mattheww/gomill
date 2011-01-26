Tournament results API
----------------------

.. todo:: introduction

.. todo:: explain *colour* is ``'b'`` or ``'w'``.

.. class:: Tournament_results

   A Tournament_results object provides access to the results of a single
   tournament.

   The tournament results are catalogued in terms of :dfn:`matchups`, with
   each matchup corresponding to a pair of players. Each matchup has an id,
   which is a short string.

   Tournament_results objects are normally retrieved from :class:`Competition`
   or :class:`Ringmaster` objects.

   Tournament_results objects support the following methods:

   .. method:: get_matchup_ids()

      Return a list of all the tournament's matchup ids.

   .. method:: get_matchup(matchup_id)

      Return a :class:`Matchup_description` describing the matchup with the
      specified id.

   .. method:: get_matchups()

      Return a map *matchup id* → :class:`Matchup_description`, describing all
      matchups.

   .. method:: get_matchup_results(matchup_id)

      Return the individual game results for the matchup with the specified id.

      Returns a list of :class:`Game_result` objects.

      The list is in unspecified order (in particular, the colours don't
      necessarily alternate, even if :attr:`alternating` is ``True`` for the
      matchup).

      :ref:`void games` do not appear in these results.

   .. method:: get_matchup_stats(matchup_id)

      Return a :class:`Matchup_stats` object containing statistics for the
      matchup with the specified id.


.. class:: Matchup_description

   A Matchup_description describes a series of games which had the same
   players and settings.

   Matchup_descriptions are normally retrieved from
   :class:`Tournament_results` objects.

   Matchup_descriptions have the following attributes (which should be treated
   as read-only):

   .. attribute:: id

      The :ref:`matchup id <matchup id>` (a string, usually 1 to 3 characters)

   .. attribute:: p1

      The :ref:`player code <player codes>` of the first player

   .. attribute:: p2

      The :ref:`player code <player codes>` of the second player

   :attr:`!p1` and :attr:`!p2` are always different.

   .. note:: In a :ref:`playoff tournament <playoff tournament>`, it is
      possible to define a matchup in which the same player takes both
      colours. In this case, :attr:`!p2` will have the string ``'#2'``
      appended to the player code from the control file.

   .. attribute:: name

      String describing the matchup (eg ``'xxx v yyy'``)

   .. attribute:: board_size

      Integer (eg ``19``)

   .. attribute:: komi

      Float (eg ``7.0``)

   .. attribute:: alternating

      Bool. If this is ``False``, :attr:`p1` played black and :attr:`p2`
      played white; otherwise they alternated.

   .. attribute:: handicap

      Integer or ``None``

   .. attribute:: handicap_style

      String: ``'fixed'`` or ``'free'``

   .. attribute:: move_limit

      Integer or ``None``. See :ref:`playing games`.

   .. attribute:: scorer

      String: ``'internal'`` or ``'players'``. See :ref:`scoring`.

   .. attribute:: number_of_games

      Integer or ``None``. This is the number of games requested in the
      control file; it may not match the number of game results that are
      available.


   Matchup_descriptions support the following method:

   .. method:: describe_details()

      Return a text description of the matchup's game settings.

      This covers the most important game settings which can't be observed in
      the results table (board size, handicap, and komi).


.. class:: Game_result

   A Game_result contains the information recorded for an individual game.

   .. note:: If an |sgf| :ref:`game record <game records>` has been written
      for the game, you can retrieve its location in the filesystem from a
      :class:`ringmaster` object using
      :samp:`ringmaster.get_sgf_filename({game_id})`

   The :ref:`player codes <player codes>` used here are the same as the ones
   in the corresponding :class:`Matchup_description`'s :attr:`p1` and
   :attr:`p2` attributes.

   See :ref:`playing games` and :ref:`details of scoring` for an explanation
   of the possible game results. Games with unknown result can be
   distinguished as having :attr:`winning_player` ``None`` but :attr:`is_jigo`
   ``False``.

   Game_results have the following attributes (which should be treated as
   read-only):

   .. attribute:: game_id

      Short string uniquely identifying the game within the tournament. See
      :ref:`game id`.

      .. Game_results returned via Tournament_results always have game_id set,
         so documenting it that way here.

   .. attribute:: players

      Map *colour* → :ref:`player code <player codes>`

   .. attribute:: player_b

      :ref:`player code <player codes>` of the Black player

   .. attribute:: player_w

      :ref:`player code <player codes>` of the White player

   .. attribute:: winning_player

      :ref:`player code <player codes>` or ``None``

   .. attribute:: losing_player

      :ref:`player code <player codes>` or ``None``

   .. attribute:: winning_colour

      *colour* or ``None``

   .. attribute:: losing_colour

      *colour* or ``None``

   .. attribute:: is_jigo

      Bool: ``True`` if the game is a :term:`jigo`.

   .. attribute:: is_forfeit

      Bool: ``True`` if the game was forfeit; see :ref:`playing games`.

   .. attribute:: sgf_result

      String describing the game's result. This is in the format used for the
      :term:`SGF` ``RE`` property (eg ``'B+1.5'``).

   .. attribute:: detail

      Additional information about the game result (string or ``None``).

      This is present (not ``None``) for those game results which are not wins
      on points, jigos, or wins by resignation.

   .. attribute:: cpu_times

      Map :ref:`player code <player codes>` → *time*.

      The time is a float representing a number of seconds, or ``None`` if
      time is not available, or ``'?'`` if :gtp:`gomill-cpu_time` is
      implemented but returned a failure response.

      See :ref:`cpu time` for more details.


   Game_results support the following method:

   .. method:: describe()

      Return a short human-readable description of the result.

      For example, ``'xxx beat yyy (W+2.5)'``.
