"""Functional test for find_forfeits.

This also exercises the ringmaster with a 'playoff' tournament.

"""

import os
import shutil
import subprocess
import tempfile

test_dir = os.path.dirname(os.path.abspath(__file__))

playoff_ctl = """

competition_type = 'playoff'

description = 'test_find_forfeits'

stderr_to_log = False

test_player = "%s"

players = {
  'p1' : Player([test_player, '--fail-command=genmove']),
  'p2' : Player([test_player]),
  }

move_limit = 10
record_games = False
board_size = 9
komi = 7.5
scorer = 'internal'

number_of_games = 2

matchups = [
  Matchup('p1', 'p2'),
  ]

""" % os.path.join(test_dir, "gtp_test_player")

ringmaster_expected = """\
forfeit by p1: failure response from 'genmove b' to player p1:
forced to fail from command line
forfeit by p1: failure response from 'genmove b' to player p1:
forced to fail from command line
"""

find_forfeits_expected = """\
p1 v p2: p1 forfeited game 0_0.sgf
p1 v p2: p1 forfeited game 0_1.sgf
"""

class TestFailed(Exception):
    pass

def make_ctl_file(dirname):
    ctl_pathname = os.path.join(dirname, 'ff.ctl')
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

def find_forfeits(ctl_pathname):
    try:
        output = subprocess.check_output(
            ["python", "gomill_examples/find_forfeits.py", ctl_pathname],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, e:
        print e.output
        raise TestFailed("find_forfeits: %d" % e.returncode)
    if output != find_forfeits_expected:
        print output
        raise TestFailed("find_forfeits")

def main():
    dirname = tempfile.mkdtemp(prefix='test_find_forfeits')
    try:
        ctl_pathname = make_ctl_file(dirname)
        run_ringmaster(ctl_pathname)
        find_forfeits(ctl_pathname)
    except TestFailed:
        print "TEST FAILED"
    else:
        print "TEST PASSED"
    finally:
        shutil.rmtree(dirname)

if __name__ == "__main__":
    main()

