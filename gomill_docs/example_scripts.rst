.. _example scripts:

The example scripts
===================

The following example scripts are available in the :file:`gomill_examples/`
directory of the Gomill source distribution.

Some of them may be independently useful, as well as illustrating the library
API.

See the top of each script for further information.

See :ref:`running the example scripts <running the example scripts>` for notes
on making the :mod:`!gomill` package available for use with the example
scripts.


.. script:: show_sgf.py

  Prints an ASCII diagram of the position from an |sgf| file.

  This demonstrates the :mod:`!sgf_reader` and :mod:`!ascii_boards` modules.


.. script:: twogtp

  A 'traditional' twogtp implementation.

  This demonstrates the :mod:`!gtp_games` module.


.. script:: find_forfeits.py

  Finds the forfeited games from a playoff competition.

  This demonstrates the library interface for :ref:`querying competition
  results <querying the results>`.


.. script:: gtp_test_player

  A |gtp| engine intended for testing |gtp| controllers.

  This demonstrates the low-level engine-side |gtp| code (the
  :mod:`!gtp_engine` module).


.. script:: gtp_stateful_player

  A |gtp| engine which maintains the board position.

  This demonstrates the :mod:`!gtp_states` module, which can be used to make a
  |gtp| engine from a stateless move-generating program, or to add commands
  like :gtp:`!undo` and :gtp:`!loadsgf` to an engine which doesn't natively
  support them.


.. script:: kgs_proxy.py

  A |gtp| engine proxy intended for use with `kgsGtp`_. This produces game
  records including the engine's commentary, if the engine supports
  :gtp:`gomill-savesgf`.

  .. _`kgsGtp`: http://senseis.xmp.net/?KgsGtp

  This demonstrates the :mod:`!gtp_proxy` module, and may be independently
  useful.


.. script:: mogo_wrapper.py

  A |gtp| engine proxy intended for use with `Mogo`_. This can be used to run
  Mogo with a |gtp| controller (eg `Quarry`_) which doesn't get on with Mogo's
  |gtp| implementation.

  .. _`Mogo`: http://www.lri.fr/~gelly/MoGo_Download.htm
  .. _`Quarry`: http://home.gna.org/quarry/

  This demonstrates the :mod:`!gtp_proxy` module, and may be independently
  useful.

