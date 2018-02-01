"""Functional tests for the ringmaster.

Doesn't cover very much at the moment.

"""

import os
import re
import shutil
import subprocess
import tempfile

test_dir = os.path.dirname(os.path.abspath(__file__))

base_ctl = """

competition_type = 'playoff'

description = 'test_ringmaster'

test_player = "%s"

players = {
  'p1' : Player([test_player]),
  'p2' : Player([test_player, '--gtp-name=Player two']),
  }

move_limit = 10
record_games = False
board_size = 9
komi = 7.5
scorer = 'internal'

number_of_games = 1

matchups = [
  Matchup('p1', 'p2'),
  ]

""" % os.path.join(test_dir, "gtp_test_player")

def normalise_report(s):
    """Remove nondeterminancy in a ringmaster report."""
    # This is for 'avg cpu' lines
    return re.sub(r"[0-9]\.[0-9]{2}$", "x.xx", s, flags=re.MULTILINE)

class TestFailed(Exception):
    pass

class Test(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('game_log', None)
        kwargs.setdefault('report', None)
        kwargs.setdefault('args', [])
        self.__dict__.update(kwargs)

    def make_ctl_file(self, dirname):
        self.competition_directory = dirname
        self.ctl_pathname = os.path.join(dirname, 'rr.ctl')
        with open(self.ctl_pathname, "w") as f:
            f.write(base_ctl + self.ctl)

    def run_ringmaster(self):
        args = ["python", "-m", "gomill.ringmaster_command_line",
                 self.ctl_pathname, "run", "--quiet"] + self.args
        try:
            output = subprocess.check_output(args, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, e:
            print e.output
            raise TestFailed("ringmaster exit status: %d" % e.returncode)
        if output != "":
            print output
            raise TestFailed("unexpected output from ringmaster")

    def parse_game_log(self, loglines):
        """Read the log entries for a single game from the event log.

        Returns the lines logged from the first game in the log.

        Raises ValueError if the log isn't as expected.

        """
        it = iter(loglines)
        if not re.match(r"run started at [-0-9]+ [:0-9]+ with max_games None$",
                        it.next()):
            raise ValueError("no run start")
        if "--parallel" in self.args:
            if not re.match(r"using \d worker processes$", it.next()):
                raise ValueError("no worker line")
        if not it.next().startswith("starting game"):
            raise ValueError("no game start")
        result = []
        for line in it:
            if line.startswith("response from game"):
                break
            result.append(line.rstrip())
        return result

    def check_game_log(self):
        log_pathname = os.path.join(self.competition_directory, "rr.log")
        loglines = open(log_pathname).readlines()
        try:
            game_log = self.parse_game_log(loglines)
        except ValueError, e:
            print "".join(loglines)
            raise TestFailed("can't parse event log: %s" % e)
        if game_log != self.game_log:
            print game_log
            raise TestFailed("log not as expected")

    def check_report(self):
        report_pathname = os.path.join(self.competition_directory, "rr.report")
        report = normalise_report(open(report_pathname).read())
        if report != self.report:
            print report
            raise TestFailed("report not as expected")

    def run_checks(self):
        if self.game_log is not None:
            self.check_game_log()
        if self.report is not None:
            self.check_report()

    def run(self):
        print "** %s" % self.code
        dirname = tempfile.mkdtemp(prefix='test_ringmaster')
        try:
            self.make_ctl_file(dirname)
            self.run_ringmaster()
            self.run_checks()
        except TestFailed, e:
            print e
            print "TEST FAILED"
        else:
            print "TEST PASSED"
        finally:
            shutil.rmtree(dirname)

tests = [

Test(
code="environ",
ctl="""\
players['p1'] = Player([test_player, '--report-environ'])
""",
game_log=['GOMILL_GAME_ID=0_0'],
report="""\
playoff: rr
test_ringmaster

p1 v p2 (1/1 games)
unknown results: 1 100.00%
board size: 9   komi: 7.5
     wins                 avg cpu
p1      0 0.00%   (black)    x.xx
p2      0 0.00%   (white)    x.xx

player p1: GTP test player
player p2: Player two

""",
),

Test(
code="environ-prl",
args=["--parallel", "2"],
ctl="""\
players['p1'] = Player([test_player, '--report-environ'])
""",
game_log=['GOMILL_GAME_ID=0_0',
          'GOMILL_SLOT=0']
),

]


def main():
    for test in tests:
        test.run()

if __name__ == "__main__":
    main()

