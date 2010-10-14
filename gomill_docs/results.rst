Viewing results
---------------

Once a run has completed, there are a number of ways to view its results.

.. contents:: Contents
   :local:

.. _competition report file:
.. index:: report file

Reports
^^^^^^^

The competition :dfn:`report file` (:file:`{code}.report`) file is a plain
text description of the competition results. This is similar to the live
report that is displayed while the competition is running. It also includes
descriptions of the players, and the contents of the competition's
:setting:`description` setting.

The :action:`report` command line action rewrites the competition report file.
This can be useful if you have changed descriptive text in the control file,
or if a run stopped ungracefully and didn't write the report.

The :action:`show` command line action prints the same report to standard
output.

It's safe to run :action:`show` or :action:`report` on a competition which is
currently in progress.


.. todo:: some reference to sample scripts, results API.



Game records
^^^^^^^^^^^^

The ringmaster writes an |sgf| record of each game it plays to the
:file:`{code}.games/` directory (which it will create if necessary). This can
be disabled with the :setting:`record_games` setting.

(You might also see game records in a :file:`{code}.void/` directory; these
are games which FIXME; see :ref:`FIXME`.)

The ringmaster supports a protocol for engines to provide text to be placed in
the comment section for individual moves: see :gtp:`gomill-explain_last_move`.

.. todo:: say that the filenames are game ids? or mention that they include
   matchup codes?


.. index:: logging, event log, history file


.. _logging:

Logging
^^^^^^^

The ringmaster writes two log files: the :dfn:`event log` (:file:`{code}.log`)
and the :dfn:`history file` (:file:`{code}.hist`).

The event log has entries for competition runs starting and finishing and for
games starting and finishing, including details of errors from games which
fail. It may also include output from the players' :ref:`standard error
streams <FIXME>`, depending on the :setting:`stderr_to_log` setting.

The history file has entries for game results, and in tuning events it
may have periodic descriptions of the tuner status.

