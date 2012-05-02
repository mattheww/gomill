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

  This demonstrates the :mod:`~gomill.sgf`, :mod:`~gomill.sgf_moves`, and
  :mod:`~gomill.ascii_boards` modules.


.. script:: split_sgf_collection.py

  Splits a file containing an |sgf| game collection into multiple files.

  This demonstrates the parsing functions from the :mod:`!sgf_grammar` module.


.. script:: twogtp

  A 'traditional' twogtp implementation.

  This demonstrates the :mod:`!gtp_games` module.


.. script:: find_forfeits.py

  Finds the forfeited games from a playoff or all-play-all tournament.

  This demonstrates the :doc:`tournament results API <tournament_results>`.


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

  .. _`Mogo`: http://www.lri.fr/~teytaud/mogo.html
  .. _`Quarry`: http://home.gna.org/quarry/

  This demonstrates the :mod:`!gtp_proxy` module, and may be independently
  useful.


.. script:: gomill-clop

  An experimental script for using Gomill as a back end for Rémi Coulom's CLOP
  optimisation system. It has been tested with ``CLOP-0.0.8``, which can be
  downloaded from http://remi.coulom.free.fr/CLOP/ .

  To use it, write a control file based on :file:`clop_example.ctl` in the
  :file:`gomill_examples/` directory, and run ::

    $ gomill-clop <control file> setup

  That will create a :samp:`.clop` file in the same directory as the control
  file, which you can then run using :samp:`clop-gui`.

