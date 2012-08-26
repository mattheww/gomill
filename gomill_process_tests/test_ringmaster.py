"""Functional tests for the ringmaster.

Doesn't cover very much at the moment.

"""

import os
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
  'p2' : Player([test_player]),
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

class TestFailed(Exception):
    pass

class Test(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('game_log', None)
        self.__dict__.update(kwargs)

    def make_ctl_file(self, dirname):
        self.competition_directory = dirname
        self.ctl_pathname = os.path.join(dirname, 'rr.ctl')
        with open(self.ctl_pathname, "w") as f:
            f.write(base_ctl + self.ctl)

    def extract_game_log(self):
        """Read the log entries for a single game from the event log.

        Returns the lines logged from the first game in the log.

        Raises ValueError if the log isn't as expected.

        """
        log_pathname = os.path.join(self.competition_directory, "rr.log")
        loglines = open(log_pathname).readlines()
        if not loglines[0].startswith("run started at"):
            raise ValueError
        if not loglines[1].startswith("starting game"):
            raise ValueError
        result = []
        for line in loglines[2:]:
            if line.startswith("response from game"):
                break
            result.append(line.rstrip())
        return result

    def run_ringmaster(self):
        try:
            output = subprocess.check_output(
                ["python", "-m", "gomill.ringmaster_command_line",
                 self.ctl_pathname, "run", "--quiet"],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, e:
            print e.output
            raise TestFailed("ringmaster exit status: %d" % e.returncode)
        if output != "":
            print output
            raise TestFailed("unexpected output from ringmaster")

    def run_checks(self):
        if self.game_log is not None:
            game_log = self.extract_game_log()
            if game_log != self.game_log:
                print game_log
                raise TestFailed("log not as expected")

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
game_log=['GOMILL_GAME_ID=0_0']
),

]


def main():
    for test in tests:
        test.run()

if __name__ == "__main__":
    main()

