.. index:: playoffs

Playoff tournaments
-------------------

In a playoff tournament, the control file explicitly describes one or more
pairings of players (:dfn:`matchups`). Each matchup is treated independently.

.. todo:: rough mention of what can be configured in a matchup? Expand on 'is
   treated independently'?


Playoff settings
^^^^^^^^^^^^^^^^

The following settings can be set at the top level of the control file, for
competitions of type ``playoff``.

For the differences in tuning events, See :ref:`The Monte Carlo tuner
<mcts_control_file_settings>` and :ref:`The cross-entropy tuner
<cem_control_file_settings>`.

The only required settings are :setting:`competition_type`,
:setting:`players`, and :setting:`matchups`.


.. setting:: matchups

  List of :setting-cls:`Matchup` definitions (see :ref:`matchup
  configuration`).

  This defines which engines will play against each other, and the game
  settings they will use.

In addition to these, all matchup settings (except :setting:`id` and
:setting:`name`) can be set at the top of the control file. These settings
will be used for any matchups which don't explicitly override them.


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


.. setting:: board_size

  Integer

  The size of Go board to use for the games (eg ``19`` for a 19x19 game). The
  ringmaster is willing to use board sizes from 2 to 25.


.. setting:: komi

  Float

  The :term:`komi` to use for the games. You can specify any floating-point
  value, and it will be passed on to the |gtp| engines unchanged, but
  normally only integer or half-integer values will be useful. Negative
  values are allowed.


.. setting:: alternating

  Boolean (default ``False``)

  If this is ``True``, the players will swap colours in successive games.
  Otherwise, the first-named player always takes Black.


.. setting:: handicap

  Integer (default ``None``)

  Number of handicap stones to give Black at the start of the game. See also
  :setting:`handicap_style`.

  See the `GTP specification`_ for the rules about what handicap values
  are permitted for different board sizes (in particular, values less than 2
  are never allowed).


.. setting:: handicap_style

  String: ``"fixed"`` or ``"free"`` (default ``"fixed"``)

  Determines whether the handicap stones are placed on prespecified points, or
  chosen by the Black player. See the `GTP specification`_ for more details.

  This is ignored if :setting:`handicap` is unset.

  .. _GTP specification: http://www.lysator.liu.se/~gunnar/gtp/gtp2-spec-draft2/gtp2-spec.html#SECTION00051000000000000000



.. setting:: move_limit

  Integer (default ``1000``)

  Maximum number of moves to allow in a game. If this limit is reached, the
  game is stopped; see :ref:`playing games`.


.. setting:: scorer

  String: ``"players"`` or ``"internal"`` (default ``"players"``)

  Determines whether the game result is determined by the engines, or by the
  ringmaster. See :ref:`Scoring <scoring>` and :setting:`is_reliable_scorer`.


.. setting:: number_of_games

  Integer (default ``None``)

  The total number of games to play in the matchup. If you leave this unset,
  there will be no limit; see :ref:`stopping competitions`.

  Changing :setting:`!number_of_games` to ``0`` provides a way to effectively
  disable a matchup in future runs, without forgetting its results.
