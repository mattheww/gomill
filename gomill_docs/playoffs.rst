.. index:: playoffs

Playoff tournaments
-------------------

In a playoff tournament, the control file explicitly describes one or more
pairings of players (:dfn:`matchups`). Each matchup is treated independently.

.. todo:: rough mention of what can be configured in a matchup? Expand on 'is
   treated independently'?


.. _sample_playoff_control_file:

Sample control file
^^^^^^^^^^^^^^^^^^^

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


Playoff settings
^^^^^^^^^^^^^^^^

The following settings can be set at the top level of the control file, for
competitions of type ``playoff``:

All :ref:`common settings <common settings>`.

.. setting:: matchups

  List of :setting-cls:`Matchup` definitions (see :ref:`matchup
  configuration`).

  This defines which engines will play against each other, and the game
  settings they will use.

All :ref:`game settings <game settings>`, :setting:`alternating`, and
:setting:`number_of_games`; these will be used for any matchups which don't
explicitly override them.

The only required settings are :setting:`competition_type`,
:setting:`players`, and :setting:`matchups`.



.. _matchup configuration:

Matchup configuration
^^^^^^^^^^^^^^^^^^^^^

.. setting-cls:: Matchup

A :setting-cls:`!Matchup` definition has the same syntax as a Python function
call: :samp:`Matchup({arguments})`.

The first two arguments should be the :ref:`player codes <player codes>` for
the two players involved in the matchup. The remaining arguments should be
specified in keyword form. For example::

  Matchup('gnugo-l1', 'fuego-5k', board_size=13, komi=6)

Defaults for matchup settings (other than :setting:`id` and :setting:`name`)
can be specified at the top level of the control file.

The :setting:`board_size` and :setting:`komi` arguments must be given for all
matchups (either explicitly or as defaults); the rest are all optional.

.. caution:: a default :setting:`komi` or :setting:`alternating` setting will
   be applied even to handicap games.


The arguments are:


.. setting:: id

  Identifier

  A short string (usually one to three characters) which is used to identify
  the matchup. Matchup ids appear in the :ref:`game ids <game id>` (and so in
  the |sgf| filenames), and are used in the :ref:`result-retrieval API
  <querying the results>`.

  If this is left unspecified, the matchup id will be the index of the matchup
  in the :setting:`matchups` list (formatted as a decimal string, starting
  from ``"0"``).


.. setting:: name

  String

  A string used to describe the matchup in reports. By default, this has the
  form :samp:`{player code} vs {player code}`; you may wish to change it if you
  have more than one matchup between the same pair of players (perhaps with
  different komi or handicap).


.. setting:: alternating

  Boolean (default ``False``)

  If this is ``True``, the players will swap colours in successive games.
  Otherwise, the first-named player always takes Black.


.. setting:: number_of_games

  Integer (default ``None``)

  The total number of games to play in the matchup. If you leave this unset,
  there will be no limit; see :ref:`stopping competitions`.

  Changing :setting:`!number_of_games` to ``0`` provides a way to effectively
  disable a matchup in future runs, without forgetting its results.


All :ref:`game settings <game settings>` can also be used as Matchup
arguments.


