.. _control file:

The control file
----------------

.. contents:: Page contents
   :local:
   :backlinks: none


.. _sample control file:

Sample control file
^^^^^^^^^^^^^^^^^^^

Here is a sample control file for a playoff tournament::

  competition_type = 'playoff'

  description = """
  This is a sample control file.

  It illustrates player definitions, common settings, and game settings.
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
              handicap=2, handicap_style='free', komi=0,
              scorer='players', number_of_games=5),

      Matchup('gnugo-l2', 'fuego-5k', alternating=True,
              scorer='players', move_limit=200),

      Matchup('gnugo-l1', 'gnugo-l2',
              komi=0.5,
              scorer='internal'),
      ]


File format
^^^^^^^^^^^

The control file is a plain text configuration file.

It is interpreted in the same way as a Python source file. See the
:ref:`sample control file` above for an example of the syntax.

  .. __: http://docs.python.org/release/2.7/reference/index.html

The control file is made up of a series of top-level :dfn:`settings`, in the
form of assignment statements: :samp:`{setting_name} = {value}`.

Each top-level setting should begin on a new line, in the leftmost column of
the file. Settings which use brackets of any kind can be split over multiple
lines between elements (for example, lists can be split at the commas).

Comments are introduced by the ``#`` character, and continue until the end of
the line.

In general, the order of settings in the control file isn't significant
(except for list members). But note that :setting:`competition_type` must come
first.

See :ref:`data types` below for the representation of values. See the `Python
language reference`__ for a formal specification.

The settings which are common to all competition types are listed below.
Further settings are given on the page documenting each competition type.

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

The recommended filename extension for the control file is :file:`.ctl`.

.. _data types:

Data types
^^^^^^^^^^

The following data types are used for values of settings:

String
  A literal string of characters in single or double quotes, eg ``'gnugo-l1'``
  or ``"free"``.

  Strings containing non-ASCII characters should be encoded as UTF-8 (Python
  unicode objects are also accepted).

  Strings can be broken over multiple lines by writing adjacent literals
  separated only by whitespace; see the :setting-cls:`Player` definitions in
  the example above.

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

When values in the control file are file or directory names, non-absolute
names are interpreted relative to the :ref:`competition directory <competition
directory>`.

If a file or directory name begins with ``~``, home directory expansion is
applied (see :func:`os.path.expanduser`).


.. _common settings:

Common settings
^^^^^^^^^^^^^^^

The following settings can appear at the top level of the control file for all
competition types.

.. setting:: competition_type

  String: ``"playoff"``, ``"allplayall"``, ``"mc_tuner"``, or ``"ce_tuner"``

  Determines the type of tournament or tuning event. This must be set on the
  first line in the control file (not counting blank lines and comments).


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

  Dictionary mapping identifiers to :setting-cls:`Player` definitions (see
  :ref:`player configuration`).

  Describes the |gtp| engines that can be used in the competition. If you wish
  to use the same program with different settings, each combination of
  settings must be given its own :setting-cls:`Player` definition. See
  :ref:`control file techniques` below for a compact way to define several
  similar Players.

  The dictionary keys are the :dfn:`player codes`; they are used to identify
  the players in reports and the |sgf| game records, and elsewhere in the
  control file to specify how players take part in the competition.

  See the pages for specific competition types for the way in which players
  are selected from the :setting:`!players` dictionary.

  It's fine to have player definitions here which aren't used in the
  competition. These definitions will be ignored, and no corresponding engines
  will be run.



.. _player configuration:

Player configuration
^^^^^^^^^^^^^^^^^^^^

.. setting-cls:: Player

A :setting-cls:`!Player` definition has the same syntax as a Python function
call: :samp:`Player({arguments})`. Apart from :setting:`command`, the
arguments should be specified using keyword form (see the examples for
particular arguments below).

All arguments other than :setting:`command` are optional.

.. tip:: For results to be meaningful, you should normally configure players
   to use a fixed amount of computing power, paying no attention to the amount
   of real time that passes, and make sure :term:`pondering` is not turned on.

The arguments are:


.. setting:: command

  String or list of strings

  This is the only required :setting-cls:`Player` argument. It can be
  specified either as the first argument, or using a keyword
  :samp:`command="{...}"`. It specifies the executable which will provide the
  player, and its command line arguments.

  The player subprocess is executed directly, not run via a shell.

  The :setting:`!command` can be either a string or a list of strings. If it
  is a string, it is split using rules similar to a Unix shell's (see
  :func:`shlex.split`).

  In either case, the first element is taken as the executable name and the
  remainder as its arguments.

  If the executable name does not contain a ``/``, it is searched for on the
  the :envvar:`!PATH`. Otherwise it is handled as described in :ref:`file and
  directory names <file and directory names>`.

  Example::

    Player("~/src/fuego-svn/fuegomain/fuego --quiet")


.. setting:: cwd

  String (default ``None``)

  The working directory for the player.

  If this is left unset, the player's working directory will be the working
  directory from when the ringmaster was launched (which may not be the
  competition directory). Use ``cwd="."`` to specify the competition
  directory.

  .. tip::

    If an engine writes debugging information to its working directory, use
    :setting:`cwd` to get it out of the way::

      Player('mogo', cwd='~/tmp')


.. setting:: environ

  Dictionary mapping strings to strings (default ``None``)

  This specifies environment variables to be set in the player process, in
  addition to (or overriding) those inherited from its parent.

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

  List of strings, or list of lists of strings (default ``None``)

  |gtp| commands to send at the beginning of each game. See :ref:`playing
  games`.

  Each command can be specified either as a single string or as a list of
  strings (with each |gtp| argument in a single string). For example, the
  following are equivalent::

    Player('fuego', startup_gtp_commands=[
                        "uct_param_player ponder 0",
                        "uct_param_player max_games 5000"])

    Player('fuego', startup_gtp_commands=[
                        ["uct_param_player", "ponder", "0"],
                        ["uct_param_player", "max_games", "5000"]])


.. setting:: gtp_aliases

  Dictionary mapping strings to strings (default ``None``)

  This is a map of |gtp| command names to command names, eg::

    Player('fuego', gtp_aliases={'gomill-cpu_time' : 'cputime'})

  When the ringmaster would normally send :gtp:`gomill-cpu_time`, it will send
  :gtp:`!cputime` instead.

  The command names are case-sensitive. There is no mechanism for altering
  arguments.


.. setting:: is_reliable_scorer

  Boolean (default ``True``)

  If the :setting:`scorer` setting is ``players``, the ringmaster normally
  asks each player that implements the :gtp:`!final_score` |gtp| command to
  report the game result. Setting :setting:`!is_reliable_scorer` to ``False``
  for a player causes that player never to be asked.


.. setting:: allow_claim

  Boolean (default ``False``)

  Permits the player to claim a win (using the |gtp| extension
  :gtp:`gomill-genmove_ex`). See :ref:`claiming wins`.


.. _game settings:

Game settings
^^^^^^^^^^^^^

The following settings describe how a particular game is to be played.

They are not all used in every competition type, and may be specified in some
other way than a top level control file setting; see the page documenting a
particular competition type for details.


.. setting:: board_size

  Integer

  The size of Go board to use for the game (eg ``19`` for a 19x19 game). The
  ringmaster is willing to use board sizes from 2 to 25.


.. setting:: komi

  Float

  The :term:`komi` to use for the game. You can specify any floating-point
  value, and it will be passed on to the |gtp| engines unchanged, but normally
  only integer or half-integer values will be useful. Negative values are
  allowed.


.. setting:: handicap

  Integer (default ``None``)

  The number of handicap stones to give Black at the start of the game. See
  also :setting:`handicap_style`.

  See the `GTP specification`_ for the rules about what handicap values
  are permitted for different board sizes (in particular, values less than 2
  are never allowed).


.. setting:: handicap_style

  String: ``"fixed"`` or ``"free"`` (default ``"fixed"``)

  Determines whether the handicap stones are placed on prespecified points, or
  chosen by the Black player. See the `GTP specification`_ for more details.

  This is ignored if :setting:`handicap` is unset.

  .. _GTP specification: http://www.lysator.liu.se/~gunnar/gtp/gtp2-spec-draft2/gtp2-spec.html#SECTION00051000000000000000



.. setting:: move_limit

  Integer (default ``1000``)

  The maximum number of moves to allow in a game. If this limit is reached,
  the game is stopped; see :ref:`playing games`.


.. setting:: scorer

  String: ``"players"`` or ``"internal"`` (default ``"players"``)

  Determines whether the game result is determined by the engines, or by the
  ringmaster. See :ref:`Scoring <scoring>` and :setting:`is_reliable_scorer`.


.. setting:: internal_scorer_handicap_compensation

  String: ``"no"``, ``"full"`` or ``"short"`` (default ``"full"``)

  Specifies whether White is given extra points to compensate for Black's
  handicap stones; see :ref:`Scoring <scoring>` for details. This setting has
  no effect for games which are played without handicap, and it has no effect
  when :setting:`scorer` is set to ``"players"``.





Changing the control file between runs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Changing the control file between runs of the same competition (or after the
final run) is allowed. For example, in a playoff tournament it's fine to
increase a completed matchup's :pl-setting:`number_of_games` and set the
competition off again.

The intention is that nothing surprising should happen if you change the
control file; of course if you change settings which affect player behaviour
then result summaries might not be meaningful.

In particular, if you change a :setting-cls:`Player` definition, the new
definition will be used when describing the player in reports; there'll be no
record of the earlier definition, or which games were played under it.

If you change descriptive text, you can use the :action:`report` command line
action to remake the report file.

The page documenting each competition type has more detail on what it is safe
to change.


.. _control file techniques:

Control file techniques
^^^^^^^^^^^^^^^^^^^^^^^

As the control file is just Python code, it's possible to use less direct
methods to specify the values of settings.

One convenient way to define a number of similar players is to define a
function which returns a :setting-cls:`Player` object. For example, the player
definitions in the sample control file could be rewritten as follows::

  def gnugo(level):
      return Player("gnugo --mode=gtp --chinese-rules "
                    "--capture-all-dead --level=%d" % level)

  def fuego(playouts_per_move, additional_commands=[]):
      commands = [
          "go_param timelimit 999999",
          "uct_max_memory 350000000",
          "uct_param_search number_threads 1",
          "uct_param_player reuse_subtree 0",
          "uct_param_player ponder 0",
          "uct_param_player max_games %d" % playouts_per_move,
          ]
      return Player(
          "fuego --quiet",
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

