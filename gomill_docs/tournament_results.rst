Tournament results API
----------------------

.. module:: gomill.tournament_results
   :synopsis: Retrieving and reporting on tournament results.

This is a Python interface for processing the game results stored in a
tournament's :ref:`state file <competition state>`. It can be used to write
custom reports, or to find games with particular results.

Note that it can be used only for :ref:`tournaments <tournaments>` (not for
:ref:`tuning events <tuners>`).

.. contents:: Page contents
   :local:
   :backlinks: none


General
^^^^^^^

In this interface, players are identified using their player codes (that is,
their keys in the control file's :setting:`players` dictionary).

.. note:: In a :doc:`playoff tournament <playoffs>`, it is possible
  to define a matchup in which the same player takes both colours. In this
  case, the player code used for the second player will be the player code
  from the control file with ``'#2'`` appended.

The classes described here are implemented in the
:mod:`!gomill.tournament_results` and :mod:`!gomill.gtp_games` modules, but
you should not normally import these directly. See
:ref:`using_the_api_in_scripts`.


Tournament_results objects
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: Tournament_results

   A Tournament_results object provides access to the game results and
   statistics for a single tournament.

   The tournament results are catalogued in terms of :dfn:`matchups`, with
   each matchup corresponding to a series of games which had the same players
   and settings. Each matchup has an id, which is a short string.

   Tournament_results objects are normally retrieved from :class:`!Competition`
   or :class:`!Ringmaster` objects; see :ref:`using_the_api_in_scripts`.

   Tournament_results objects support the following methods:

   .. method:: get_matchup_ids()

      :rtype: list of strings

      Return the tournament's matchup ids.

   .. method:: get_matchup(matchup_id)

      :rtype: :class:`Matchup_description`

      Describe the matchup with the specified id.

   .. method:: get_matchups()

      :rtype: map *matchup id* → :class:`Matchup_description`

      Describe all matchups.

   .. method:: get_matchup_stats(matchup_id)

      :rtype: :class:`Matchup_stats` object

      Return statistics for the matchup with the specified id.

   .. method:: get_matchup_results(matchup_id)

      :rtype: list of :class:`~.Game_result` objects

      Return the individual game results for the matchup with the specified id.

      The list is in unspecified order (in particular, the colours don't
      necessarily alternate, even if :attr:`~Matchup_description.alternating`
      is ``True`` for the matchup).

      :ref:`void games` do not appear in these results.


Matchup_description objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: Matchup_description

   A Matchup_description describes a series of games which had the same
   players and settings. The information comes from the current contents of
   the tournament's control file.

   Matchup_descriptions are normally retrieved from
   :class:`Tournament_results` objects.

   Matchup_descriptions have the following attributes (which should be treated
   as read-only):

   .. attribute:: id

      The :ref:`matchup id <matchup id>` (a string, usually 1 to 3 characters).

   .. attribute:: player_1
                  player_2

      The :ref:`player codes <player codes>` of the two players. These are
      never equal.

   .. attribute:: name

      String describing the matchup (eg ``'xxx v yyy'``).

   .. attribute:: board_size

      Integer (eg ``19``).

   .. attribute:: komi

      Float (eg ``7.0``).

   .. attribute:: alternating

      Bool. If this is ``False``, :attr:`player_1` played black and
      :attr:`player_2` played white; otherwise they alternated.

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

      :rtype: string

      Return a text description of the matchup's game settings.

      This covers the most important game settings which can't be observed in
      the results table (board size, handicap, and komi).


Matchup_stats objects
^^^^^^^^^^^^^^^^^^^^^

.. class:: Matchup_stats

   A Matchup_stats object provides basic summary information for a matchup.
   The information comes from the tournament's :ref:`state file <competition
   state>`.

   Matchup_stats objects are normally retrieved from
   :class:`Tournament_results` objects.

   Matchup_stats objects have the following attributes (which should be
   treated as read-only):

   .. attribute:: player_1
                  player_2

      The :ref:`player codes <player codes>` of the two players. These are
      never equal.

   .. attribute:: total

      Integer. The number of games played in the matchup.

   .. attribute:: wins_1
                  wins_2

      Integer. The number of games won by each player.

   .. attribute:: forfeits_1
                  forfeits_2

      Integer. The number of games in which each player lost by forfeit.

   .. attribute:: unknown

      Integer. The number of games whose result is unknown.

   .. attribute:: average_time_1
                  average_time_2

      float or ``None``. The average CPU time taken by each player.

      If CPU times are available for only some games, the average is taken
      over the games for which they are available. If they aren't available
      for any games, the average is given as ``None``. See :ref:`cpu time`
      for notes on how CPU times are obtained.

   .. attribute:: played_1b
                  played_2b

      Integer. The number of games in which each player took Black.

   .. attribute:: played_1w
                  played_2w

      Integer. The number of games in which each player took White.

   .. attribute:: alternating

      Bool. This is true if each player played at least one game as Black and
      at least one game as White.

      This doesn't always equal the :attr:`~Matchup_description.alternating`
      attribute from the corresponding :class:`Matchup_description` object (in
      particular, if only one game was played in the matchup, it will always
      be ``False``).

   If :attr:`alternating` is ``True``, the following attributes are also
   available:

   .. attribute:: wins_b

      Integer. The number of games in which Black won.

   .. attribute:: wins_w

      Integer. The number of games in which White won.

   .. attribute:: wins_1b
                  wins_2b

      Integer. The number of games in which each player won with Black.

   .. attribute:: wins_1w
                  wins_2w

      Integer. The number of games in which each player won with White.


   If :attr:`alternating` is ``False``, the following attributes are also
   available:

   .. attribute:: colour_1
                  colour_2

      The *colour* taken by each player.


.. currentmodule:: gomill.gtp_games

Game_result objects
^^^^^^^^^^^^^^^^^^^

.. class:: Game_result

   A Game_result contains the information recorded for an individual game. The
   information comes from the tournament's :ref:`state file <competition
   state>`.

   .. note::

      If an |sgf| :ref:`game record <game records>` has been written for the
      game, you can retrieve its location in the filesystem from a
      :class:`!Ringmaster` object using
      :samp:`ringmaster.get_sgf_pathname({game_id})`.

   The :ref:`player codes <player codes>` used here are the same as the ones
   in the corresponding :class:`.Matchup_description`'s
   :attr:`~.Matchup_description.player_1` and
   :attr:`~.Matchup_description.player_2` attributes.

   See :ref:`playing games` and :ref:`details of scoring` for an explanation
   of the possible game results. Games with unknown result can be
   distinguished as having :attr:`winning_player` ``None`` but :attr:`is_jigo`
   ``False``.

   Game_results can be retrieved from
   :class:`.Tournament_results` objects.

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

      :rtype: string

      Return a short human-readable description of the result.

      For example, ``'xxx beat yyy (W+2.5)'``.


.. currentmodule:: tournament_results

.. _using_the_api_in_scripts:

Using the API in scripts
^^^^^^^^^^^^^^^^^^^^^^^^

To write a standalone script using the tournaments results API, obtain a
:class:`.Tournament_results` object from a :class:`!Ringmaster` object as
follows::

  from gomill import ringmasters
  ringmaster = ringmasters.Ringmaster(control_file_pathname)
  ringmaster.load_status()
  tournament_results = ringmaster.get_tournament_results()

All of these calls report problems by raising the :exc:`!RingmasterError`
exception defined in the :mod:`!ringmasters` module.

See the :script:`find_forfeits.py` example script for a more fleshed-out
example.

