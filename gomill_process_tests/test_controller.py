"""Process-level controller tests, using gtp_test_controller.

Requires:
 - gomill_process_tests/gtp_test_player

"""

import os
import re
import subprocess
import sys

from gomill import __version__

class Test(object):
    def __init__(self, **kwargs):
        kwargs.setdefault('sgf', None)
        kwargs.setdefault('exit_status', 0)
        self.__dict__.update(kwargs)

    def expected_output(self):
        return self.output.strip()

tests = [

Test(
code="failed-startup",
command="""
gomill_process_tests/gtp_test_controller
--white='--bad-option'
""",
exit_status=1,
output="""\
Usage: gtp_test_player [options]

gtp_test_player: error: no such option: --bad-option
error creating players:
error reading response to first command (protocol_version) from player white:
engine has closed the response channel
""",
),

Test(
code="failed-startup-nonblocking",
command="""
gomill_process_tests/gtp_test_controller
--white='--bad-option'
--capture-stderr=bw
""",
exit_status=1,
output="""\
w says:
Usage: gtp_test_player [options]

gtp_test_player: error: no such option: --bad-option

error creating players:
error reading response to first command (protocol_version) from player white:
engine has closed the response channel
""",
),

Test(
code="stderr",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr'
--capture-stderr=bw
""",
output="""\
b B3 genmove: 0
w C3 --
b J5 genmove: 2
w A6 --
final: b: genmove: 4

white beat black W+R
""",
),

Test(
code="nocapture",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr'
--white='--chat-stderr'
--capture-stderr=b
""",
output="""\
genmove: 1
genmove: 3
b B3 genmove: 0
w C3 --
b J5 genmove: 2
w A6 --
final: b: genmove: 4

white beat black W+R
""",
),

Test(
code="stderr-large",
command="""
gomill_process_tests/gtp_test_controller
--black='--copious-stderr'
--capture-stderr=b
""",
output="""\
b B3 xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|
w C3 --
b J5 xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|
w A6 --
final: b: xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|xxxx[16385]
|
white beat black W+R
""",
),

Test(
code="dies",
command="""
gomill_process_tests/gtp_test_controller
--black='--move-limit=2 --exit-uncleanly'
""",
output="""\
aborting run due to error:
error reading response to 'genmove b' from player black:
engine has closed the response channel

b B3 --
w C3 --
""",
),

Test(
code="dies-nonblocking",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr --move-limit=2 --exit-uncleanly'
--capture-stderr=bw
""",
output="""\
aborting run due to error:
error reading response to 'genmove b' from player black:
engine has closed the response channel

b B3 genmove: 0
w C3 --
b says:
genmove: 2
""",
),

Test(
code="dies-nonblocking2",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=kill
""",
output="""\
aborting run due to error:
error reading response to 'genmove b' from player black:
engine has closed the response channel

b B3 genmove: 0
w C3 --
b says:
genmove: 2
""",
),

Test(
code="late-error",
command="""
gomill_process_tests/gtp_test_controller
--black='--fail-command=play --exit-uncleanly'
""",
output="""\
b B3 --
white beat black W+F (forfeit by black: failure response from 'play w C3' to player black:
forced to fail from command line)

late errors:
error reading response to 'quit' from player black:
engine has closed the response channel
""",
),

Test(
code="stdout-errors",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr --ignore-broken-stderr-pipe'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=stdout-errors
""",
output="""\
aborting run due to error:
transport error reading response to 'genmove b' from player black:
[Errno 21] Is a directory

b B3 genmove: 0
w C3 --
b says:
genmove: 2
""",
),

Test(
code="stderr-close",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr --close-stderr'
--capture-stderr=bw
""",
output="""\
b B3 genmove: 0
w C3 --
b J5 --
w A6 --
white beat black W+R
""",
),

Test(
code="stderr-errors",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr --ignore-broken-stderr-pipe'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=stderr-errors
""",
output="""\
b B3 genmove: 0
w C3 --
b J5 genmove: 2

[error reading from stderr: [Errno 21] Is a directory]
w A6 --
white beat black W+R
""",
),

Test(
code="opponent-stdout-errors",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr --ignore-broken-stderr-pipe'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=opponent-stdout-errors
""",
output="""\
aborting run due to error:
transport error reading response to 'play b J5' from player white:
[Errno 21] Is a directory

b B3 genmove: 0
w C3 --
""",
),

Test(
code="opponent-stderr-errors",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr'
--white='--chat-stderr --ignore-broken-stderr-pipe'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=opponent-stderr-errors
""",
output="""\
b B3 genmove: 0
w C3 genmove: 1
b J5 genmove: 2
w A6 [error reading from stderr: [Errno 21] Is a directory]
final: b: genmove: 4

white beat black W+R
""",
),

Test(
code="opponent-dies",
command="""
gomill_process_tests/gtp_test_controller
--black='--chat-stderr'
--capture-stderr=bw
--trigger-colour=b
--trigger-message='genmove: 2'
--trigger-action=opponent-kill
""",
output="""\
aborting run due to error:
error sending 'play b J5' to player white:
engine has closed the command channel

b B3 genmove: 0
w C3 --
""",
),

Test(
code="ponder",
command="""
gomill_process_tests/gtp_test_controller
--black='--move-limit=4 --fake-ponder'
--white='--move-limit=4 --move-sleep=1'
--capture-stderr=bw
""",
output="""\
b B3 --
w C3 --
b J5 """ + "xxxx[3072]|" * 50 + """
w A6 --
white beat black W+R
""",
),

]


def clean_output(s):
    def clean_xs(match):
        return "xxxx[%d]" % len(match.group(0))
    s = s.strip()
    s = re.sub(r"xxxxx*", clean_xs, s)
    return s

def testrun(test):
    print "** %s" % test.code
    try:
        output = subprocess.check_output(
            test.command.replace("\n", " "),
            shell=True,
            stderr=subprocess.STDOUT)
        status = 0
    except subprocess.CalledProcessError, e:
        status = e.returncode
        output = e.output
    passed = True
    output = clean_output(output)
    if output != test.expected_output():
        passed = False
        print "BAD OUTPUT"
        print output[:4096]
    if status != test.exit_status:
        passed = False
        print "BAD EXIT STATUS"
        print status
    if passed:
        print "TEST PASSED"
    else:
        print "TEST FAILED"

def run(include, skip):
    for test in tests:
        if test.code in skip or (include and test.code not in include):
            print "## %s: SKIP" % test.code
            continue
        testrun(test)

SLOW = set(['stderr-large', 'ponder'])

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

