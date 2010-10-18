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
report that is displayed while the competition is running. It also includes
descriptions of the players, and the contents of the competition's
:setting:`description` setting. For example::

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


.. todo:: Mention void and unfinished games, and forfeits (ie, say what the
   distinction is.

.. todo:: say anything about player codes and matchup codes? And
   describe_engine. Possibly a ^^^-level heading for player descriptions.


The :action:`report` command line action rewrites the competition report file.
This can be useful if you have changed descriptive text in the control file,
or if a run stopped ungracefully and didn't write the report.

The :action:`show` command line action prints the same report to standard
output.

It's safe to run :action:`show` or :action:`report` on a competition which is
currently in progress.


.. _game records:

Game records
^^^^^^^^^^^^

The ringmaster writes an |sgf| record of each game it plays to the
:file:`{code}.games/` directory (which it will create if necessary). This can
be disabled with the :setting:`record_games` setting.

(You might also see game records in a :file:`{code}.void/` directory; these
are games which FIXME; see :ref:`FIXME`.)

The ringmaster supports a protocol for engines to provide text to be placed in
the comment section for individual moves: see :gtp:`gomill-explain_last_move`.

The game record includes a description of the players in the root node comment
[#]_. If an engine implements :gtp:`gomill-describe_engine`, its output is
included.

.. todo:: say that the filenames are game ids? or mention that they include
   matchup codes? See 'SGF output' in ringmaster.txt.

.. [#] The root node comment is used rather than the game comment because (in
   my experience) |sgf| viewers tend to make it easier to see information
   there.


CPU time
^^^^^^^^

The reports and game records show the CPU time taken by the players, when
available.

If an engine implements the :gtp:`gomill-cpu_time` command, its output is
used. Otherwise, the ringmaster uses the CPU time of the engine process that
it created, as returned by the :c:func:`wait4()` system call (unfortunately,
this may not be meaningful, if the engine's work isn't all done directly in
that process).



Querying the results
^^^^^^^^^^^^^^^^^^^^

.. todo:: some reference to sample scripts, results API.


