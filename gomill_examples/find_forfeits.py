"""Find forfeited games in tournament results.

This demonstrates retrieving and processing results from a tournament.

"""

import sys
from optparse import OptionParser

from gomill.common import opponent_of
from gomill.ringmasters import Ringmaster, RingmasterError

def show_result(matchup, result, filename):
    print "%s: %s forfeited game %s" % (
        matchup.name, result.losing_player, filename)

def find_forfeits(ringmaster):
    ringmaster.load_status()
    tournament_results = ringmaster.get_tournament_results()
    matchup_ids = tournament_results.get_matchup_ids()
    for matchup_id in matchup_ids:
        matchup = tournament_results.get_matchup(matchup_id)
        results = tournament_results.get_matchup_results(matchup_id)
        for result in results:
            if result.is_forfeit:
                filename = ringmaster.get_sgf_filename(result.game_id)
                show_result(matchup, result, filename)


_description = """\
Read results of a tournament and show all forfeited games.
"""

def main(argv):
    parser = OptionParser(usage="%prog <filename.ctl>",
                          description=_description)
    opts, args = parser.parse_args(argv)
    if not args:
        parser.error("not enough arguments")
    if len(args) > 1:
        parser.error("too many arguments")
    ctl_pathname = args[0]
    try:
        ringmaster = Ringmaster(ctl_pathname)
        find_forfeits(ringmaster)
    except RingmasterError, e:
        print >>sys.stderr, "ringmaster:"
        print >>sys.stderr, e
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

