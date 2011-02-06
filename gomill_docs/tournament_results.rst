Tournament results API
----------------------

This is a Python library interface for processing the competition results
stored in a tournament's :ref:`state file <competition state>`.

Note that it can be used only for :ref:`tournaments <tournaments>` (not for
:ref:`tuning events <tuners>`).

In the descriptions below, *colour* represents a single-character string,
either ``'b'`` or ``'w'``.

.. contents:: Page contents
   :local:
   :backlinks: none



Tournament_results objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: Tournament_results

   A Tournament_results object provides access to the game results and
   statistics for a single tournament.

   The tournament results are catalogued in terms of :dfn:`matchups`, with
   each matchup corresponding to a series of games which had the same players
   and settings. Each matchup has an id, which is a short string.

   Tournament_results objects are normally retrieved from :class:`Competition`
   or :class:`Ringmaster` objects; see :ref:`using_the_api_in_scripts`.

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

      This returns a list of :class:`Game_result` objects.

      The list is in unspecified order (in particular, the colours don't
      necessarily alternate, even if :attr:`alternating` is ``True`` for the
      matchup).

      :ref:`void games` do not appear in these results.

   .. method:: get_matchup_stats(matchup_id)

      Return a :class:`Matchup_stats` object containing statistics for the
      matchup with the specified id.


Matchup_description objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: Matchup_description

   A Matchup_description describes a series of games which had the same
   players and settings.

   Matchup_descriptions are normally retrieved from
   :class:`Tournament_results` objects.

   Matchup_descriptions have the following attributes (which should be treated
   as read-only):

   .. attribute:: id

      The :ref:`matchup id <matchup id>` (a string, usually 1 to 3 characters).

   .. attribute:: p1

      The :ref:`player code <player codes>` of the first player.

   .. attribute:: p2

      The :ref:`player code <player codes>` of the second player.

   :attr:`!p1` and :attr:`!p2` are always different.

   .. note:: In a :ref:`playoff tournament <playoff tournament>`, it is
      possible to define a matchup in which the same player takes both
      colours. In this case, :attr:`!p2` will have the string ``'#2'``
      appended to the player code from the control file.

   .. attribute:: name

      String describing the matchup (eg ``'xxx v yyy'``).

   .. attribute:: board_size

      Integer (eg ``19``).

   .. attribute:: komi

      Float (eg ``7.0``).

   .. attribute:: alternating

      Bool. If this is ``False``, :attr:`p1` played black and :attr:`p2`
      played white; otherwise they alternated.

   .. attribute:: handicap

      Integer or ``None``.

   .. attribute:: handicap_style

      String: ``'fixed'`` or ``'free'``.

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


Game_result objects
^^^^^^^^^^^^^^^^^^^

.. class:: Game_result

   A Game_result contains the information recorded for an individual game.

   .. note:: If an |sgf| :ref:`game record <game records>` has been written
      for the game, you can retrieve its location in the filesystem from a
      :class:`ringmaster` object using
      :samp:`ringmaster.get_sgf_filename({game_id})`

   The :ref:`player codes <player codes>` used here are the same as the ones
   in the corresponding :class:`Matchup_description`'s
   :attr:`~Matchup_description.p1` and :attr:`~Matchup_description.p2`
   attributes.

   See :ref:`playing games` and :ref:`details of scoring` for an explanation
   of the possible game results. Games with unknown result can be
   distinguished as having :attr:`winning_player` ``None`` but :attr:`is_jigo`
   ``False``.

   Game_results can be retrieved from :class:`Tournament_results` objects.

   Game_results have the following attributes (which should be treated as
   read-only):

   .. attribute:: game_id

      Short string uniquely identifying the game within the tournament. See
      :ref:`game id`.

      .. Game_results returned via Tournament_results always have game_id set,
         so documenting it that way here.

   .. attribute:: players

      Map *colour* → :ref:`player code <player codes>`.

   .. attribute:: player_b

      :ref:`player code <player codes>` of the Black player.

   .. attribute:: player_w

      :ref:`player code <player codes>` of the White player.

   .. attribute:: winning_player

      :ref:`player code <player codes>` or ``None``.

   .. attribute:: losing_player

      :ref:`player code <player codes>` or ``None``.

   .. attribute:: winning_colour

      *colour* or ``None``.

   .. attribute:: losing_colour

      *colour* or ``None``.

   .. attribute:: is_jigo

      Bool: ``True`` if the game was a :term:`jigo`.

   .. attribute:: is_forfeit

      Bool: ``True`` if one of the players lost the game by forfeit; see
      :ref:`playing games`.

   .. attribute:: sgf_result

      String describing the game's result. This is in the format used for the
      :term:`SGF` ``RE`` property (eg ``'B+1.5'``).

   .. attribute:: detail

      Additional information about the game result (string or ``None``).

      This is present (not ``None``) for those game results which are not wins
      on points, jigos, or wins by resignation.

   .. (leaving cpu_times undocumented, as I don't want to say it's stable)

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


