.. _control file:

The control file
----------------

.. contents:: Page Contents
   :local:
   :backlinks: none


File format
^^^^^^^^^^^

Competition settings
^^^^^^^^^^^^^^^^^^^^

Player configuration
^^^^^^^^^^^^^^^^^^^^

Commands are normally expressed as strings. They're not run via a shell, but
they're split into arguments in a shell-like way (see :func:`shlex.split`).
You can also use a list of strings explicitly. '~' (home directory) expansion
is applied to the the pathname of the executable (see
:func:`os.path.expanduser`).


Matchup settings
^^^^^^^^^^^^^^^^

.. setting:: number_of_games

  number of games to be played in the matchup. If you omit this setting or set
  it to :const:`None`, there will be no limit.


