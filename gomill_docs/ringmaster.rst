The ringmaster
==============

The ringmaster can run different kinds of competition. A competition is a
resumable processing job based on playing many GTP games. It could be:

a :dfn:`playoff`
  In a playoff, the ringmaster plays many games between a fixed set of
  players, to compare their strength.

a :dfn:`tuning event`
  In a tuning event, the ringmaster runs an algorithm for adjusting player
  parameters to find a good configuration.


Control files
-------------

Commands are strings. They're not run via a shell, but they're split into
arguments in a shell-like way (see :func:`shlex.split`). '~' (home directory)
expansion is applied to the the pathname of the executable (see
:func:`os.path.expanduser`).


Matchup parameters
~~~~~~~~~~~~~~~~~~

.. confval:: number_of_games

  number of games to be played in the matchup. If you omit this setting or set
  it to :const:`None`, there will be no limit.



Usage
-----

For example::

  $ ringmaster <code>.tourn

runs a competition; continues from where it left off if interrupted.

::

  $ ringmaster <code>.tourn stop

tells a running competition to stop after the current game(s).

::

  $ ringmaster <code>.tourn show

prints a report from a competition's current status.

::

  $ ringmaster <code>.tourn reset

deletes all state and output for the competition.

::

  $ ringmaster <code>.tourn check

runs a test invocation of the competition's players.


.. program:: ringmaster

Command-line options:

.. cmdoption:: --parallel=<N>

   use multiple processes

.. cmdoption:: --quiet

   disable printing results after each game

.. cmdoption:: --max-games=<N>

   maximum number of games to play in the run

.. cmdoption:: --log-gtp

   log all GTP traffic

:option:`!--max-games` is independent of any :confval:`number_of_games`
settings in the control file; the run will halt if either limit is reached.

If :option:`!--log-gtp` is set, the ringmaster logs all GTP commands and
responses. It writes a separate log file for each game, in the
`<code>.sgflogs` directory.

It's ok to stop a competition with :kbd:`Ctrl-C`; incomplete games will be
rerun from scratch on the next run.

