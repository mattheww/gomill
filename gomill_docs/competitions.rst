.. _running competitions:

Running competitions
--------------------

.. contents:: Page contents
   :local:
   :backlinks: none


Pairings
^^^^^^^^

When a competition is run, the ringmaster will launch one or more games
between pairs of players.

For playoff tournaments, the pairings are determined by the
:pl-setting-cls:`Matchup` descriptions in the control file. If more than one
matchup is specified, the ringmaster prefers to start games from the matchup
which has played fewest games.

For all-play-all tournaments, the ringmaster will again prefer the pair of
:aa-setting:`competitors` which has played the fewest games.

For tuning events, the pairings are specified by a tuning algorithm.


.. index:: game_id

.. _game id:

Game identification
^^^^^^^^^^^^^^^^^^^

Each game played in a competition is identified using a short string (the
:dfn:`game_id`). This is used in the |sgf| :ref:`game record <game records>`
filename and game name (``GN``), the :ref:`log files <logging>`, the live
display, and so on.

For playoff tournaments, game ids are made up from the :pl-setting:`matchup id
<id>` and the number of the game within the matchup; for example, the first
game played might be ``0_0`` or ``0_000`` (depending on the value of
:pl-setting:`number_of_games`).

Similarly for all-play-all tournaments, game ids are like ``AvB_0``, using the
competitor letters shown in the results grid, with the length depending on the
:aa-setting:`rounds` setting.


.. _simultaneous games:

Simultaneous games
^^^^^^^^^^^^^^^^^^

The ringmaster can run more than one game at a time, if the
:option:`--parallel <ringmaster --parallel>` command line option is specified.

This can be useful to keep processor cores busy, or if the actual playing
programs are running on different machines to the ringmaster.

Normally it makes no difference whether the ringmaster starts games in
sequence or in parallel, but it does have an effect on the :doc:`Monte Carlo
tuner <mcts_tuner>`, as in parallel mode it will have less information each
time it chooses a candidate player.

.. tip:: Even if an engine is capable of using multiple threads, it may be
   better to use a single-threaded configuration during development to get
   reproducible results, or to be sure that system load does not affect play.

.. tip:: When deciding how many games to run in parallel, remember to take
   into account the amount of memory needed, as well as the number of
   processor cores available.


.. _live_display:

Display
^^^^^^^

While the competition runs, the ringmaster displays a summary of the
tournament results (or of the tuning algorithm status), a list of games in
progress, and a list of recent game results. For example, in a playoff
tournament with a single matchup::

  2 games in progress: 0_2 0_4
  (Ctrl-X to halt gracefully)

  gnugo-l1 v gnugo-l2 (3/5 games)
  board size: 9   komi: 7.5
             wins              black         white      avg cpu
  gnugo-l1      2 66.67%       1 100.00%     1 50.00%      1.13
  gnugo-l2      1 33.33%       1  50.00%     0  0.00%      1.32
                               2  66.67%     1 33.33%

  = Results =
  game 0_1: gnugo-l2 beat gnugo-l1 B+8.5
  game 0_0: gnugo-l1 beat gnugo-l2 B+33.5
  game 0_3: gnugo-l1 beat gnugo-l2 W+2.5

Use :ref:`quiet mode <quiet mode>` to turn this display off.


.. _stopping competitions:

Stopping competitions
^^^^^^^^^^^^^^^^^^^^^

Unless interrupted, a run will continue until either the competition completes
or the per-run limit specified by the :option:`--max-games
<ringmaster --max-games>` command line option is reached.

Type :kbd:`Ctrl-X` to stop a run. The ringmaster will wait for all games in
progress to complete, and then exit (the stop request won't be acknowledged on
screen until the next game result comes in).

It's also reasonable to stop a run with :kbd:`Ctrl-C`; games in progress will
be terminated immediately (assuming the engine processes are well-behaved).
The partial games will be forgotten; the ringmaster will replay them as
necessary if the competition is resumed later.

You can also stop a competition by running the command line :action:`stop`
action from a shell; like :kbd:`Ctrl-X`, this will be acknowledged when the
next game result comes in, and the ringmaster will wait for games in progress
to complete.


Running players
^^^^^^^^^^^^^^^

The ringmaster requires the player engines to be standalone executables which
speak :term:`GTP` version 2 on their standard input and output streams.

It launches the executables itself, with command line arguments and other
environment as detailed by the :ref:`player settings <player configuration>`
in the control file. See also :ref:`environment variables` and :ref:`standard
error` below.

It launches a new engine subprocess for each game and closes it when the game
is terminated.

.. tip:: To run a player on a different computer to the ringmaster, specify a
   suitable :program:`ssh` command line in the :setting-cls:`Player`
   definition.

