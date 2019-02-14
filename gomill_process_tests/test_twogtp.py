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
import tempfile

from gomill import __version__

class Test(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('sgf', None)
        kwargs.setdefault('exit_status', 0)
        self.__dict__.update(kwargs)


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
--white='gomill_process_tests/gtp_test_player --fail-command=genmove'
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
--size=3 --sgfbase=%(sgfbase)s
""",
output="""\
gnugo beat /usr/games/gnugo B+R
""",
sgf="(;FF[4]AP[Gomill twogtp:VER]CA[UTF-8]DT[***]GM[1]KM[7.5]PB[GNU Go:3.8]"
    "PW[GNU Go:3.8]RE[B+R]SZ[3];B[bb]C[gnugo beat /usr/games/gnugo B+R])"
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
    if output != test.output:
        passed = False
        print "BAD OUTPUT"
        print output
    if status != test.exit_status:
        passed = False
        print "BAD EXIT STATUS"
        print status
    if test.sgf:
        sgf_written = open("%s/%s000.sgf" % (sandbox_dir, test.code)).read()
        if scrub_sgf(sgf_written) != test.sgf:
            passed = False
            print "BAD SGF"
            print sgf_written
    if passed:
        print "TEST PASSED"
    else:
        print "TEST FAILED"

#SKIP = set(['gnugo', 'verbose-1'])
SKIP = set()

def main():
    dirname = tempfile.mkdtemp(prefix='test_twogtp')
    try:
        for test in tests:
            if test.code in SKIP:
                print "## %s: SKIP" % test.code
                continue
            testrun(test, dirname)
    finally:
        shutil.rmtree(dirname)

if __name__ == "__main__":
    main()

