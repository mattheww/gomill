Introduction
============

Gomill is a suite of tools, and a Python library, for use in developing and
testing Go-playing programs. It is based around the Go Text Protocol
(:term:`GTP`) and the Smart Game Format (:term:`SGF`).

The principal tool is the :dfn:`ringmaster`, which plays programs against each
other and keeps track of the results.

Ringmaster features include:

- testing multiple pairings in one run
- playing multiple games in parallel
- displaying live results
- engine configuration by command line options or |gtp| commands
- a protocol for including per-move engine diagnostics in |sgf| output
- automatically tuning engine parameters based on game results
  (**experimental**)

.. contents:: Page contents
   :local:
   :backlinks: none


Ringmaster example
------------------

Create a file called :file:`demo.ctl`, with the following contents::

  competition_type = 'playoff'

  board_size = 9
  komi = 7.5

  players = {
      'gnugo-l1' : Player('gnugo --mode=gtp --level=1'),
      'gnugo-l2' : Player('gnugo --mode=gtp --level=2'),
      }

  matchups = [
      Matchup('gnugo-l1', 'gnugo-l2',
              alternating=True,
              number_of_games=5),
      ]

(If you don't have :program:`gnugo` installed, change the
:setting-cls:`Player` definitions to use a command line for whatever |gtp|
engine you have available.)

Then run ::

  $ ringmaster demo.ctl

The ringmaster will run five games between the two players, showing a summary
of the results on screen, and then exit.

(If the ringmaster is not already installed, see :doc:`install` for
instructions.)

The final display should be something like this::

  gnugo-l1 v gnugo-l2 (5/5 games)
  board size: 9   komi: 7.5
             wins              black        white      avg cpu
  gnugo-l1      2 40.00%       1 33.33%     1 50.00%      1.05
  gnugo-l2      3 60.00%       1 50.00%     2 66.67%      1.12
                               2 40.00%     3 60.00%

  = Results =
  game 0_0: gnugo-l2 beat gnugo-l1 W+21.5
  game 0_1: gnugo-l2 beat gnugo-l1 B+9.5
  game 0_2: gnugo-l2 beat gnugo-l1 W+14.5
  game 0_3: gnugo-l1 beat gnugo-l2 W+7.5
  game 0_4: gnugo-l1 beat gnugo-l2 B+2.5

The ringmaster will create several files named like :file:`demo.{xxx}` in the
same directory as :file:`demo.ctl`, including a :file:`demo.sgf` directory
containing game records.


The Python library
------------------

Gomill also provides a Python library for working with |gtp| and |sgf|, though
as of Gomill |version| only part of the API is stable. See :doc:`library` for
details.


The example scripts
-------------------

Some :doc:`example scripts <example_scripts>` are also included in the Gomill
distribution, as illustrations of the library interface and in some cases as
tools useful in themselves.


