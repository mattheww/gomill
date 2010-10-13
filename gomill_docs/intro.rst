Introduction
============

Gomill is a suite of tools, and a Python library, for use in developing and
testing Go-playing programs. It is based around the Go Text Protocol
(:term:`GTP`) and the Smart Game Format (:term:`SGF`).

.. todo: refs for GTP and SGF.

The principal tool is the :dfn:`ringmaster`, which plays programs against each
other and keeps track of the results.

Ringmaster features include:

- testing multiple pairings in one run
- playing multiple games in parallel
- displaying live results
- engine configuration by command-line options or |gtp| commands
- a protocol for per-move engine diagnostics in |sgf| output

There is also experimental support for automatically tuning player parameters
based on the game results.


Ringmaster example
------------------

Create a file called :file:`demo.ctl`, with the following contents::

  competition_type = 'playoff'

  board_size = 9
  komi = 7.5
  record_games = True

  players = {
      'gnugo-l1' : Player('gnugo --mode=gtp --level=1'),
      'gnugo-l2' : Player('gnugo --mode=gtp --level=2'),
      }

  matchups = [
      Matchup('gnugo-l1', 'gnugo-l2', number_of_games=5),
      ]

(If you don't have :program:`gnugo` installed, change the Players to use a
command line for whatever |gtp| engine you have available.)

Then run ::

  $ ringmaster demo.ctl

The ringmaster will run five games between the two players, showing a summary
of the results on screen, and then exit. It will create several files named
like :file:`demo.{xxx}` in the same directory as :file:`demo.ctl`, including a
:file:`demo.sgf` directory containing game records.


Other tools
-----------

.. todo:: refer to the page about them, brief summary here.


The Python library
------------------

.. todo:: say the API isn't stable as of Gomill |version|, refer to page about
          it.
