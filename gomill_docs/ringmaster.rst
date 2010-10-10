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

Commands are normally expressed as strings. They're not run via a shell, but
they're split into arguments in a shell-like way (see :func:`shlex.split`).
You can also use a list of strings explicitly. '~' (home directory) expansion
is applied to the the pathname of the executable (see
:func:`os.path.expanduser`).


Matchup parameters
~~~~~~~~~~~~~~~~~~

.. confval:: number_of_games

  number of games to be played in the matchup. If you omit this setting or set
  it to :const:`None`, there will be no limit.



Usage
-----

.. program:: ringmaster

The ringmaster is a command line application. It expects two arguments: the
control file and a command::

  $ ringmaster [options] <control file> [run|show|reset|check|report|stop]

The default command is :option:`run`, so running a competition is normally as
simple as::

  $ ringmaster tournaments/test.ctl


The following commands are available:

.. cmdoption:: run

  Runs the competition. If the competition has been run already, it continues
  from where it left off.

.. cmdoption:: show

  Prints a report of the competition's current status.

.. cmdoption:: reset

  Cleans up the competition completely. This deletes all output files,
  including the competition's state file.

.. cmdoption:: check

  Runs a test invocation of the competition's players. This is the same as the
  startup checks (see FIXME), except that any output the players send to their
  standard error stream will be printed.

.. cmdoption:: report

  Rewrites the competition report file (FIXME: ref) based on the current
  status.

.. cmdoption:: stop

  Tells a running competition to stop as soon as the current game(s) have
  completed.


It's safe to run :option:`show` or :option:`report` on a competition which
is currently in progress.




Command-line options:

.. cmdoption:: --parallel=<N>

   Use multiple processes.

.. cmdoption:: --quiet

   Disable the on-screen reporting.

.. cmdoption:: --max-games=<N>

   Maximum number of games to play in the run.

.. cmdoption:: --log-gtp

   Log all GTP traffic.

:option:`!--max-games` is independent of any :confval:`number_of_games`
settings in the control file; the run will halt if either limit is reached.

If :option:`!--log-gtp` is set, the ringmaster logs all GTP commands and
responses. It writes a separate log file for each game, in the
`<code>.sgflogs` directory. (FIXME: Define <code>).

It's ok to stop a competition with :kbd:`Ctrl-C`; any interrupted games will
be rerun from scratch on the next run. (FIXME: Not quite true now.)

