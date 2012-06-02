"""Functional tests for the ringmaster.

At the moment this just covers capture_stderr.

"""

import os
import shutil
import subprocess
import tempfile

from gomill import sgf
from gomill.common import format_vertex

def sgf_moves_and_comments(sgf_game):
    """Extract moves and comments from an Sgf_game.

    Returns a list of strings.

    """
    def fmt(node):
        colour, move = node.get_move()
        if colour is None and node is sgf_game.get_root():
            src = "root"
        else:
            src = "%s %s" % (colour, format_vertex(move))
        try:
            comment = node.get("C")
        except KeyError:
            comment = "--"
        return "%s: %s" % (src, comment)
    return map(fmt, sgf_game.get_main_sequence())

def sgf_moves_and_comments_from_string(s):
    """Variant of sgf_moves_and_comments taking a string parameter."""
    return sgf_moves_and_comments(sgf.Sgf_game.from_string(s))


test_dir = os.path.dirname(os.path.abspath(__file__))

playoff_ctl = """

competition_type = 'playoff'

description = 'test_ringmaster'

stderr_to_log = False

test_player = "%s"

players = {
  'p1' : Player([test_player, '--chat-stderr', '--seed=5'],
                 capture_stderr=True),
  'p2' : Player([test_player, '--seed=4']),
  }

move_limit = 10
record_games = False
board_size = 9
komi = 7.5
scorer = 'internal'

record_games=True
number_of_games = 1

matchups = [
  Matchup('p1', 'p2'),
  ]

""" % os.path.join(test_dir, "gtp_test_player")

ringmaster_expected = ""

class TestFailed(Exception):
    pass

def make_ctl_file(dirname):
    ctl_pathname = os.path.join(dirname, 'rr.ctl')
    with open(ctl_pathname, "w") as f:
        f.write(playoff_ctl)
    return ctl_pathname

def run_ringmaster(ctl_pathname):
    try:
        output = subprocess.check_output(
            ["python", "-m", "gomill.ringmaster_command_line",
             ctl_pathname, "run", "--quiet"],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, e:
        print e.output
        raise TestFailed("ringmaster: %d" % e.returncode)
    if output != ringmaster_expected:
        print output
        raise TestFailed("ringmaster")
    print ctl_pathname
    sgf_pathname = os.path.join(os.path.dirname(ctl_pathname),
                                "rr.games", "0_0.sgf")
    mac = sgf_moves_and_comments_from_string(open(sgf_pathname).read())
    if mac[1:] != [
        "b G7: genmove: 0\n",
        "w J1: --",
        "b E9: genmove: 2\n",
        "w E2: --",
        "b C9: genmove: 4\n\n\np1 beat p2 B+R",
        ]:
        print "\n".join(mac[1:])
        raise TestFailed("sgf")


def main():
    dirname = tempfile.mkdtemp(prefix='test_ringmaster')
    try:
        ctl_pathname = make_ctl_file(dirname)
        run_ringmaster(ctl_pathname)
    except TestFailed, e:
        print e
        print "TEST FAILED"
    else:
        print "TEST PASSED"
    finally:
        shutil.rmtree(dirname)

if __name__ == "__main__":
    main()

