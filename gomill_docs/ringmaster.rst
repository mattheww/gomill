The ringmaster
==============

The ringmaster is a command line program which arranges games between |gtp|
engines and keeps track of the results. See :ref:`cmdline` below for details
of the command line options.

.. index:: competition

The ringmaster takes its instructions from a single configuration file known
as the :ref:`control file <control file>`. Each control file defines a
:term:`competition`; the :ref:`output files <output files>` for that
competition are written to the directory containing the control file.


.. index:: run

A competition can take place over multiple invocations of the ringmaster
(:dfn:`runs`). For example, a run can be halted from the console, in which
case starting the ringmaster again will make it continue from where it left
off.


.. index:: competition type

The ringmaster supports a number of different :dfn:`competition types`.
Currently, two types of competition are supported:

.. index:: playoff, matchup

Playoffs
  In a playoff, the ringmaster plays many games between fixed player pairings
  (:dfn:`matchups`), to compare their strengths.

Tuning events
  In a :ref:`tuning event <tuners>`, the ringmaster runs an algorithm for
  adjusting player parameters to try to find the values which give strongest
  play.


.. _running competitions:

Running competitions
--------------------

When a competition is run, the ringmaster will launch games between pairs of
players, as described by the :setting:`matchup` descriptions in the control
file (for playoffs), or as specified by a tuning algorithm (for tuning
events).

It may play multiple games in parallel; see :ref:`parallel-games` below.

It normally displays a summary of the scores in each matchup (or of the tuning
algorithm status), a list of games in progress, and a list of recent game
results. Use :ref:`quiet mode <quiet mode>` to turn this display off.

Unless interrupted, the run will continue until the specified
:setting:`number_of_games` have been played for each matchup (indefinitely if
:setting:`number_of_games` is unset), or the limit specified by the
:option:`--max-games <ringmaster --max-games>` command line option is reached.

Use :kbd:`Ctrl-X` to stop a run. The ringmaster will wait for all games in
progress to complete, and then exit (the stop request won't be acknowledged on
screen until the next game result comes in).

It's also ok to stop a competition with :kbd:`Ctrl-C`; games in progress will
be terminated immediately (assuming the engine processes are well-behaved),
and the ringmaster will replay them as necessary if the competition is resumed
later.

You can also stop a competition by running the :program:`ringmaster`
:action:`stop` action from a shell; like :kbd:`Ctrl-X`, this will be
acknowledged when the next game result comes in, and the ringmaster will wait
for games in progress to complete.

.. todo:: document reset here? If not, where?


Players
^^^^^^^

The ringmaster requires the players to be standalone executables which speak
|gtp| on their standard input and output streams.

It launches the executables itself, as detailed by the :setting:`Player`
settings in the control file.

.. todo:: Probably worth an explicit link here to the setting docs, and maybe
   a brief summary of the sort of thing that can be configured.

It launches a new engine subprocess for each game and waits for it to
terminate as soon as the game is completed.

.. tip:: to run players on a different computer to the ringmaster,
   specify a suitable :program:`ssh` command line in the :setting:`Player`
   definition.

.. todo:: link to tedious docs about what happens if an engine fails
   to launch, and exit status.


Games
^^^^^

.. index:: rules

The :setting:`board_size`, :setting:`komi`, :setting:`handicap`, and
:setting:`handicap_style` settings control the details of the game. The
ringmaster doesn't know or care what rule variant the players are using; it's
up to you to make sure they agree with each other.

Each game normally continues until both players pass in succession, or one
player resigns.

The ringmaster rejects moves to occupied points, and moves forbidden by simple
ko, as illegal. It doesn't reject self-capture moves, and it doesn't enforce
any kind of :term:`superko` rule. If the ringmaster rejects a move, the engine
that tried to play it loses the game by forfeit.

If one of the players rejects a move as illegal (ie, with the |gtp| failure
response ``illegal move``), the ringmaster assumes its opponent really has
played an illegal move and so should forfeit the game (this is convenient if
you're testing an experimental engine against an established one).

If one of the players returns any other |gtp| failure response (either to
:gtp:`genmove` or to :gtp:`play`), or an uninterpretable response to
:gtp:`genmove`, it forfeits the game.

If the game lasts longer than the configured :setting:`move_limit`, it is
recorded as having an unknown result (with |sgf| result ``Void``).

See also :ref:`claiming wins`.

.. todo:: somewhere around here say whether failure response to commands like
   boardsize or handicap forfeits or voids the game or what.


Scoring
^^^^^^^

The ringmaster has two scoring methods: ``players`` (which is the default),
and ``internal``. The :setting:`scorer` setting determines which is used.

When the ``players`` method is used, the players are asked to score the game
using the |gtp| :gtp:`final_score` command. See also the
:setting:`is_reliable_scorer` setting.

When the ``internal`` method is used, the ringmaster scores the game itself,
area-fashion. It assumes that all stones remaining on the board at the end of
the game are alive. It doesn't apply any handicap stone compensation.


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
:setting:`discard_stderr` settings are ignored).

