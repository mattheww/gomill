.. index:: monte carlo tuner

The Monte Carlo tuner
=====================

The Monte Carlo tuner treats the tuning event as a :term:`bandit problem`.
That is, it attempts to find the candidate which has the highest probability
of beating the opponent, and arranges to 'spend' more games on the candidates
which have the highest winning percentages so far.

It does this using the :term:`UCB` algorithm (or, optionally, :term:`UCT`)
which is familiar to Go programmers.

.. caution:: As of Gomill |version|, the Monte Carlo tuner is still
   experimental. The control file settings may change in future. The reports
   aren't very good.

.. contents:: Page contents
   :local:
   :backlinks: none


The parameter model
^^^^^^^^^^^^^^^^^^^

The Monte Carlo tuner expects to work with one or more independent parameters.

Internally, it models each parameter value as a floating point number in the
range 0.0 to 1.0. It makes candidates with parameter values taken uniformly
from this scale. Values from this range are known as :dfn:`optimiser
parameters`. A number of :ref:`predefined scales <predefined scales>` are
provided.

In practice, engine parameters might not be floating point numbers, their
range is unlikely to be 0.0 to 1.0, and you may wish to use a non-uniform (eg,
logarithmic) scale for the candidates.

To support this, each parameter has an associated :setting:`scale`. This is a
function which maps an optimiser parameter to an :dfn:`engine parameter`
(which can be of an arbitrary Python type).

Each candidate's engine parameters are passed to the :setting:`make_candidate`
function, which returns a Player definition.

Reports, and the live display, are also based on engine parameters; see the
:setting:`format` parameter setting.

.. caution:: While the Monte Carlo tuner does not impose any limit on the
   number of parameters you use, unless the games are unusually rapid it may
   be optimistic to try to tune more than two parameters at once.


The tuning algorithm
^^^^^^^^^^^^^^^^^^^^

.. todo:: give an overview of the algorithm. Need to find a
   reference so as to use its terminology. Explain about 'split'.

.. todo:: say how the 'best parameter vector' is determined.


Reporting
^^^^^^^^^

.. todo:: say no sophisticated reports are available yet



.. _sample_mcts_control_file:

Sample control file
^^^^^^^^^^^^^^^^^^^

Here is a sample control file, illustrating most of the available settings for
a Monte Carlo tuning event::

  competition_type = "mc_tuner"

  description = """\
  This is a sample control file.

  It illustrates the available settings for the Monte Carlo tuner.
  """

  players = {
      'gnugo-l10' : Player("gnugo --mode=gtp --chinese-rules "
                           "--capture-all-dead --level=10"),
      }

  def fuego(max_games, additional_commands=[]):
      commands = [
          "go_param timelimit 999999",
          "uct_max_memory 350000000",
          "uct_param_search number_threads 1",
          "uct_param_player reuse_subtree 0",
          "uct_param_player ponder 0",
          "uct_param_player max_games %d" % max_games,
          ]
      return Player(
          "fuego --quiet",
          startup_gtp_commands=commands+additional_commands)

  FUEGO_MAX_GAMES = 5000

  parameters = [
      Parameter('rave_weight_initial',
                scale = LOG(0.01, 5.0),
                split = 8,
                format = "I: %4.2f"),

      Parameter('rave_weight_final',
                scale = LOG(1e2, 1e5),
                split = 8,
                format = "F: %4.2f"),
      ]

  def make_candidate(rwi, rwf):
      return fuego(
          FUEGO_MAX_GAMES,
          ["uct_param_search rave_weight_initial %f" % rwi,
           "uct_param_search rave_weight_final %f" % rwf])

  board_size = 19
  komi = 7.5
  opponent = 'gnugo-l10'
  candidate_colour = 'w'
  number_of_games = 10000

  exploration_coefficient = 0.2
  initial_visits = 10
  initial_wins = 5

  summary_spec = [40]
  log_tree_to_history_period = 200



Control file settings
^^^^^^^^^^^^^^^^^^^^^

The control file settings are similar to those used in playoffs.

The :setting:`competition_type` setting must have the value ``"mc_tuner"``.

The :setting:`players` dictionary must be present as usual, but it is used
only to define the opponent.

The :setting:`matchups` setting is not used. The following matchup settings
may be specified as top-level settings (as usual, :setting:`board_size` and
:setting:`komi` are compulsory):

