"""Find forfeited games in playoff results.

This demonstrates retrieving and processing playoff results.

"""

import sys
from optparse import OptionParser

from gomill.gomill_common import opponent_of
from gomill.ringmasters import Ringmaster, RingmasterError

# FIXME
def loser(result):
    return {'b' : result.player_b, 'w' : result.player_w}\
         [opponent_of(result.winning_colour)]

def show_result(matchup, game_id, result):
    print "%s: %s forfeited game %s" % (matchup.name, loser(result), game_id)

def find_forfeits(ringmaster):
    if ringmaster.competition_type != 'playoff':
        raise RingmasterError("not a playoff")
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    playoff = ringmaster.competition
    matchup_ids = playoff.get_matchup_ids()
    for matchup_id in matchup_ids:
        matchup = playoff.get_matchup(matchup_id)
        results = playoff.get_matchup_results(matchup_id)
        for game_id, result in results:
            if result.is_forfeit:
                show_result(matchup, game_id, result)


_description = """\
Read results of a playoff and show all forfeited games.
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
    if not ctl_pathname.endswith(".ctl"):
        parser.error("not a .ctl file")
    try:
        ringmaster = Ringmaster(ctl_pathname)
        find_forfeits(ringmaster)
    except RingmasterError, e:
        print >>sys.stderr, "ringmaster:"
        print >>sys.stderr, e
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

