Introduction
============


Example usage
-------------

Create a file called :file:`demo.ctl`, with the following contents::

  competition_type = 'playoff'

  board_size = 9
  komi = 7.5
  move_limit = 200
  record_games = True

  players = {
      'gnugol1' : Player('gnugo --mode=gtp --level=1'),
      'gnugol2' : Player('gnugo --mode=gtp --level=2'),
      }

  matchups = [
      Matchup('gnugol1', 'gnugol2', number_of_games=5),
      ]

(If you don't have gnugo installed, change the Players to include a command
line for whatever GTP engine you have available.)

Then run ::

  $ ringmaster demo.ctl

The ringmaster will run five games between the two players, showing a summary
of the results on screen. It will create several files named like
:file:`demo.{xxx}` in the same directory as :file:`demo.ctl`, including a
:file:`demo.sgf` directory containing game records.