- :setting:`board_size`
- :setting:`komi`
- :setting:`handicap`
- :setting:`handicap_style`
- :setting:`move_limit`
- :setting:`scorer`
- :setting:`number_of_games`

All other competition settings may be present, with the same meaning as for
playoffs.


The following additional settings are used (all those without a listed default
are compulsory):

.. setting:: parameters

  List of :setting:`Parameter` definitions (see :ref:`parameter
  configuration`).

  Describes the parameter space that the tuner will work in. See :ref:`The
  parameter model` for more details.

  The order of the parameter definitions is used for the arguments to
  :setting:`make_candidate`, and whenever parameters are described in reports
  or game records.


.. setting:: make_candidate

  Python function

  Function to create a Player from its engine parameters.

  This function is passed one argument for each candidate Parameter, and must
  return a Player definition. Each argument is the output of the corresponding
  Parameter's :setting:`scale`.

  The function will typically use its arguments to construct command line
  options or |gtp| commands for the Player. For example::

    def make_candidate(param1, param2):
        return Player(["goplayer", "--param1", str(param1),
                       "--param2", str(param2)])

    def make_candidate(param1, param2):
        return Player("goplayer", startup_gtp_commands=[
                       ["param1", str(param1)],
                       ["param2", str(param2)],
                      ])


.. setting:: candidate_colour

  String: ``"b"`` or ``"w"``

  The colour for the candidates to take in every game.


.. setting:: opponent

  Identifier

  The :ref:`player code <player codes>` of the player to use as the
  candidates' opponent.


.. setting:: exploration_coefficient

  Float

  The coefficient of the exploration term in the :ref:`UCB` algorithm (eg
  ``0.25``).

  .. todo:: proper description in terminology of whatever reference we use?
     Suggested range?


.. setting:: initial_visits

  Positive integer

  The number of visits to initialise each candidate with. At the start of the
  event, the tuner will behave as if each candidate has already played this
  many games.


.. setting:: initial_wins

  Positive integer

  The number of wins to initialise each candidate with. At the start of the
  event, the tuner will behave as if each candidate has already won this many
  games.

  .. tip:: It's best to set :setting:`initial_wins` so that
     :setting:`initial_wins` / :setting:`initial_visits` is close to the
     typical candidate's expected win rate.


.. setting:: max_depth

  Positive integer

  See :ref:`tree search` below.


The remaining settings only affect reporting and logging; they have no effect
on the tuning algorithm.

.. setting:: summary_spec

  List of integers (default [30])

  Number of candidates to describe in the runtime display and reports (the
  candidates with most visits are described).

  (This list should have :setting:`max_depth` elements; if
  :setting:`max_depth` is greater than 1, it specifies how many candidates to
  show from each level of the tree, starting with the highest.)


.. setting:: log_tree_to_history_period

  Positive integer (default None)

  If this is set, a detailed description of the :ref:`UCT` tree is written to
  the history file periodically (after every
  :setting:`!log_tree_to_history_period` games).


.. setting:: number_of_running_simulations_to_show

  Positive integer (default 12)

  The maximum number of games in progress to describe on the runtime display.


.. _parameter configuration:

Parameter configuration
^^^^^^^^^^^^^^^^^^^^^^^

A Parameter definition has the same syntax as a Python function call:
:samp:`Parameter({arguments})`. Apart from :setting:`!code`, the arguments
should be specified using keyword form (see :ref:`sample_mcts_control_file`).

All parameters other than :setting:`format` are required.

The parameters are:


.. setting:: code

  Identifier

  A short string used to identify the parameter. This is used in error
  messages, and in the default for :setting:`format`.


.. setting:: scale

  Python function

  Function mapping an optimiser parameter to an :dfn:`engine parameter`; see
  :ref:`The parameter model`.

  Although this can be defined explicitly, in most cases you should be able
  to use one of the :ref:`predefined scales <predefined scales>`.

  Examples::

    Parameter('p1', split = 8,
              scale = LINEAR(-1.0, 1.0))

    Parameter('p2', split = 8,
              scale = LOG(10, 10000, integer=True))

    Parameter('p3', split = 3,
              scale = EXPLICIT(['low', 'medium', 'high']))

    def scale_p3(f):
        return int(1000 * math.sqrt(f))
    Parameter('p3', split = 20, scale = scale_p3)



