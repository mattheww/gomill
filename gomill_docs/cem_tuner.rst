.. |ce| replace:: :ref:`[CE] <ce_paper>`

The cross-entropy tuner
^^^^^^^^^^^^^^^^^^^^^^^

:setting:`competition_type` string: ``"ce_tuner"``.

The cross-entropy tuner uses the :dfn:`cross-entropy method` described in
|ce|:

.. _ce_paper:

| [CE] G.M.J-B. Chaslot, M.H.M Winands, I. Szita, and H.J. van den Herik.
| Cross-entropy for Monte-Carlo Tree Search. ICGA Journal, 31(3):145-156.
| http://www.personeel.unimaas.nl/g-chaslot/papers/crossmcICGA.pdf

.. caution:: The cross-entropy tuner is experimental. It can take a very large
   number of games to converge.


.. contents:: Page contents
   :local:
   :backlinks: none


The tuning algorithm
""""""""""""""""""""

The algorithm is not described in detail in this documentation. See |ce|
section 3 for the description. The tuner always uses a Gaussian distribution.
The improvement suggested in section 5 is not implemented.


.. _ce parameter model:

The parameter model
"""""""""""""""""""

The parameter values taken from the Gaussian distribution are floating-point
numbers known as :dfn:`optimiser parameters`.

These parameters can be transformed before being used to configure the
candidate (see 3.3 *Normalising Parameters* in |ce|). The transformed values
are known as :dfn:`engine parameters`. The transformation is implemented using
a Python :ce-setting:`transform` function defined in the control file.

Reports show engine parameters (see the :ce-setting:`format` parameter
setting), together with the mean and variance of the corresponding optimiser
parameter distribution in the form :samp:`{mean}~{variance}`.


.. _the cem tuning algorithm:

.. _sample_cem_control_file:

Sample control file
"""""""""""""""""""

Here is a sample control file, illustrating most of the available settings for
a cross-entropy tuning event::

  competition_type = "ce_tuner"

  description = """\
  This is a sample control file.

  It illustrates the available settings for the cross entropy tuner.
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

  FUEGO_MAX_GAMES = 1000

  def exp_10(f):
      return 10.0**f

  parameters = [
      Parameter('rave_weight_initial',
                # Mean and variance are in terms of log_10 (rave_weight_initial)
                initial_mean = -1.0,
                initial_variance = 1.5,
                transform = exp_10,
                format = "I: %4.2f"),

      Parameter('rave_weight_final',
                # Mean and variance are in terms of log_10 (rave_weight_final)
                initial_mean = 3.5,
                initial_variance = 1.5,
                transform = exp_10,
                format = "F: %4.2f"),
      ]

  def make_candidate(rwi, rwf):
      return fuego(
          FUEGO_MAX_GAMES,
          ["uct_param_search rave_weight_initial %f" % rwi,
           "uct_param_search rave_weight_final %f" % rwf])

  board_size = 9
  komi = 7.5
  opponent = 'gnugo-l10'
  candidate_colour = 'w'

  number_of_generations = 5
  samples_per_generation = 100
  batch_size = 10
  elite_proportion = 0.1
  step_size = 0.8



.. _cem_control_file_settings:

Control file settings
"""""""""""""""""""""

The following settings can be set at the top level of the control file:

All :ref:`common settings <common settings>` (the :setting:`players`
dictionary is required, though it is used only to define the opponent).

The following game settings (only :setting:`!board_size` and :setting:`!komi`
are required):

- :setting:`board_size`
- :setting:`komi`
- :setting:`handicap`
- :setting:`handicap_style`
- :setting:`move_limit`
- :setting:`scorer`


The following additional settings (they are all required):

.. ce-setting:: candidate_colour

  String: ``"b"`` or ``"w"``

  The colour for the candidates to take in every game.


.. ce-setting:: opponent

  Identifier

  The :ref:`player code <player codes>` of the player to use as the
  candidates' opponent.


.. ce-setting:: parameters

  List of :ce-setting-cls:`Parameter` definitions (see :ref:`ce parameter
  configuration`).

  Describes the parameters that the tuner will work with. See :ref:`ce
  parameter model` for more details.

  The order of the :ce-setting-cls:`Parameter` definitions is used for the
  arguments to :ce-setting:`make_candidate`, and whenever parameters are
  described in reports or game records.


