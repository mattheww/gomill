The ringmaster
==============

The ringmaster is a command line program which arranges games between |gtp|
engines and keeps track of the results. See :doc:`ringmaster_cmdline` below
for details of the command line options.

.. contents:: Page contents
   :local:
   :backlinks: none

Competitions and runs
---------------------

.. index:: competition

The ringmaster takes its instructions from a single configuration file known
as the :doc:`control file <settings>`. Each control file defines a
:term:`competition`; the :ref:`output files <output files>` for that
competition are written to the directory containing the control file.


.. index:: run

A competition can take place over multiple invocations of the ringmaster
(:dfn:`runs`). For example, a run can be halted from the console, in which
case starting the ringmaster again will make it continue from where it left
off.


Competition types
-----------------

The ringmaster supports a number of different :dfn:`competition types`.
These are divided into :dfn:`tournaments` and :dfn:`tuning events`.

In a tournament, the ringmaster plays games between predefined players, in
order to compare their strengths. The types of tournament are:

Playoff tournaments
  In a playoff tournament the control file explicitly describes one or more
  pairings of players (:dfn:`matchups`). Each matchup can have separate
  settings.

All-play-all tournaments
  In an all-play-all tournament the control file lists a number of players, and
  games are played with the same settings between each possible pairing.

In a tuning event, the ringmaster runs an algorithm for adjusting player
parameters to try to find the values which give strongest play.

See :ref:`competition types` for full details of the types of tournament and
tuning event.




Using the ringmaster
--------------------

.. toctree::
   :maxdepth: 3
   :titlesonly:

   competitions
   results
   ringmaster_cmdline
   settings
   competition_types
   Error handling… <errors>