.. setting:: split

  Positive integer

  The number of samples from this parameter to use to make candidates.

  .. todo:: write properly after 'the tuning algorithm' is in


.. setting:: format

  String (default :samp:`"{parameter_code}: %s"`)

  Format string used to display the parameter value. This should include a
  short abbreviation to indicate which parameter is being displayed, and also
  contain ``%s``, which will be replaced with the engine parameter value.

  You can use any Python conversion specifier instead of ``%s``. For example,
  ``%.2f`` will format a floating point number to two decimal places. ``%s``
  should be safe to use for all types of value. See FIXME for details.

  Format strings should be kept short, as screen space is limited.

  Examples::

    Parameter('parameter_1', split = 8,
              scale = LINEAR(-1.0, 1.0),
              format = "p1: %.2f")

    Parameter('parameter_2', split = 8,
              scale = LOG(10, 10000, integer=True),
              format = "p2: %d")

    Parameter('parameter_3', split = 3,
              scale = EXPLICIT(['low', 'medium', 'high']),
              format = "p3: %s")


.. index:: predefined scale
.. index:: scale; predefined

.. _predefined scales:

Predefined scales
^^^^^^^^^^^^^^^^^

There are three kinds of predefined scale which you can use in a
:setting:`scale` definition:

.. index:: LINEAR

.. object:: LINEAR

  A linear scale between specified bounds. This takes two arguments:
  ``lower_bound`` and ``upper_bound``.

  Optionally, you can also pass ``integer=True``, in which case the result is
  rounded to the nearest integer.

  Examples::

    LINEAR(0, 100)
    LINEAR(-64.0, 256.0, integer=True)

  .. tip:: To make candidates which take each value from a simple integer range
     from (say) 0 to 10 inclusive, use::

       Parameter('p1', split = 11,
                 scale = LINEAR(-0.5, 10.5, integer=True))

     (or use EXPLICIT)


.. index:: LOG

.. object:: LOG

  A 'logarithmic scale' (ie, an exponential function) between specified
  bounds. This takes two arguments: ``lower_bound`` and ``upper_bound``.

  Optionally, you can also pass ``integer=True``, in which case the result is
  rounded to the nearest integer.

  Example::

    LOG(0.01, 1000)


.. index:: EXPLICIT

.. object:: EXPLICIT

  This scale makes the engine parameters take values from an explicitly
  specified list. You should normally use this with :setting:`split` equal to
  the length of the list.

  Examples::

    EXPLICIT([0, 1, 2, 4, 6, 8, 10, 15, 20])
    EXPLICIT(['low', 'medium', 'high'])


  .. note:: if :setting:`max_depth` is greater than 1,
     :setting:`split` ^ :setting:`max_depth` should equal the length of the
     list.


.. _tree search:

Tree search
^^^^^^^^^^^

As a further (and even more experimental) refinement, it's possible to arrange
the candidates in the form of a tree and use the :term:`UCT` algorithm instead
of plain :term:`UCB`.

To do this, set the :setting:`max_depth` setting to a value greater than 1. At
each generation of the tree, the parameter space will be subdivided FIXME.

.. todo:: finish this. Say each parameter is treated the same, and each is
   split in each generation. Say the split is the same at each dimension. Say
   it expands the tree on the second visit. Say it doesn't currently use
   virtual losses, which isn't ideal if --parallel is high.

.. note:: It isn't clear that using UCT for a continuous parameter space like
   this is a wise (or valid) thing to do. I suspect it needs some form of RAVE
   to perform well.


Changing the control file between runs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In general, you shouldn't change the Parameter definitions or the settings
which control the tuning algorithm between runs. The ringmaster will normally
notice and refuse to start, but it's possible to fool it and so get
meaningless results.

Changing the :setting:`exploration_coefficient` is ok. Increasing
:setting:`max_depth` is ok (decreasing it is ok too, but it won't stop the
tuner exploring parts of the tree that it has already expanded).

Changing :setting:`make_candidate` is ok, though if this affects player
behaviour it will probably be unhelpful.

Changing :setting:`initial_wins` or :setting:`initial_visits` will have no
effect if :setting:`max_depth` is 1; otherwise it will affect only
newly-created tree nodes.

Changing the settings which control reporting, including :setting:`format`, is
ok.

