The ringmaster
==============

The ringmaster is a command line program which arranges games between |gtp|
engines and keeps track of the results. See :ref:`cmdline` below for details
of the command line options.

.. contents:: Page contents
   :local:
   :backlinks: none

Competitions and runs
---------------------

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
These are divided into :dfn:`tournaments` and :dfn:`tuning events`.


Tournaments
-----------

In a tournament, the ringmaster plays games between predefined players, in
order to compare their strengths.

There are two kinds of tournament: playoff and all-play-all.

Playoff tournaments
  In a playoff tournament, the control file explicitly describes one or more
  pairings of players (:dfn:`matchups`). Each matchup is treated
  independently.

All-play-all tournaments
  In an all-play-all tournament, the control file lists a number of players, and
  games are played between each possible pairing.



Tuning events
-------------

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

