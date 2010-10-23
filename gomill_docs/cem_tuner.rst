The cross-entropy tuner
=======================

The cross-entropy tuner uses the :dfn:`cross-entropy method` described in
[CE]_.

.. caution:: The cross-entropy tuner is experimental. It can take a very large
   number of games to converge.


.. contents:: Page contents
   :local:
   :backlinks: none


The tuning algorithm
^^^^^^^^^^^^^^^^^^^^

The algorithm is not described in detail in this documentation. See [CE]_
section 3 for the description. The tuner always uses a Gaussian distribution.
The improvement suggested in section 5 is not implemented.


The parameter model
^^^^^^^^^^^^^^^^^^^

The parameter values taken from the Gaussian distribution are floating-point
numbers known as :dfn:`optimiser parameters`.

These parameters can be transformed before being used to construct the
candidate (see 3.3 'Normalising Parameters in [CE]_). The transformed values
are known as :dfn:`engine parameters`. The transformation is implemented using
a Python :ce-setting:`transform` function defined in the control file.

Reports show engine parameters (see the :ce-setting:`format` parameter
setting), together with the mean and variance of the corresponding optimiser
parameter distribution in the form :samp:`{mean}~{variance}`.


.. _the cem tuning algorithm:

.. _sample_cem_control_file:

Sample control file
^^^^^^^^^^^^^^^^^^^

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

  batch_size = 10
  samples_per_generation = 100
  number_of_generations = 5
  elite_proportion = 0.1
  step_size = 0.8




.. todo::

  Changing settings in the middle of a run::

     batch_size -- safe to increase
     samples_per_generation -- not safe
     number_of_generations -- safe
     elite_proportion -- safe
     step_size -- safe

     format_parameters -- safe
     convert_optimiser_parameters_to_engine_parameters -- not safe
     make_candidate -- not safe
                       (but ok if you're changing non-play-affecting options)



.. [CE]
   G.M.J-B. Chaslot, M.H.M Winands, I. Szita, and H.J. van den Herik.
   Cross-entropy for Monte-Carlo Tree Search. ICGA Journal, 31(3):145-156.
   http://www.personeel.unimaas.nl/g-chaslot/papers/crossmcICGA.pdf


Reporting
^^^^^^^^^

Currently, there aren't any sophisticated reports.

The standard report shows the parameters of the current Gaussian distribution,
and the number of wins for each candidate in the current generation.

After each generation, the details of the candidates are written to the
:ref:`history file <logging>`. The candidates selected as elite are marked
with a ``*``.

