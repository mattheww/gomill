.. index:: playoffs

.. _playoff tournament:

Playoff tournaments
^^^^^^^^^^^^^^^^^^^

:setting:`competition_type` string: ``"playoff"``.

In a playoff tournament the control file explicitly describes one or more
pairings of players (:dfn:`matchups`).

Each matchup is treated independently: different matchups can use different
board sizes, handicap arrangements, and so on.

The tournament runs until :pl-setting:`number_of_games` have been played for
each matchup (indefinitely, if :pl-setting:`number_of_games` is unset).


.. contents:: Page contents
   :local:
   :backlinks: none


.. _sample_playoff_control_file:

Sample control file
"""""""""""""""""""

Here is a sample control file, illustrating how matchups are specified::

  competition_type = 'playoff'

  players = {
      'gnugo-l1' : Player("gnugo --mode=gtp --chinese-rules "
                          "--capture-all-dead --level=1"),

      'gnugo-l2' : Player("gnugo --mode=gtp --chinese-rules "
                          "--capture-all-dead --level=2"),
      }

  board_size = 9
  komi = 6

  matchups = [
      Matchup('gnugo-l1', 'gnugo-l2', board_size=13,
              handicap=2, handicap_style='free', komi=0,
              scorer='players', number_of_games=5),

      Matchup('gnugo-l1', 'gnugo-l2', alternating=True,
              scorer='players', move_limit=200),

      Matchup('gnugo-l1', 'gnugo-l2',
              komi=0.5,
              scorer='internal'),
      ]


.. _playoff_control_file_settings:

Control file settings
"""""""""""""""""""""

The following settings can be set at the top level of the control file:

All :ref:`common settings <common settings>`.

All :ref:`game settings <game settings>`, and the matchup settings
:pl-setting:`alternating` and :pl-setting:`number_of_games` described below;
these will be used for any matchups which don't explicitly override them.

.. pl-setting:: matchups

  List of :pl-setting-cls:`Matchup` definitions (see :ref:`matchup
  configuration`).

  This defines which players will compete against each other, and the game
  settings they will use.

The only required settings are :setting:`competition_type`,
:setting:`players`, and :pl-setting:`matchups`.



.. _matchup configuration:

Matchup configuration
"""""""""""""""""""""

.. pl-setting-cls:: Matchup

A :pl-setting-cls:`!Matchup` definition has the same syntax as a Python
function call: :samp:`Matchup({arguments})`.

The first two arguments should be the :ref:`player codes <player codes>` for
the two players involved in the matchup. The remaining arguments should be
specified in keyword form. For example::

  Matchup('gnugo-l1', 'fuego-5k', board_size=13, komi=6)

Defaults for matchup arguments (other than :pl-setting:`id` and
:pl-setting:`name`) can be specified at the top level of the control file.

The :setting:`board_size` and :setting:`komi` arguments must be given for all
matchups (either explicitly or as defaults); the rest are all optional.

.. caution:: a default :setting:`komi` or :pl-setting:`alternating` setting
   will be applied even to handicap games.


All :ref:`game settings <game settings>` can be used as matchup arguments, and
also the following:


.. _matchup id:

.. pl-setting:: id

  Identifier

  A short string (usually one to three characters) which is used to identify
  the matchup. Matchup ids appear in the :ref:`game ids <game id>` (and so in
  the |sgf| filenames), and are used in the :doc:`tournament results API
  <tournament_results>`.

  If this is left unspecified, the matchup id will be the index of the matchup
  in the :pl-setting:`matchups` list (formatted as a decimal string, starting
  from ``"0"``).


.. pl-setting:: name

  String

  A string used to describe the matchup in reports. By default, this has the
  form :samp:`{player code} vs {player code}`; you may wish to change it if you
  have more than one matchup between the same pair of players (perhaps with
  different komi or handicap).


.. pl-setting:: alternating

  Boolean (default ``False``)

  If this is ``True``, the players will swap colours in successive games.
  Otherwise, the player given as the first argument always takes Black.


.. pl-setting:: number_of_games

  Integer (default ``None``)

  The total number of games to play in the matchup. If you leave this unset,
  there will be no limit.

  Changing :pl-setting:`!number_of_games` to ``0`` provides a way to effectively
  disable a matchup in future runs, without forgetting its results.


Reporting
"""""""""

The :ref:`live display <live_display>` and :ref:`competition report
<competition report file>` show each matchup's results in the following form::

  gnugo-l1 v gnugo-l2 (5/5 games)
  board size: 9   komi: 7.5
             wins              black        white      avg cpu
  gnugo-l1      2 40.00%       1 33.33%     1 50.00%      1.23
  gnugo-l2      3 60.00%       1 50.00%     2 66.67%      1.39
                               2 40.00%     3 60.00%

or, if the players have not alternated colours::

  gnugo-l1 v gnugo-l2 (5/5 games)
  board size: 9   komi: 7.5
             wins                   avg cpu
  gnugo-l1      0   0.00%   (black)    0.49
  gnugo-l2      5 100.00%   (white)    0.48

Any :term:`jigos <jigo>` are counted as half a win for each player. If any
games have been lost by forfeit, a count will be shown for each player. If any
games have unknown results (because they could not be scored, or reached the
:setting:`move_limit`), a count will be shown for each matchup. :ref:`void
games` are not shown in these reports.

If there is more than one matchup between the same pair of players, use the
matchup :pl-setting:`name` setting to distinguish them.


Changing the control file between runs
""""""""""""""""""""""""""""""""""""""

If you change a :pl-setting-cls:`Matchup` definition, the new definition will
be used when describing the matchup in reports; there'll be no record of the
earlier definition, or which games were played under it.

If you change a :pl-setting-cls:`Matchup` definition to have different players
(ie, player codes), the ringmaster will refuse to run the competition.

If you delete a :pl-setting-cls:`Matchup` definition, results from that
matchup won't be displayed during future runs, but will be included (with some
missing information) in the :action:`report` and :action:`show` output.

If you add a :pl-setting-cls:`Matchup` definition, put it at the end of the
list (or else explicitly specify the matchup ids).

It's safe to increase or decrease a matchup's :pl-setting:`number_of_games`.
If more games have been played than the new limit, they will not be forgotten.

In practice, you shouldn't delete :pl-setting-cls:`Matchup` definitions (if
you don't want any more games to be played, set :pl-setting:`number_of_games`
to ``0``).

