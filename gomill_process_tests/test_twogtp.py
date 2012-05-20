"""Functional test for twogtp.

Requires:
 - gnugo 3.8 in /usr/games/gnugo
 - gomill_process_tests/test_gtp_player
 - gomill_examples/test_gtp_player

Test output may need adjusting if gnugo RNG changes.

"""

import subprocess

tests = [

("failgenmove", 0, """
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='gomill_process_tests/gtp_test_player --fail-command=genmove'
--size=9
--verbose=1
""", """\
Black: GNU Go:3.8
White: GTP test player
B E5
gnugo beat gomill_process_tests/gtp_test_player B+F (forfeit by gomill_process_tests/gtp_test_player: failure response from 'genmove w' to player gomill_process_tests/gtp_test_player:
forced to fail from command line)
"""),

("failgtp", 1, """
gomill_examples/twogtp
--black='echo fail'
--white='gomill_process_tests/gtp_test_player --fail-command=genmove'
--size=9
--verbose=1
""", """\
error creating players:
GTP protocol error reading response to first command (protocol_version) from player echo:
engine isn't speaking GTP: first byte is 'f'

"""),

("samename", 0, """
gomill_examples/twogtp
--black='gomill_examples/gtp_test_player'
--white='gomill_examples/gtp_test_player'
--size=9
""", """\
gomill_examples/gtp_test_player-b vs gomill_examples/gtp_test_player-w ? (no score reported)
"""),

("gnugo", 0, """
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=5
--games=2
""", """\
gnugo beat /usr/games/gnugo B+R
gnugo beat /usr/games/gnugo B+R
"""),

("verbose-1", 0, """
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=5
--verbose=1
""", """\
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

("verbose-2", 0, """
gomill_examples/twogtp
--black='gnugo --mode=gtp --level=0 --seed=1'
--white='/usr/games/gnugo --mode=gtp --level=0 --seed=2'
--size=3
--verbose=2
""", """\
Black: GNU Go:3.8

White: GNU Go:3.8

B B2
3  .  .  .
2  .  #  .
1  .  .  .
   A  B  C

gnugo beat /usr/games/gnugo B+R
"""),

]

def testrun(code, expected_status, cmd, expected_output):
    print "** %s" % code
    try:
        output = subprocess.check_output(
            cmd.replace("\n", " "),
            shell=True,
            stderr=subprocess.STDOUT)
        status = 0
    except subprocess.CalledProcessError, e:
        status = e.returncode
        output = e.output
    passed = True
    if output != expected_output:
        passed = False
        print "BAD OUTPUT"
        print output
    if status != expected_status:
        passed = False
        print "BAD EXIT STATUS"
        print status
    if passed:
        print "TEST PASSED"
    else:
        print "TEST FAILED"

#SKIP = set(['gnugo', 'verbose-1'])
SKIP = set()

def main():
    for t in tests:
        if t[0] in SKIP:
            print "## %s: SKIP" % t[0]
            continue
        testrun(*t)

if __name__ == "__main__":
    main()

