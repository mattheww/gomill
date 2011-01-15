.. index:: competition type

.. _competition types:

Competition types
-----------------

The ringmaster supports a number of different :dfn:`competition types`. These
are divided into :dfn:`tournaments` and :dfn:`tuning events`.


.. contents:: Page contents
   :local:
   :backlinks: none


.. index:: tournament

.. _tournaments:

Tournaments
^^^^^^^^^^^

A :dfn:`tournament` is a form of competition in which the ringmaster plays
games between predefined players, in order to compare their strengths.


There are currently two types of tournament:

.. toctree::
   :maxdepth: 3
   :titlesonly:

   Playoff <playoffs>
   All-play-all <allplayalls>


.. index:: tuning event

.. _tuners:

Tuning events
^^^^^^^^^^^^^

A :dfn:`tuning event` is a form of competition in which the ringmaster runs an
algorithm which adjusts engine parameters to try to find the values which give
strongest play.

.. index:: opponent

At present, all tuning events work by playing games between different
:dfn:`candidate` players and a single fixed :dfn:`opponent` player. The
candidate always takes the same colour. The komi and any handicap can be
specified as usual.

There are currently two tuning algorithms:

.. toctree::
   :maxdepth: 3
   :titlesonly:

   Monte Carlo <mcts_tuner>
   Cross-entropy <cem_tuner>