See :ref:`engine errors` and :ref:`engine exit behaviour` for details of what
happens if engines misbehave.


.. index:: rules, ko, superko

.. _playing games:

Playing games
^^^^^^^^^^^^^

The :setting:`board_size`, :setting:`komi`, :setting:`handicap`, and
:setting:`handicap_style` game settings control the details of the game. The
ringmaster doesn't know or care what rule variant the players are using; it's
up to you to make sure they agree with each other.

Any :setting:`startup_gtp_commands` configured for a player will be sent
before the :gtp:`!boardsize` and :gtp:`!clear_board` commands. Non-failure
responses from these commands are ignored.

Each game normally continues until both players pass in succession, or one
player resigns.

The ringmaster rejects moves to occupied points, and moves forbidden by
:term:`simple ko`, as illegal. It doesn't reject self-capture moves, and it
doesn't enforce any kind of :term:`superko` rule. If the ringmaster rejects a
move, the player that tried to make it loses the game by forfeit.

If one of the players rejects a move as illegal (ie, with the |gtp| failure
response ``illegal move``), the ringmaster assumes its opponent really has
played an illegal move and so should forfeit the game (this is convenient if
you're testing an experimental engine against an established one).

If one of the players returns any other |gtp| failure response (either to
:gtp:`!genmove` or to :gtp:`!play`), or an uninterpretable response to
:gtp:`!genmove`, it forfeits the game.

If the game lasts longer than the configured :setting:`move_limit`, it is
stopped at that point, and recorded as having an unknown result (with |sgf|
result ``Void``).

See also :ref:`claiming wins`.

.. note:: The ringmaster does not provide a game clock, and it does not
   use any of the |gtp| time handling commands. Players should normally be
   configured to use a fixed amount of computing power, independent of
   wall-clock time.


.. index:: handicap compensation

.. _scoring:

Scoring
^^^^^^^

The ringmaster has two scoring methods: ``players`` (which is the default),
and ``internal``. The :setting:`scorer` game setting determines which is used.

When the ``players`` method is used, the players are asked to score the game
using the |gtp| :gtp:`!final_score` command. See also the
:setting:`is_reliable_scorer` player setting.

When the ``internal`` method is used, the ringmaster scores the game itself,
area-fashion. It assumes that all stones remaining on the board at the end of
the game are alive. It applies :setting:`komi`.

In handicap games, the internal scorer can also apply handicap stone
compensation, controlled by the
:setting:`internal_scorer_handicap_compensation` game setting: ``"full"`` (the
default) means that White is given an additional point for each handicap
stone, ``"short"`` means White is given an additional point for each handicap
stone except the first, and ``"no"`` means that no handicap stone compensation
is given.


.. _claiming wins:

Claiming wins
^^^^^^^^^^^^^

The ringmaster supports a protocol to allow players to declare that they have
won the game. This can save time if you're testing against opponents which
don't resign.

To support this, the player has to implement :gtp:`gomill-genmove_ex` and
recognise the ``claim`` keyword.

You must also set :setting:`allow_claim` ``True`` in the :setting-cls:`Player`
definition for this mechanism to be used.

The |sgf| result of a claimed game will simply be ``B+`` or ``W+``.


.. _startup checks:

Startup checks
^^^^^^^^^^^^^^

Whenever the ringmaster starts a run, before starting any games, it launches
an instance of each engine that will be required for the run and checks that
it operates reasonably.

If any engine fails the checks, the run is cancelled. The standard error
stream from the engines is suppressed for these automatic startup checks.

The :action:`check` command line action runs the same checks, but it leaves
the engines' standard error going to the console (any
:setting:`discard_stderr` player settings are ignored).

For playoff tournaments, only players listed in matchups are checked (and
matchups with :pl-setting:`number_of_games` set to ``0`` are ignored). If a
player appears in more than one matchup, the board size and komi from its
first matchup are used.

For all-play-all tournaments, all players listed as :aa-setting:`competitors`
are checked.

For tuning events, the opponent and one sample candidate are checked.

The checks are as follows:

- the engine subprocess starts, and replies to |gtp| commands
- the engine reports |gtp| protocol version 2 (if it supports
  :gtp:`!protocol_version` at all)
- the engine accepts any :setting:`startup_gtp_commands`
- the engine accepts the required board size and komi
- the engine accepts the :gtp:`!clear_board` |gtp| command

If your engine needs to know whether it is being run for the purpose of
startup checks, it can check the :envvar:`GOMILL_GAME_ID` environment
variable.


.. _quiet mode:

.. index:: quiet mode

Quiet mode
^^^^^^^^^^

The :option:`--quiet <ringmaster --quiet>` command line option makes the
ringmaster run in :dfn:`quiet mode`. In this mode, it prints nothing to
standard output, and only errors and warnings to standard error.

This mode is suitable for running in the background.

