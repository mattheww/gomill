"""Functional test for twogtp.

Requires:
 - gnugo 3.8 in /usr/games/gnugo
 - gomill_process_tests/gtp_test_player
 - gomill_examples/gtp_test_player

Test output may need adjusting if gnugo RNG changes.

"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

from gomill import __version__

class Test(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('sgf', None)
        kwargs.setdefault('exit_status', 0)
        self.__dict__.update(kwargs)

    def expected_output(self):
        return self.output.strip()

    def expected_sgf(self):
        return self.sgf.replace("\n", "")

tests = [

Test(
code="failgenmove",
command="""
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='gomill_process_tests/gtp_test_player --fail-command=genmove'
--size=9
--verbose=1
""",
output="""\
Black: GNU Go:3.8
White: GTP test player
B E5
gnugo beat gomill_process_tests/gtp_test_player B+F (forfeit by gomill_process_tests/gtp_test_player: failure response from 'genmove w' to player gomill_process_tests/gtp_test_player:
forced to fail from command line)
"""),

Test(
code="failgtp",
command="""
gomill_examples/twogtp
--black='echo fail'
--white='gomill_process_tests/gtp_test_player'
--size=9
--verbose=1
""",
output="""\
error creating players:
GTP protocol error reading response to first command (protocol_version) from player echo:
engine isn't speaking GTP: first byte is 'f'

""",
exit_status=1),

Test(
code="samename",
command="""
gomill_examples/twogtp
--black='gomill_examples/gtp_test_player'
--white='gomill_examples/gtp_test_player'
--size=9
""",
output="""\
gomill_examples/gtp_test_player-b vs gomill_examples/gtp_test_player-w ? (no score reported)
"""),

Test(
code="gnugo",
command="""
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=5
--games=2
""",
output="""\
gnugo beat /usr/games/gnugo B+R
gnugo beat /usr/games/gnugo B+R
"""),

Test(
code="verbose-1",
command="""
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=5
--verbose=1
""",
output="""\
Black: GNU Go:3.8
White: GNU Go:3.8
B C3
W C4
B B4
W B3
B D4
W D3
B C2
W D2
B E2
W E4
B C5
W B2
B B1
W D5
B C4
gnugo beat /usr/games/gnugo B+R
"""),

Test(
code="verbose-2",
command="""
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=3
--verbose=2
""",
output="""\
Black: GNU Go:3.8

White: GNU Go:3.8

B B2
3  .  .  .
2  .  #  .
1  .  .  .
   A  B  C

gnugo beat /usr/games/gnugo B+R
"""),

Test(
code="sgf",
command="""
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=3
--sgfbase=%(sgfbase)s
""",
output="""\
gnugo beat /usr/games/gnugo B+R
""",
sgf="""
(;FF[4]AP[Gomill twogtp:VER]CA[UTF-8]DT[***]GM[1]KM[7.5]PB[GNU Go:3.8]
PW[GNU Go:3.8]RE[B+R]SZ[3];B[bb]C[gnugo beat /usr/games/gnugo B+R])
"""
),

Test(
code="stderr",
command="""
gomill_examples/twogtp
--black='gomill_process_tests/gtp_test_player --seed=3 --chat-stderr'
--white='gomill_process_tests/gtp_test_player --seed=3'
--size=9
--capture-stderr=bw
--sgfbase=%(sgfbase)s
""",
output="""\
gomill_process_tests/gtp_test_player-w beat gomill_process_tests/gtp_test_player-b W+R
""",
sgf="""
(;FF[4]AP[Gomill twogtp:VER]CA[UTF-8]DT[***]GM[1]KM[7.5]PB[GTP test player]
PW[GTP test player]RE[W+R]SZ[9];B[ie]C[genmove: 0];W[he];B[ed]C[genmove: 2];
W[fd];B[fi]C[genmove: 4];
C[final message from b: <<<genmove: 6>>>
gomill_process_tests/gtp_test_player-w beat gomill_process_tests/gtp_test_player-b W+R]
W[ei])
"""
),

Test(
code="exit-uncleanly",
command="""
gomill_examples/twogtp
--black='gomill_process_tests/gtp_test_player --seed=3 --exit-uncleanly'
--white='gomill_process_tests/gtp_test_player --seed=3'
--size=9
--sgfbase=%(sgfbase)s
""",
output="""\
error reading response to 'quit' from player gomill_process_tests/gtp_test_player-b:
engine has closed the response channel
gomill_process_tests/gtp_test_player-w beat gomill_process_tests/gtp_test_player-b W+R
""",
),

Test(
code="dies",
command="""
gomill_examples/twogtp
--black='gomill_process_tests/gtp_test_player --seed=3
                                              --move-limit=2 --exit-uncleanly'
