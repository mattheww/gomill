The Gomill library
==================

Gomill is intended to be useful as a Python library for developing |gtp| and
|sgf|-based tools.


.. contents:: Page contents
   :local:
   :backlinks: none


Library status
--------------

As of Gomill |version|, the library API is not formally documented, and should
not be considered entirely stable.

Nonetheless, the source files contain fairly detailed documentation, and the
:ref:`example scripts <example scripts>` illustrate how various parts of the
library can be used.


Library overview
----------------

Generic support code

- :mod:`compact_tracebacks`
- :mod:`ascii_tables`
- :mod:`job_manager`
- :mod:`settings`


Go-related support code

- :mod:`gomill_common`
- :mod:`ascii_boards`
- :mod:`boards`
- :mod:`handicap_layout`


|sgf| support

- :mod:`sgf_reader`
- :mod:`sgf_writer`


|gtp| controller side

- :mod:`gtp_controller`
- :mod:`gtp_games`


|gtp| engine side

- :mod:`gtp_engine`
- :mod:`gtp_states`
- :mod:`gtp_proxy`


Competitions

- :mod:`competition_schedulers`
- :mod:`competitions`
- :mod:`cem_tuners`
- :mod:`mcts_tuners`
- :mod:`playoffs`


The Ringmaster

- :mod:`game_jobs`
- :mod:`terminal_input`
- :mod:`ringmaster_presenters`
- :mod:`ringmasters`
- :mod:`ringmaster_command_line`



.. _example scripts:

The example scripts
-------------------

The following example scripts are available in the :file:`gomill_examples/`
directory of the Gomill source distribution.

Some of them may be independently useful, as well as illustrating the library
API.

.. todo:: after install docs are written, say something about how to run them,
   or link to install docs for an explanation.


.. script:: find_forfeits.py

  Finds the forfeited games from a playoff competition.

  .. todo:: xref results API

  This demonstrates the results API.


.. script:: gtp_test_player

  A |gtp| engine intended for testing |gtp| controllers.

  This demonstrates the engine-side |gtp| code.


.. script:: gtp_stateful_player

  A |gtp| engine which maintains the board position.

  This demonstrates the :mod:`gtp_states` module, which can be used to make a
  |gtp| engine from a stateless move-generating program, or to add commands
  like :gtp:`undo` and :gtp:`loadsgf` to an engine which doesn't natively
  support them.


.. script:: kgs_proxy.py

  A |gtp| engine proxy intended for use with `kgsGtp`_. This produces game
  records including the engine's commentary, if the engine supports
  :gtp:`gomill-explain_last_move` and :gtp:`gomill-savesgf`.

  .. _`kgsGtp`: http://senseis.xmp.net/?KgsGtp

  This demonstrates the :mod:`gtp_proxy` module, and may be independently
  useful.


.. script:: mogo_wrapper.py

  A |gtp| engine proxy intended for use with `Mogo`_. This can be used to run
  Mogo with a |gtp| controller (eg `Quarry`_) which doesn't get on with Mogo's
  |gtp| implementation.

  .. _`Mogo`: http://www.lri.fr/~gelly/MoGo_Download.htm
  .. _`Quarry`: http://home.gna.org/quarry/

  This demonstrates the :mod:`gtp_proxy` module, and may be independently
  useful.


.. script:: show_sgf.py

  Prints an ASCII diagram of the position from an |sgf| file.

  This demonstrates the :mod:`sgf_reader` and :mod:`ascii_boards` modules.


.. script:: twogtp

  A 'traditional' twogtp implementation.

  This demonstrates the :mod:`gtp_games` module.

