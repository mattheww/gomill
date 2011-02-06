Viewing results
---------------

.. contents:: Page contents
   :local:
   :backlinks: none

.. _competition report file:
.. index:: report file

Reports
^^^^^^^

The competition :dfn:`report file` (:file:`{code}.report`) file is a plain
text description of the competition results. This is similar to the live
report that is displayed while the competition is running. It includes the
contents of the competition's :setting:`description` setting.

For tournaments, it also shows descriptions of the players. These are obtained
using the |gtp| :gtp:`!name` and :gtp:`!version` commands, or using
:gtp:`gomill-describe_engine` if the engine provides it.

For example, in a playoff tournament with a single matchup::

  playoff: example

  Testing GNU Go level 1 vs level 2, 2010-10-14

  gnugo-l1 v gnugo-l2 (5/5 games)
  board size: 9   komi: 7.5
             wins              black        white      avg cpu
  gnugo-l1      2 40.00%       1 33.33%     1 50.00%      1.23
  gnugo-l2      3 60.00%       1 50.00%     2 66.67%      1.39
                               2 40.00%     3 60.00%

  player gnugo-l1: GNU Go:3.8
  player gnugo-l2: GNU Go:3.8


The report file is written automatically at the end of each run. The
:action:`report` command line action forces it to be rewritten; this can be
useful if you have changed descriptive text in the control file, or if a run
stopped ungracefully.

The :action:`show` command line action prints the same report to standard
output.

It's safe to run :action:`show` or :action:`report` on a competition which is
currently being run.


.. _game records:

Game records
^^^^^^^^^^^^

The ringmaster writes an |sgf| record of each game it plays to the
:file:`{code}.games/` directory (which it will create if necessary). This can
be disabled with the :setting:`record_games` setting. The filename is based on
the game's :ref:`game_id <game id>`.

(You might also see game records in a :file:`{code}.void/` directory; these
are games which were abandoned due to software failure; see :ref:`void
games`.)

The ringmaster supports a protocol for engines to provide text to be placed in
the comment section for individual moves: see :gtp:`gomill-explain_last_move`.

The game record includes a description of the players in the root node comment
[#]_. If an engine implements :gtp:`gomill-describe_engine`, its output is
included.

.. [#] The root node comment is used rather than the game comment because (in
   my experience) |sgf| viewers tend to make it easier to see information
   there.


.. index:: CPU time
.. index:: time; CPU

.. _cpu time:

CPU time
^^^^^^^^

The reports and game records show the CPU time taken by the players, when
available.

If an engine implements the :gtp:`gomill-cpu_time` command, its output is
used. Otherwise, the ringmaster uses the CPU time of the engine process that
it created, as returned by the :c:func:`!wait4()` system call (user plus system
time); unfortunately, this may not be meaningful, if the engine's work isn't
all done directly in that process.


.. _querying the results:

Querying the results
^^^^^^^^^^^^^^^^^^^^

Gomill provides a Python library interface for processing the game results
stored in a tournament's :ref:`state file <competition state>`.

This is documented in :doc:`tournament_results`. See also the
:script:`find_forfeits.py` example script.