:kbd:`Ctrl-X` still works in quiet mode to stop a run gracefully, if the
ringmaster process is in the foreground.


.. _output files:

.. _competition directory:

Output files
^^^^^^^^^^^^

.. index:: competition directory

The ringmaster writes a number of files, which it places in the directory
which contains the control file (the :dfn:`competition directory`). The
filename stem (the part before the filename extension) of each file is the
same as in the control file (:file:`{code}` in the table below).

The full set of files that may be present in the competition directory is:

======================= =======================================================
:file:`{code}.ctl`      the :doc:`control file <settings>`
:file:`{code}.status`   the :ref:`competition state <competition state>` file
:file:`{code}.log`      the :ref:`event log <logging>`
:file:`{code}.hist`     the :ref:`history file <logging>`
:file:`{code}.report`   the :ref:`report file <competition report file>`
:file:`{code}.cmd`      the :ref:`remote control file <remote control file>`
:file:`{code}.games/`   |sgf| :ref:`game records <game records>`
:file:`{code}.void/`    |sgf| game records for :ref:`void games <void games>`
:file:`{code}.gtplogs/` |gtp| logs
                        (from :option:`--log-gtp <ringmaster --log-gtp>`)
======================= =======================================================

The recommended filename extension for the control file is :file:`.ctl`, but
other extensions are allowed (except those listed in the table above).


.. _competition state:

Competition state
^^^^^^^^^^^^^^^^^

.. index:: state file

The competition :dfn:`state file` (:file:`{code}.state`) contains a
machine-readable description of the competition's results; this allows
resuming the competition, and also programmatically :ref:`querying the results
<querying the results>`. It is rewritten after each game result is received,
so that little information will be lost if the ringmaster stops ungracefully
for any reason.

The :action:`reset` command line action deletes **all** competition output
files, including game records and the state file.

State files written by one Gomill release may not be accepted by other
releases. See :doc:`changes` for details.

.. caution:: If the ringmaster loads a state file written by a hostile party,
   it can be tricked into executing arbitrary code. On a shared system, do not
   make the competition directory or the state file world-writeable.


.. index:: logging, event log, history file

.. _logging:

Logging
^^^^^^^

The ringmaster writes two log files: the :dfn:`event log` (:file:`{code}.log`)
and the :dfn:`history file` (:file:`{code}.hist`).

The event log has entries for competition runs starting and finishing and for
games starting and finishing, including details of errors from games which
fail. It may also include output from the players' :ref:`standard error
streams <standard error>`, depending on the :setting:`stderr_to_log` setting.

The history file has entries for game results, and in tuning events it
may have periodic descriptions of the tuner status.

Also, if the :option:`--log-gtp <ringmaster --log-gtp>` command line option is
passed, the ringmaster logs all |gtp| commands and responses. It writes a
separate log file for each game, in the :file:`{code}.gtplogs` directory.


.. _environment variables:

Players' environment variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The players are given a copy of the ringmaster's environment variables,
supplemented (or overridden) by any variables specified by the
:setting:`environ` player setting.

The following environment variables are also set:

.. envvar:: GOMILL_GAME_ID

  The :ref:`game_id <game id>` of the game which will be played.

  When an engine is launched for the :ref:`startup checks <startup checks>`,
  this variable's value is ``startup-check``.

.. envvar:: GOMILL_SLOT

  If the ringmaster is configured to play up to N :ref:`simultaneous games
  <simultaneous games>`, this variable is set to one of N distinct strings,
  such that both of the engines playing one game are given the same string,
  but otherwise no two engines which are running simultaneously are given the
  same string.

  (Less formally: the ringmaster uses N worker processes to manage the games,
  and the slot values are simply integers from 0 to N-1 identifying the
  workers.)

  If the ringmaster is not configured to play simultaneous games, this
  variable is left unset.

  When an engine is launched for the :ref:`startup checks <startup checks>`,
  this variable is left unset.


.. index:: standard error, stderr

.. _standard error:

Players' standard error
^^^^^^^^^^^^^^^^^^^^^^^

By default, the players' standard error streams are sent to the ringmaster's
:ref:`event log <logging>`. All players write to the same log, so there's no
direct indication of which messages came from which player (the log entries
for games starting and completing may help).

If the competition setting :setting:`stderr_to_log` is False, the players'
standard error streams are left unchanged from the ringmaster's. This is only
useful in :ref:`quiet mode <quiet mode>`, or if you redirect the ringmaster's
standard error.

You can send standard error for a particular player to :file:`/dev/null` using
the player setting :setting:`discard_stderr`. This can be used for players
which like to send copious diagnostics to stderr, but if possible it is better
to configure the player not to do that, so that any real error messages aren't
hidden (eg with a command line option like ``fuego --quiet``).

