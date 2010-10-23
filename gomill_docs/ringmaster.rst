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
Currently, three types of competition are supported:

.. index:: playoff, matchup

Playoffs
  In a playoff, the ringmaster plays many games between fixed player pairings
  (:dfn:`matchups`), to compare their strengths.

Tuning events
  In a :ref:`tuning event <tuners>`, the ringmaster runs an algorithm for
  adjusting player parameters to try to find the values which give strongest
  play.

  There are two types of tuning event, :doc:`Monte Carlo <mcts_tuner>` and
  :doc:`cross-entropy <cem_tuner>`.


Using the ringmaster
--------------------

.. toctree::
   :maxdepth: 2
   :titlesonly:

   competitions
   results
   settings
   ringmaster_cmdline

