The cross-entropy method tuner
==============================

Here's a sample of the control file settings for the CEM tuner::

  batch_size = 100
  samples_per_generation = 20
  number_of_generations = 5
  elite_proportion = 0.1
  step_size = 0.5

  # The dimensions are
  #  - resign_at
  #  - log_10 (playouts_per_move)

  initial_distribution = [
      # mean, variance in optimiser coordinates
      (0.5, 1.0),
      (2.0, 2.0),
      ]

  def convert_optimiser_parameters_to_engine_parameters(optimiser_parameters):
      opt_resign_at, opt_playouts_per_move = optimiser_parameters
      resign_at = max(0.0, min(1.0, opt_resign_at))
      playouts_per_move = int(10**opt_playouts_per_move)
      playouts_per_move = max(10, min(3000, playouts_per_move))
      return [resign_at, playouts_per_move]

  def format_parameters(optimiser_parameters):
      """Pretty-print an optimiser parameter vector.

      Returns a string.

      """
      resign_at, opt_playouts_per_move = optimiser_parameters
      clipped_resign_at = max(0.0, min(1.0, resign_at))
      if resign_at == clipped_resign_at:
          resign_at_s = "%.2f       " % resign_at
      else:
          resign_at_s = "%.2f(% .2f)" % (clipped_resign_at, resign_at)
      ppm = int(10**opt_playouts_per_move)
      clipped_ppm = max(10, min(3000, ppm))
      if ppm == clipped_ppm:
          ppm_s = "%4s       " % ppm
      else:
          ppm_s = "%4s(%5s)" % (clipped_ppm, ppm)
      return "%s %s" % (resign_at_s, ppm_s)

  def make_candidate(parameters):
      # This demonstrates setting parameters on the command line and with GTP
      # commands.
      resign_at, playouts_per_move = parameters
      opts = ["--ppm=%d" % playouts_per_move]
      commands = ["kiai-settings resign_at %f" % resign_at]
      return Player(kiai + " ".join(opts), startup_gtp_commands=commands)

  matchups = [
      ('k50', CANDIDATE),
      (CANDIDATE, 'k50'),
      #('gnugo-l1', CANDIDATE),
      #(CANDIDATE, 'gnugo-l1'),
      ]