For playoffs, only players listed in matchups are checked. If a player appears
in more than one matchup, the board size and komi from its first matchup are
used.

For tuning events, the opponent and one sample candidate are checked.

The checks are as follows:

- the engine subprocess starts, and replies to |gtp| commands
- the engine reports |gtp| protocol version 2 (if it supports
  :gtp:`protocol_version` at all)
- the engine accepts any :setting:`startup_gtp_commands`
- the engine accepts the required board size and komi
- the engine accepts the :gtp:`clear_board` |gtp| command


.. _output files:

Output files
^^^^^^^^^^^^

.. index:: competition directory

The ringmaster writes a number of files, which it places in the directory
which contains the control file (the :dfn:`competition directory`). The
basename (the part before the file extension) of each file is the same as the
control file (:file:`{code}` in the table below).

The full set of files that may be present in the competition directory is:

======================= =======================================================
:file:`{code}.ctl`      the control file
:file:`{code}.status`   the competition state file
:file:`{code}.log`      the event log
:file:`{code}.hist`     the history file
:file:`{code}.report`   the full text report
:file:`{code}.cmd`      the remote control file
:file:`{code}.games/`   |SGF| game records
:file:`{code}.void/`    |SGF| game records for void games
:file:`{code}.gtplogs/` |GTP| logs
                        (from :option:`--log-gtp <ringmaster --log-gtp>`)
======================= =======================================================


.. _quiet mode:

Quiet mode
^^^^^^^^^^


Game records
^^^^^^^^^^^^

.. todo:: link to explain_last_move in gtp-extensions section.




Viewing competition results
---------------------------


.. _control file:

Control files
-------------

Commands are normally expressed as strings. They're not run via a shell, but
they're split into arguments in a shell-like way (see :func:`shlex.split`).
You can also use a list of strings explicitly. '~' (home directory) expansion
is applied to the the pathname of the executable (see
:func:`os.path.expanduser`).


Matchup settings
^^^^^^^^^^^^^^^^

.. setting:: number_of_games

  number of games to be played in the matchup. If you omit this setting or set
  it to :const:`None`, there will be no limit.


.. _cmdline:

Command line interface
----------------------

.. program:: ringmaster

.. index:: action; ringmaster

The ringmaster expects two command line arguments: the pathname of the control
file and an :dfn:`action`::

  $ ringmaster [options] <code>.ctl [run|show|reset|check|report|stop]

The control file must have extension :file:`.ctl`.

The default action is :action:`!run`, so running a competition is normally a
simple line like::

  $ ringmaster competitions/test.ctl

See :ref:`running competitions` above for details of how to stop the ringmaster.


The following actions are available:

.. action:: run

  Runs the competition. If the competition has been run already, it continues
  from where it left off.

.. action:: show

  Prints a report of the competition's current status.

.. action:: reset

  Cleans up the competition completely. This deletes all output files,
  including the competition's state file.

.. action:: check

  Runs a test invocation of the competition's players. This is the same as the
  :ref:`startup checks`, except that any output the players send to their
  standard error stream will be printed.

.. action:: report

  Rewrites the `competition report file`_ based on the current status.

.. action:: stop

  Tells a running ringmaster for the competition to stop as soon as the
  current game(s) have completed.

It's safe to run :action:`!show` or :action:`!report` on a competition which
is currently in progress.


Command-line options:

.. option:: --parallel <N>, -j <N>

   Use multiple processes.

.. option:: --quiet, -q

   Disable the on-screen reporting.

.. option:: --max-games <N>, -g <N>

   Maximum number of games to play in the run.

.. option:: --log-gtp

   Log all |gtp| traffic.

.. todo:: move the log-gtp para to the 'logging' section, and leave a
   reference instead.

If :option:`!--log-gtp` is set, the ringmaster logs all |gtp| commands and
responses. It writes a separate log file for each game, in the
:file:`{competition code}.gtplogs` directory.

.. todo:: Doc exit status

