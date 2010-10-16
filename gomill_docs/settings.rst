.. _control file:

The control file
----------------

.. contents:: Page contents
   :local:
   :backlinks: none


.. _sample control file:

Sample control file
^^^^^^^^^^^^^^^^^^^

Here is a sample control file, illustrating most of the available settings for
a playoff::

  competition_type = 'playoff'

  description = """
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


File format
^^^^^^^^^^^

The control file is a plain text configuration file.

It is interpreted in the same way as a Python source file. See the
:ref:`sample control file` above for an example of the syntax. See
:ref:`FIXME` for a formal specification.

The control file is made up of a series of top-level :dfn:`settings`, in the
form of Python assignment statements: :samp:`{setting_name} = {value}`.

Each top-level setting should begin on a new line, in the leftmost column of
the file. Settings which use brackets of any kind can be split over multiple
lines between elements (for example, lists can be split at the commas).

Comments are introduced by the ``#`` character, and continue until the end of
the line.

The settings for use in playoffs are listed below. Note that
:setting:`competition_type` must come first.

.. caution:: while the ringmaster will give error messages for unacceptable
   setting values, it will ignore attempts to set a nonexistent setting (this
   is because you're allowed to define variables of your own in the control
   file and use them in later setting definitions).

If you wish, you can use arbitrary Python expressions in the control file; see
:ref:`control file techniques` below.

.. caution:: all Python code in the control file will be executed; a hostile
   party with write access to a control file can cause the ringmaster to
   execute arbitrary code. On a shared system, do not make the competition
   directory or the control file world-writeable.


Data types
^^^^^^^^^^

The following data types are used for values of settings:

String
  A literal string of characters in single or double quotes, eg ``'gnugo-l1'``
  or ``"free"``.

  Strings containing non-ascii characters should be encoded as UTF-8 (Python
  unicode objects are also accepted).

  .. todo:: add ref to encoding section, once it's written.

  Strings can be broken over multiple lines by writing adjacent literals
  separated only by whitespace; see the Player definitions in the example
  above.

  Backslash escapes can be used in strings, such as ``\n`` for a newline.
  Alternatively, three (single or double) quotes can be used for a multi-line
  string; see ``description`` in the example above.

Identifier
  A (short) string made up of any combination of ASCII letters, numerals, and
  the punctuation characters ``- ! $ % & * + - . : ; < = > ? ^ _ ~``.

Boolean
  A truth value, written as ``True`` or ``False``.

Integer
  A whole number, written as a decimal literal, eg ``19`` or ``-1``.

Float
  A floating-point number, written as a decimal literal, eg ``6`` or ``6.0``
  or ``6.5``.

List
  A sequence of values of uniform type, written with square brackets separated
  by commas, eg ``["max_playouts 3000", "initial_wins 5"]``. An extra comma
  after the last item is harmless.

Dictionary
  An explicit map of keys of uniform type to values of uniform type, written
  with curly brackets, colons, and commas, eg ``{'p1' : True, 'p2' : False}``.
  An extra comma after the last item is harmless.


.. _file and directory names:

File and directory names
^^^^^^^^^^^^^^^^^^^^^^^^

When setting values are file or directory names, non-absolute names are
interpreted relative to the :ref:`competition directory <competition
directory>`.

If a file or directory name begins with ``~``, home directory expansion is
applied (see :func:`os.path.expanduser`).

  .. todo:: sort out best way to refer to Python stdlib functions.


Playoff settings
^^^^^^^^^^^^^^^^

The following settings can be set at the top level of the control file, for
competitions of type ``playoff``. See FIXME for tuning events.

The only required settings are :setting:`competition_type`,
:setting:`players`, and :setting:`matchups`.


.. setting:: competition_type

  String: ``"playoff"``, ``"mc_tuner"``, or ``"cem_tuner"``

  Determines whether the competition is a playoff or a specific kind of
  tuning event. This must be set on the first line in the control file
  (except for blank lines and comments).


.. setting:: description

  String (default ``None``)

  A text description of the competition. This will be included in the
  :ref:`competition report file <competition report file>`. Leading and
  trailing whitespace is ignored.


.. setting:: record_games

  Boolean (default ``True``)

  Write |sgf| :ref:`game records <game records>`.


.. setting:: stderr_to_log

  Boolean (default ``True``)

  Redirect all players' standard error streams to the :ref:`event log
  <logging>`. See :ref:`standard error`.


.. _player codes:

.. index:: player code

.. setting:: players

  Dictionary mapping identifiers to :setting:`Player` definitions (see
  :ref:`player configuration`).

  Describes the |gtp| engines that can be used in the competition. If you wish
  to use the same program with different settings, each combination of
  settings must be given its own :setting:`!Player` definition. See
  :ref:`control file techniques` below for a compact way to define several
  similar Players.

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

In addition to these, all Matchup settings (except :setting:`id` and
:setting:`name`) can be set at the top of the control file. These settings
will be used for any matchups which don't explicitly override them.


.. _player configuration:

Player configuration
^^^^^^^^^^^^^^^^^^^^

A Player definition has the same syntax as a Python function call:
:samp:`Player({parameters})`. Apart from :setting:`!command`, the parameters
should be specified as keyword arguments (see :ref:`sample control file`).

All parameters other than :setting:`!command` are optional.

The parameters are:


.. setting:: command

  String or list of strings

  This is the only required Player parameter. It can be specified either as
  the first parameter, or using a keyword :samp:`command="{...}"`. It
  specifies the executable which will provide the player, and its command line
  arguments.

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

  String (default ``None``)

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

  Dictionary mapping strings to strings (default ``None``)

  This specifies environment variables to be set in the player process, in
  addition to (or overriding) those inherited from the parent.

  Note that there is no special handling in this case for values which happen
  to be file or directory names.

  Example::

    Player('goplayer', environ={'GOPLAYER-DEBUG' : 'true'})


.. setting:: discard_stderr

  Boolean (default ``False``)

  Redirect the player's standard error stream to :file:`/dev/null`. See
  :ref:`standard error`.

  Example::

    Player('mogo', discard_stderr=True)


.. setting:: startup_gtp_commands

  List of strings, or list of sequences of strings (default ``None``)

  |gtp| commands to send at the beginning of each game. See :ref:`playing
  games`.

  Each command can be specified either as a single string or as a sequence of
  strings (with each argument in a single string). For example, the following
  are equivalent::

    Player('fuego', startup_gtp_commands=[
                        "uct_param_player ponder 0",
                        "uct_param_player max_games 5000"])

    Player('fuego', startup_gtp_commands=[
                        ("uct_param_player", "ponder", "0"),
                        ("uct_param_player", "max_games", "5000")])


.. setting:: gtp_aliases

  Dictionary mapping strings to strings (default ``None``)

  This is a map of |gtp| command names to command names, eg::

    Player('fuego', gtp_aliases={'gomill-cpu_time' : 'cputime'})

  When the ringmaster would normally send :gtp:`gomill-cpu_time`, it will send
  :gtp:`cputime` instead.

  The command names are case-sensitive. There is no mechanism for altering
  arguments.


.. setting:: is_reliable_scorer

  Boolean (default ``True``)

  If the :setting:`scorer` is ``players``, the ringmaster normally asks each
  player that implements the :gtp:`final_score` |gtp| command to report the
  game result. Setting :setting:`!is_reliable_scorer` to ``False`` for a
  player causes that player never to be asked.


.. setting:: allow_claim

  Boolean (default ``False``)

  Permits the player to claim a win (using the |gtp| extension
  :gtp:`gomill-genmove_ex claim`). See :ref:`claiming wins`.

  .. todo:: check link


.. _matchup configuration:

Matchup configuration
^^^^^^^^^^^^^^^^^^^^^

A Matchup definition has the same syntax as a Python function call:
:samp:`Matchup({parameters})`.

The first two parameters should be the :ref:`player codes <player codes>` for
the two players involved in the matchup. The remaining parameters should be
specified as keyword arguments. For example::

  Matchup('gnugo-l1', 'fuego-5k', board_size=13, komi=6)

Defaults for Matchup settings (other than :setting:`id` and :setting:`name`)
can be specified at the top level of the control file.

The :setting:`board_size` and :setting:`komi` parameters must be given for all
matchups (either explictly or as defaults); the rest are all optional.

.. caution:: a default :setting:`komi` or :setting:`alternating` setting will
   be applied even to handicap games.


The parameters are:


.. setting:: id

  Identifier

  A short string (usually one to three characters) which is used to identify
  the matchup. Matchup ids appear in the game ids (and so in the |sgf|
  filenames), and are used in the result-retrieval API.

  If this is left unspecified, the matchup id will be the index of the matchup
  in the :setting:`matchups` list (formatted as a decimal string, starting
  from ``"0"``).


  .. todo:: look at this para again once the things it talks about are or are
     not documented.


.. setting:: name

  String

  A string used to describe the matchup in reports. By default, this has the
  form :samp:`{player code} vs {player code}`; you may wish to change it if you
  have more than one matchup between the same pair of players (perhaps with
  different komi or handicap).


.. setting:: board_size

  Integer

  The size of Go board to use for the games (eg ``19`` for a 19x19 game). The
  ringmaster is willing to use board sizes from 2 to 25.


.. setting:: komi

  Float

  The :term:`komi` to use for the games. You can specify any floating-point
  value, and it will be passed on to the |gtp| engines unchanged, but
  normally only integer or half-integer values will be useful. Negative
  values are allowed.


.. setting:: alternating

  Boolean (default ``False``)

  If this is ``True``, the players will swap colours in successive games.
  Otherwise, the first-named player always takes Black.


.. setting:: handicap

  Integer (default ``None``)

  Number of handicap stones to give Black at the start of the game. See also
  :setting:`handicap_style`.

  See the :term:`GTP` specification for the rules about what handicap values
  are permitted for different board sizes (in particular, values less than 2
  are never allowed).


.. setting:: handicap_style

  String: ``"fixed"`` or ``"free"`` (default ``fixed``)

  Determines whether the handicap stones are placed on prespecified points, or
  chosen by the Black player. See the :term:`GTP` specification for more
  details.

  This is ignored if :setting:`handicap` is unset.


.. setting:: move_limit

  Integer (default ``1000``)

  Maximum number of moves to allow in a game. If this limit is reached, the
  game is stopped; see :ref:`playing games`.


.. setting:: scorer

  String: ``"players"`` or ``"internal"`` (default ``players``)

  Determines whether the game result is determined by the engines, or by the
  ringmaster. See :ref:`Scoring <scoring>` and :setting:`is_reliable_scorer`.


.. setting:: number_of_games

  Integer (default ``None``)

  The total number of games to play in the matchup. If you leave this unset,
  there will be no limit; see :ref:`stopping competitions`.

  Changing :setting:`!number_of_games` to ``0`` provides a way to effectively
  disable a matchup in future runs, without forgetting its results.


Changing the control file between runs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Changing the control file between runs of the same competition (or after the
final run) is allowed. For example, it's fine to increase a completed
matchup's :setting:`number_of_games` and set the competition off again.

The intention is that nothing surprising should happen if you change the
control file; of course if you change settings which affect player behaviour
then result summaries might not be meaningful.

In particular:

- if you change a player definition, the new definition will be used when
  describing the player in reports; there'll be no record of the earlier
  definition, or which games were played under it.

- if you change a matchup definition, the new definition will be used when
  describing the matchup in reports; there'll be no record of the earlier
  definition, or which games were played under it.

- if you change a matchup definition to have different players (ie, player
  codes), the ringmaster will refuse to run the competition.

- if you delete a matchup definition, results from that matchup won't be
  displayed during future runs, but will be included (with some missing
  information) in the :action:`report` and :action:`show` output.

If you add a matchup definition, put it at the end of the list (or else
explicitly specify the matchup ids).

In practice, you shouldn't delete matchup definitions (if you don't want any
more games to be played, set :setting:`number_of_games` to ``0``).

If you change descriptive text, you can use the :action:`report` command line
action to remake the report file.


.. _control file techniques:

Control file techniques
^^^^^^^^^^^^^^^^^^^^^^^

As the control file is just Python code, it's possible to use less direct
methods to specify the setting values.

One convenient way to define a number of similar players is to define a
function which returns a Player object. For example, the player definitions in
the sample control file could be rewritten as follows::

  def gnugo(level):
      return Player("gnugo --mode=gtp --chinese-rules --capture-all-dead "
                    "--level=%d" % level)

  def fuego(playouts_per_move, additional_commands=[]):
      commands = [
          "go_param timelimit 999999",
          "uct_max_memory 350000000",
          "uct_param_search number_threads 1",
          "uct_param_player reuse_subtree 0",
          "uct_param_player ponder 0",
          "uct_param_player max_games %d" % playouts_per_move,
          ]
      return Player("fuego --quiet",
                    startup_gtp_commands=commands+additional_commands)

  players = {
      'gnugo-l1' : gnugo(level=1),
      'gnugo-l2' : gnugo(level=2),
      'fuego-5k' : fuego(playouts_per_move=5000)
      }

If you assign to a setting more than once, the final value is the one that
counts. Settings specified above as having default ``None`` can be assigned
the value ``None``, which will be equivalent to leaving them unset.

Importing parts of the Python standard library (or other Python libraries that
you have installed) is allowed.

.. todo:: ref example in tuners docs, if there is one.


