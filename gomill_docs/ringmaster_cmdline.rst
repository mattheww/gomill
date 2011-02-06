Command line
^^^^^^^^^^^^

.. program:: ringmaster

.. index:: action; ringmaster

The ringmaster expects two command line arguments: the pathname of the control
file and an :dfn:`action`::

  ringmaster [options] <code>.ctl run
  ringmaster [options] <code>.ctl show
  ringmaster [options] <code>.ctl reset
  ringmaster [options] <code>.ctl check
  ringmaster [options] <code>.ctl report
  ringmaster [options] <code>.ctl stop

The default action is :action:`!run`, so running a competition is normally a
simple line like::

  $ ringmaster competitions/test.ctl

See :ref:`Stopping competitions <stopping competitions>` for the various ways
to stop the ringmaster.


The following actions are available:

.. action:: run

  Starts the competition running. If the competition has been run previously,
  it continues from where it left off.

.. action:: show

  Prints a :ref:`report <competition report file>` of the competition's
  current status. This can be used for both running and stopped competitions.

.. action:: reset

  Cleans up the competition completely. This deletes all output files,
  including the competition's :ref:`state file <competition state>`.

.. action:: check

  Runs a test invocation of the competition's players. This is the same as the
  :ref:`startup checks`, except that any output the players send to their
  standard error stream will be printed.

.. action:: report

  Rewrites the :ref:`competition report file <competition report file>` based
  on the current status. This can be used for both running and stopped
  competitions.

.. action:: stop

  Tells a running ringmaster for the competition to stop as soon as the
  current games have completed.


The following options are available:

.. option:: --parallel <N>, -j <N>

   Play N :ref:`simultaneous games <simultaneous games>`.

.. option:: --quiet, -q

   Disable the on-screen reporting; see :ref:`Quiet mode <quiet mode>`.

.. option:: --max-games <N>, -g <N>

   Maximum number of games to play in the run; see :ref:`running
   competitions`.

.. option:: --log-gtp

   Log all |gtp| traffic; see :ref:`logging`.

