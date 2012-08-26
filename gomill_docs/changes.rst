Changes
=======


Gomill 0.7.4 (2012-08-26)
-------------------------

* Added the :envvar:`GOMILL_GAME_ID` and :envvar:`GOMILL_SLOT` environment
  variables.

* :mod:`~!gomill.gtp_games` now permits free-handicap games with the maximum
  number of handicap stones permitted by |gtp| (the previous restriction was
  one less).

* Bug fix: :meth:`.Board.is_empty()` was wrong after a self-capture which
  leaves the board empty.

* Documentation correction: the example in :ref:`using_the_api_in_scripts`
  showed :meth:`!Ringmaster.tournament_results` rather than
  :meth:`!Ringmaster.get_tournament_results`.


Gomill 0.7.3 (2012-05-02)
-------------------------

Bug-fix release.

* Made the documentation (index page) build properly with Sphinx v1.1.

* Documentation correction: failure responses from
  :setting:`startup_gtp_commands` are not ignored.

* Bug fix: internal scorer with
  :setting:`internal_scorer_handicap_compensation` ``"short"`` was off by one in
  a non-handicap game.

* Bug fix: :meth:`.Tree_node.new_child` was failing if it was called with an
  explicitly-specified index on the root node of an :class:`.Sgf_game` which
  was loaded from a string and had not otherwise had its structure modified.


Gomill 0.7.2 (2011-09-05)
-------------------------

* Added the *wrap* parameter to :meth:`.Sgf_game.serialise`.

* Added the :script:`gomill-clop` example script.


Gomill 0.7.1 (2011-08-15)
-------------------------

Bug-fix release.

* Bug fix: made board sizes 24 and 25 work (column lettering, and therefore
  |gtp| support, was incorrect for these sizes in all previous versions).

* Tightened up input validation for :func:`.format_vertex` and
  :func:`.colour_name`.

* Distinguished Stone, Point, and Move in the :ref:`sgf_property_types`
  table in |sgf| documentation.



Gomill 0.7 (2011-08-13)
-----------------------

The ringmaster now applies handicap stone compensation when using its internal
scorer. Set :setting:`internal_scorer_handicap_compensation` to ``"no"`` to
return to the old behaviour.

* Added a full implementation of :doc:`sgf`, replacing the previous minimal
  support.

* Added a :script:`split_sgf_collection.py` example script.

* The :mod:`~gomill.common`, :mod:`~gomill.boards`,
  :mod:`~gomill.ascii_boards`, and :mod:`~gomill.handicap_layout` modules are
  now documented as stable.

* Improved handling of long responses to the :gtp:`!version` |gtp| command.

* Added support for handicap stone compensation when scoring games.

* Gomill now checks the response to the :gtp:`!fixed_handicap` |gtp| command.

* Added the :data:`gomill.__version__` constant.


Changes to (previously) undocumented parts of the library:

* Renamed the :mod:`!gomill.gomill_common` module to :mod:`!gomill.common`.

* Renamed the :mod:`!gomill.gomill_utils` module to :mod:`!gomill.utils`.

* Renamed :attr:`!Board.board_coords` to :attr:`~.Board.board_points`.

* Replaced the :func:`!ascii_boards.play_diagram` function with
  :func:`~.ascii_boards.interpret_diagram`, making the *board* parameter
  optional.

* :func:`!gtp_engine.interpret_float` now rejects infinities and NaNs.

* Changes to the :mod:`!gtp_states` module: tightened error handling, removed
  the komi-mangling feature, renamed :attr:`!History_move.coords` to
  :attr:`!History_move.move`.


Gomill 0.6 (2011-02-13)
-----------------------

Playoff tournament :ref:`state files <competition state>` from Gomill 0.5 are
incompatible with Gomill 0.6. Tuning event state files are compatible.

* Added the :doc:`All-play-all <allplayalls>` tournament type.

* Expanded and documented the :doc:`tournament_results`. Changed return type
  of
  :meth:`~.Tournament_results.get_matchup_results`.

* Fixed reporting for matchups with the same player specified twice.

* Allowed arbitrary filename extensions for control files.


Gomill 0.5 (2010-10-29)
-----------------------

* First public release.

