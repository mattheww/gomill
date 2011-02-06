.. index:: all-play-all

All-play-all tournaments
^^^^^^^^^^^^^^^^^^^^^^^^

:setting:`competition_type` string: ``"allplayall"``.

In an all-play-all tournament the control file lists a number of players (the
:dfn:`competitors`), and games are played between each possible pairing.

All games are played with no handicap and with the same komi. The players in
each pairing will swap colours in successive games.

For most purposes an all-play-all tournament is equivalent to a playoff
tournament with a matchup defined for each pair of competitors; the main
difference is that reports include a results summary grid.

The tournament runs until :aa-setting:`rounds` games have been played between
each pairing (indefinitely, if :aa-setting:`rounds` is unset).


.. contents:: Page contents
   :local:
   :backlinks: none


.. _sample_allplayall_control_file:

Sample control file
"""""""""""""""""""

Here is a sample control file::

  competition_type = 'allplayall'

  players = {
      'gnugo-l1' : Player("gnugo --mode=gtp --chinese-rules "
                          "--capture-all-dead --level=1"),

      'gnugo-l2' : Player("gnugo --mode=gtp --chinese-rules "
                          "--capture-all-dead --level=2"),

      'gnugo-l3' : Player("gnugo --mode=gtp --chinese-rules "
                          "--capture-all-dead --level=3"),
      }

  board_size = 9
  komi = 6

  rounds = 20
  competitors = ['gnugo-l1', 'gnugo-l2', 'gnugo-l3']


.. _allplayall_control_file_settings:

Control file settings
"""""""""""""""""""""

The following settings can be set at the top level of the control file:

All :ref:`common settings <common settings>`.

The following game settings: :setting:`board_size`, :setting:`komi`,
:setting:`move_limit`, :setting:`scorer`.

The following additional settings:

.. aa-setting:: competitors

  List of :ref:`player codes <player codes>`.

  This defines which players will take part. Reports will list the players
  in the order in which they appear here. You may not list the same player
  more than once.

.. aa-setting:: rounds

  Integer (default ``None``)

  The number of games to play for each pairing. If you leave this unset, the
  tournament will continue indefinitely.

The only required settings are :setting:`competition_type`,
:setting:`players`, :aa-setting:`competitors`, :setting:`board_size`, and
:setting:`komi`.


Reporting
"""""""""

The :ref:`live display <live_display>` and :ref:`competition report
<competition report file>` summarise the tournament results in the form of a
grid, for example::

              A   B   C
  A gnugo-l1     4-5 3-5
  B gnugo-l2 5-4     3-5
  C gnugo-l3 5-3 5-3

Each row shows the number of wins and losses for the player named on that row
against each opponent (in the example, ``gnugo-l1`` has won 4 games and lost 5
against ``gnugo-l2``).

If any games have unknown results (because they could not be scored, or
reached the :setting:`move_limit`), they will not be shown in the grid.

The competition report also shows full details of each pairing in the same
style as playoff tournaments.

For purposes of the :doc:`tournament results API <tournament_results>`, the
matchup ids are of the form ``AvB`` (using the competitor letters shown in the
results grid).


Changing the control file between runs
""""""""""""""""""""""""""""""""""""""

You can add new players to the end of the :aa-setting:`competitors` list
between runs, but you may not remove or reorder competitors.

