Changes
=======

The ringmaster now applies handicap stone compensation when using its internal
scorer. Set :setting:`internal_scorer_handicap_compensation` to ``"no"`` to
return to the old behaviour.

* Added support for handicap stone compensation when scoring games.

* Gomill now checks the response to the :gtp:`!fixed_handicap` |gtp| command.

* Added the :data:`gomill.__version__` constant.


Gomill 0.6 (2011-02-13)
-----------------------

Playoff tournament :ref:`state files <competition state>` from gomill 0.5 are
incompatible with gomill 0.6. Tuning event state files are compatible.

* Added :doc:`All-play-all <allplayalls>` tournament type.

* Expanded and documented the :doc:`tournament_results`. Changed return type
  of :meth:`~tournament_results.Tournament_results.get_matchup_results`.

* Fixed reporting for matchups with the same player specified twice.

* Allowed arbitrary filename extensions for control files.


Gomill 0.5 (2010-10-29)
-----------------------

* First public release.