.. ce-setting:: make_candidate

  Python function

  Function to create a :setting-cls:`Player` from its engine parameters.

  This function is passed one argument for each candidate parameter, and must
  return a :setting-cls:`Player` definition. Each argument is the output of
  the corresponding Parameter's :ce-setting:`transform`.

  The function will typically use its arguments to construct command line
  options or |gtp| commands for the player. For example::

    def make_candidate(param1, param2):
        return Player(["goplayer", "--param1", str(param1),
                       "--param2", str(param2)])

    def make_candidate(param1, param2):
        return Player("goplayer", startup_gtp_commands=[
                       ["param1", str(param1)],
                       ["param2", str(param2)],
                      ])


.. ce-setting:: number_of_generations

  Positive integer

  The number of times to repeat the tuning algorithm (*number of iterations*
  or *T* in the terminology of |ce|).


.. ce-setting:: samples_per_generation

  Positive integer

  The number of candidates to make in each generation (*population_size* or
  *N* in the terminology of |ce|).


.. ce-setting:: batch_size

  Positive integer

  The number of games played by each candidate.


.. ce-setting:: elite_proportion

  Float between 0.0 and 1.0

  The proportion of candidates to select from each generation as 'elite' (the
  *selection ratio* or *ρ* in the terminology of |ce|). A value between 0.01
  and 0.1 is recommended.



.. ce-setting:: step_size

  Float between 0.0 and 1.0

  The rate at which to update the distribution parameters between generations
  (*α* in the terminology of |ce|).

  .. caution:: I can't find anywhere in the paper the value they used for
     this, so I don't know what to recommend.


.. _ce parameter configuration:

Parameter configuration
"""""""""""""""""""""""

.. ce-setting-cls:: Parameter

A :ce-setting-cls:`!Parameter` definition has the same syntax as a Python
function call: :samp:`Parameter({arguments})`. Apart from :ce-setting:`!code`,
the arguments should be specified using keyword form (see
:ref:`sample_cem_control_file`).

The :ce-setting:`code`, :ce-setting:`initial_mean`, and
:ce-setting:`initial_variance` arguments are required.

The arguments are:


.. ce-setting:: code

  Identifier

  A short string used to identify the parameter. This is used in error
  messages, and in the default for :ce-setting:`format`.


.. ce-setting:: initial_mean

  Float

  The mean value for the parameter in the first generation's distribution.


.. ce-setting:: initial_variance

  Float >= 0

  The variance for the parameter in the first generation's distribution.


.. ce-setting:: transform

  Python function (default identity)

  Function mapping an optimiser parameter to an engine parameter; see :ref:`ce
  parameter model`.

  Examples::

    def exp_10(f):
        return 10.0**f

    Parameter('p1', initial_mean = …, initial_variance = …,
              transform = exp_10)

  If the :ce-setting:`!transform` is not specified, the optimiser parameter is
  used directly as the engine parameter.


.. ce-setting:: format

  String (default :samp:`"{parameter_code}: %s"`)

  Format string used to display the parameter value. This should include a
  short abbreviation to indicate which parameter is being displayed, and also
  contain ``%s``, which will be replaced with the engine parameter value.

  You can use any Python conversion specifier instead of ``%s``. For example,
  ``%.2f`` will format a floating point number to two decimal places. ``%s``
  should be safe to use for all types of value. See `string formatting
  operations`__ for details.

  .. __: http://docs.python.org/release/2.7/library/stdtypes.html#string-formatting-operations

  Format strings should be kept short, as screen space is limited.

  Examples::

    Parameter('parameter_1',
              initial_mean = 0.0, initial_variance = 1.0,
              format = "p1: %.2f")

    Parameter('parameter_2',
              initial_mean = 5000, initial_variance = 250000,
              format = "p2: %d")


Reporting
"""""""""

Currently, there aren't any sophisticated reports.

The standard report shows the parameters of the current Gaussian distribution,
and the number of wins for each candidate in the current generation.

After each generation, the details of the candidates are written to the
:ref:`history file <logging>`. The candidates selected as elite are marked
with a ``*``.


Changing the control file between runs
""""""""""""""""""""""""""""""""""""""

Some settings can safely be changed between runs of the same cross-entropy
tuning event:

:ce-setting:`batch_size`
  safe to increase

:ce-setting:`samples_per_generation`
  not safe to change

:ce-setting:`number_of_generations`
  safe to change

:ce-setting:`elite_proportion`
  safe to change

:ce-setting:`step_size`
  safe to change

:ce-setting:`make_candidate`
  safe to change, but don't alter play-affecting options

:ce-setting:`transform`
  not safe to change

:ce-setting:`format`
  safe to change

