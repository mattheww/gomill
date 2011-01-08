.. index:: tuning event

.. _tuners:

Tuning events
=============

A :dfn:`tuning event` is a form of :term:`competition` in which the ringmaster
runs an algorithm which adjusts engine parameters to try to find the values
which give strongest play.

.. index:: opponent

At present, all tuning events work by playing games between different
:dfn:`candidate` players and a single fixed :dfn:`opponent` player. The
candidate always takes the same colour. The komi and any handicap can be
specified as usual.

There are currently two types of tuning event, which are documented
independently.


Specific tuners
---------------

.. toctree::
   :maxdepth: 2
   :titlesonly:

   mcts_tuner
   cem_tuner