Matchup_stats objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: Matchup_stats

   A Matchup_stats object provides basic summary information for a matchup.

   Matchup_stats objects are normally retrieved from
   :class:`Tournament_results` objects.

   Matchup_stats objects have the following attributes (which should be
   treated as read-only):

   .. attribute:: player_x

      :ref:`player code <player codes>` of the first player.

   .. attribute:: player_y

      :ref:`player code <player codes>` of the second player.

   .. attribute:: total

      Integer. The number of games played in the matchup.

   .. attribute:: x_wins

      Integer. The number of games won by the first player.

   .. attribute:: y_wins

      Integer. The number of games won by the second player.

   .. attribute:: x_forfeits

      Integer. The number of games in which the first player lost by forfeit.

   .. attribute:: y_forfeits

      Integer. The number of games in which the second player lost by forfeit.

   .. attribute:: unknown

      Integer. The number of games whose result is unknown.

   .. attribute:: x_average_time

      float or ``None``. The average CPU time taken by the first player.

   .. attribute:: y_average_time

      float or ``None``. The average CPU time taken by the second player.

   If CPU times are available for only some games, the average is taken over
   the games for which they are available. If they aren't available for any
   games, the average is given as ``None``. See :ref:`cpu time` for notes on
   how CPU times are obtained.


   .. attribute:: xb_played

      Integer. The number of games in which the first player took Black.

   .. attribute:: xw_played

      Integer. The number of games in which the first player took White.

   .. attribute:: yb_played

      Integer. The number of games in which the second player took Black.

   .. attribute:: yw_played

      Integer. The number of games in which the second player took White.

   .. attribute:: alternating

      Bool. This is true if each player played at least one game as Black and
      at least one game as White.

      This doesn't always equal the :attr:`~Matchup_description.alternating`
      attribute from the corresponding :class:`Matchup_description` object (in
      particular, if only one game was played in the matchup, it will always
      be ``False``).

   If :attr:`alternating` is ``True``, the following attributes are also
   available:

   .. attribute:: b_wins

      Integer. The number of games in which Black won.

   .. attribute:: w_wins

      Integer. The number of games in which White won.

   .. attribute:: xb_wins

      Integer. The number of games in which the first player won with Black.

   .. attribute:: xw_wins

      Integer. The number of games in which the first player won with White.

   .. attribute:: yb_wins

      Integer. The number of games in which the second player won with Black.

   .. attribute:: yw_wins

      Integer. The number of games in which the second player won with White.


   If :attr:`alternating` is ``False``, the following attributes are also
   available:

   .. attribute:: x_colour

      The *colour* taken by the first player.

   .. attribute:: y_colour

      The *colour* taken by the second player.


.. _using_the_api_in_scripts:

Using the API in scripts
^^^^^^^^^^^^^^^^^^^^^^^^

To write a stand-alone script using the tournaments results API, use a
:class:`Ringmaster` object as follows::

  from gomill import ringmasters
  ringmaster = ringmasters.Ringmaster(control_file_pathname)
  ringmaster.load_status()
  tournament_results = ringmaster.tournament_results()

All of these calls report problems by raising the :exc:`RingmasterError`
exception defined in the :mod:`ringmasters` module.

See the :script:`find_forfeits.py` example script for a more fleshed-out
example.

