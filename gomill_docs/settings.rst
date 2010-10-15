.. _control file:

The control file
----------------

.. contents:: Page contents
   :local:
   :backlinks: none


File format
^^^^^^^^^^^

.. todo:: remember encoding stuff


.. _sample control file:

Sample control file
^^^^^^^^^^^^^^^^^^^

Here is a sample control file, illustrating most of the available settings::

  competition_type = 'playoff'

  description = """\
  This is a sample configuration file.

  It illustrates most of the available settings for a playoff.
  """

  record_games = True
  stderr_to_log = False

  players = {
    # GNU Go level 1
    'gnugo-l1' : Player("gnugo --mode=gtp --chinese-rules "
                        "--capture-all-dead --level=1"),

    # GNU Go level 2
    'gnugo-l2' : Player("gnugo --mode=gtp --chinese-rules "
                        "--capture-all-dead --level=2"),

    # Fuego at 5000 playouts per move
    'fuego-5k' : Player("fuego --quiet",
                        startup_gtp_commands=[
                            "go_param timelimit 999999",
                            "uct_max_memory 350000000",
                            "uct_param_search number_threads 1",
                            "uct_param_player reuse_subtree 0",
                            "uct_param_player ponder 0",
                            "uct_param_player max_games 5000",
                            ]),
      }

  board_size = 9
  komi = 6

  matchups = [
      Matchup('gnugo-l1', 'fuego-5k', board_size=13,
              handicap=2, handicap_style='free',
              scorer='players', number_of_games=5),

      Matchup('gnugo-l2', 'fuego-5k', alternating=True,
              scorer='players'),

      Matchup('gnugo-l1', 'gnugo-l2', alternating=True,
              komi=0.5,
              scorer='internal'),
      ]


.. _file and directory names:

File and directory names
^^^^^^^^^^^^^^^^^^^^^^^^

When control file settings are file or directory names, non-absolute names are
interpreted relative to the :ref:`competition directory <competition
directory>`.

If a file or directory name begins with ``~``, home directory expansion is
applied (see :func:`os.path.expanduser`).

  .. todo:: sort out best way to refer to Python functions.


Competition settings
^^^^^^^^^^^^^^^^^^^^

The following settings can be set at the top level of the control file:

.. setting:: competition_type

  String: ``"playoff"``, ``"mc_tuner"``, or ``"cem_tuner"``

  Determines whether the competition is a playoff or a specific kind of
  tuning event. This must be set on the first line in the control file
  (except for blank lines and comments).

.. setting:: description

  String (default None)

  A text description of the competition. This will be included in the
  :ref:`competition report file <competition report file>`.

.. setting:: record_games

  Bool (default True)

  Controls whether the ringmaster writes |sgf| :ref:`game records <game
  records>`.

.. setting:: stderr_to_log

  Bool (default True)

  Controls whether players' standard error streams are redirected to the
  :ref:`event log <logging>`. See :ref:`standard error`.

.. setting:: players

  Dictionary mapping identifiers to :setting:`Player` definitions (see
  :ref:`player configuration`).

  This describes the |gtp| engines that can be used in the competition.

  The dictionary keys are the :dfn:`player codes`; they are used to identify
  the players in :setting:`Matchup` definitions, and also appear in reports
  and the |sgf| game records.

  It's fine to have player definitions here which aren't used in any
  matchups. These definitions will be ignored, and no corresponding engines
  will be run.

.. setting:: matchups

  List of :setting:`Matchup` definitions (see :ref:`matchup
  configuration`).

  This defines which engines will play against each other, and the game
  settings they will use.

In addition to these, all matchup settings can be set at the top of the
control file. These settings will be used for any matchups which don't
explicitly override them.

.. todo:: (except id? player1 player2? Is 'matchup settings' defined? can we
   have a link?)

.. todo:: explicitly say 'the required settings are...'?


.. _player configuration:

Player configuration
^^^^^^^^^^^^^^^^^^^^

A Player definition has the same syntax a Python function call:
``Player([parameters])``. Apart from :setting:`!command`, the parameters
should be specified as keyword arguments (see :ref:`sample control file`). The
parameters are:


.. setting:: command

  String or list of strings

  This is the only required Player parameter. It can be specified either as
  the first parameter, or using a keyword ``command="..."``. It specifies the
  executable which will provide the player, and its command line arguments.

  The :setting:`!command` can be either a string or a list of strings. If it
  is a string, it is split using rules similar to a Unix shell's (see
  :func:`shlex.split`). (But note that the player subprocess is always executed
  directly, not run via a shell.)

  In either case, the first element is taken as the executable name and the
  remainder as its arguments.

  If the executable name does not contain a ``/``, it is searched for on the
  the :envvar:`PATH`. Otherwise it is handled as described in :ref:`file and
  directory names <file and directory names>`.

  Example::

    Player("~/src/fuego-svn/fuegomain/fuego --quiet")


.. setting:: cwd

   String (default None)

   The working directory for the player.

   If this is left unset, the player's working directory will be the current
   working directory when the ringmaster was launched (which may not be the
   competition directory). Use ``cwd="."`` to specify the competition
   directory.

   .. tip::
     If an engine writes debugging information to its working directory, use
     :setting:`cwd` to get it out of the way::

       Player('mogo', cwd='~/tmp')


.. setting:: environ

   Dictionary mapping strings to strings (default None)

   This specifies environment variables to be set in the player process, in
   addition to those inherited from the parent.

   Note that there is no special handling in this case for values which happen
   to be file or directory names.

   Example::

     Player('goplayer', environ={'GOPLAYER-DEBUG' : 'true'})


.. setting:: discard_stderr

  Bool (default False)

  Controls whether the player's standard error stream is redirected to
  :file:`/dev/null`. See :ref:`standard error`.

  Example::

    Player('mogo', discard_stderr=True)


.. setting:: gtp_aliases

  Dictionary mapping strings to strings (default None)

  This is a map of |gtp| command names to command names, eg::

    Player('fuego', gtp_aliases={'gomill-cpu_time' : 'cputime'})

  When the ringmaster would normally send :gtp:`gomill-cpu_time`, it will send
  :gtp:`cputime` instead.

  The command names are case-sensitive.


.. setting:: startup_gtp_commands
.. setting:: is_reliable_scorer
.. setting:: allow_claim

.. todo:: example of a function


.. _matchup configuration:

Matchup configuration
^^^^^^^^^^^^^^^^^^^^^

.. setting:: id?
.. setting:: boardsize
.. setting:: komi
.. setting:: alternating
.. setting:: handicap
.. setting:: handicap_style
.. setting:: move_limit
.. setting:: scorer
.. setting:: number_of_games

.. setting:: xxnumber_of_games

  number of games to be played in the matchup. If you omit this setting or set
  it to :const:`None`, there will be no limit.