--white='gomill_process_tests/gtp_test_player --seed=3'
--size=9
--sgfbase=%(sgfbase)s
""",
output="""\
aborting run due to error:
error reading response to 'genmove b' from player gomill_process_tests/gtp_test_player-b:
engine has closed the response channel

""",
exit_status=1,
),

Test(
code="badoption",
command="""
gomill_examples/twogtp
--black='gomill_process_tests/gtp_test_player --seed=3'
--white='gomill_process_tests/gtp_test_player --unknownoption'
--size=9
""",
output="""\
Usage: gtp_test_player [options]

gtp_test_player: error: no such option: --unknownoption
error creating players:
error reading response to first command (protocol_version) from player gomill_process_tests/gtp_test_player-w:
engine has closed the response channel
""",
exit_status=1,
),

Test(
code="badoption-capture",
command="""
gomill_examples/twogtp
--black='gomill_process_tests/gtp_test_player --seed=3'
--white='gomill_process_tests/gtp_test_player --unknownoption'
--capture-stderr=bw
--size=9
""",
output="""\
gomill_process_tests/gtp_test_player-w says:
Usage: gtp_test_player [options]

gtp_test_player: error: no such option: --unknownoption

error creating players:
error reading response to first command (protocol_version) from player gomill_process_tests/gtp_test_player-w:
engine has closed the response channel
""",
exit_status=1,
),

]

def scrub_sgf(s):
    """Normalise sgf string for convenience of testing.

    Replaces dates with '***', and 'twogtp:<__version__>' with 'twogtp:VER'.

    Removes newlines.

    """
    s = re.sub(r"(?<=DT\[)[-0-9]+(?=\])", "***", s)
    s = re.sub(r"twogtp:" + re.escape(__version__), "twogtp:VER", s)
    s = s.replace("\n", "")
    return s

def testrun(test, sandbox_dir):
    print "** %s" % test.code
    sgfbase = os.path.join(sandbox_dir, test.code)
    try:
        output = subprocess.check_output(
            test.command.replace("\n", " ") % locals(),
            shell=True,
            stderr=subprocess.STDOUT)
        status = 0
    except subprocess.CalledProcessError, e:
        status = e.returncode
        output = e.output
    passed = True
    output = output.strip()
    if output != test.expected_output():
        passed = False
        print "BAD OUTPUT"
        print output
    if status != test.exit_status:
        passed = False
        print "BAD EXIT STATUS"
        print status
    if test.sgf and (passed or status == 0):
        sgf_written = open("%s/%s000.sgf" % (sandbox_dir, test.code)).read()
        if scrub_sgf(sgf_written) != test.expected_sgf():
            passed = False
            print "BAD SGF"
            if len(sgf_written) < 4096:
                print sgf_written
    if passed:
        print "TEST PASSED"
    else:
        print "TEST FAILED"

def run(include, skip):
    dirname = tempfile.mkdtemp(prefix='test_twogtp')
    try:
        for test in tests:
            if test.code in skip or (include and test.code not in include):
                print "## %s: SKIP" % test.code
                continue
            testrun(test, dirname)
    finally:
        shutil.rmtree(dirname)

SLOW = set(['gnugo', 'verbose-1'])

def main(argv):
    skip = set()
    include = None
    if len(argv) > 0:
        if argv[0] == "--quick":
            skip = SLOW
        else:
            include = set(argv)
    run(include, skip)

if __name__ == "__main__":
    main(sys.argv[1:])

