# The following settings are supported:
#
# - all _common settings_
#
# - all _game settings_
#
# - tuning event settings (cf mcts_tuner):
#   - candidate_colour
#   - opponent
#   - parameters
#   - make_candidate
#
# - settings for experiment control
#   - parallel      -- number of games to run in parallel
#   - stop_on_error -- boolean
#
# - regression parameters:
#   - clop_H        -- float
#   - correlations  -- 'all' (default) or 'none'
#
## <<
# clop_H: 3 is recommended (it is the default value)
# correlations:
# Even if variables are not correlated "all" should work well. The problem is
# that the regression might become very costly if the number of variables is
# high. So use "correlations none" only if you are certain parameters are
# independent or you have so many variables that "all" is too costly.
## >>
#

# The available parameter types are:
#  LinearParameter
#  IntegerParameter
#  GammaParameter
#  IntegerGammaParameter
# For GammaParameter, quadratic regression is performed on log(x)

competition_type = "clop_tuner"

description = """\
Sample control file for CLOP integration.

"""

def gnugo(level):
    return Player("gnugo --mode=gtp --chinese-rules --capture-all-dead "
                  "--level=%d" % level)

def pachi(playouts, policy):
    return Player(
        "~/src/pachi/pachi "
        "-d 0 "   # silence stderr
        "-t =%d "
        "threads=1,max_tree_size=2048 "
        "policy=%s "
        % (playouts, policy))

players = {
    'gnugo-l7' : gnugo(7),
    }


parameters = [
    Parameter('equiv_rave',
              type = "GammaParameter",
              min = 40,
              max = 32000),
    ]

def make_candidate(equiv_rave):
    return pachi(2000, policy="ucb1amaf:equiv_rave=%f" % equiv_rave)

board_size = 19
komi = 7.5
opponent = 'gnugo-l7'
candidate_colour = 'w'
parallel = 2

