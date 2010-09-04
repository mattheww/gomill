"""Command-line interface to the ringmaster."""

import os
import sys
from optparse import OptionParser

from gomill import compact_tracebacks
from gomill import job_manager # FIXME
from gomill.ringmaster import Ringmaster, RingmasterError

def do_run(ringmaster, options):
    if options.log_gtp:
        ringmaster.enable_gtp_logging()
    if options.quiet:
        ringmaster.set_quiet_mode()
    if ringmaster.status_file_exists():
        ringmaster.load_status()
    else:
        ringmaster.set_clean_status()
    if options.parallel is not None:
        ringmaster.set_parallel_worker_count(options.parallel)
    ringmaster.run(options.max_games)
    ringmaster.report()

def do_stop(ringmaster, options):
    try:
        f = open(ringmaster.command_pathname, "w")
        f.write("stop")
        f.close()
    except EnvironmentError, e:
        raise RingmasterError("error writing command file:\n%s" % e)

def do_show(ringmaster, options):
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.print_status_report()

def do_report(ringmaster, options):
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.report()

def do_reset(ringmaster, options):
    ringmaster.delete_state_and_output()

def do_check(ringmaster, options):
    if not ringmaster.check_players():
        return 1

def do_debugstatus(ringmaster, options):
    ringmaster.print_status()


_actions = {
    "run" : do_run,
    "stop" : do_stop,
    "show" : do_show,
    "report" : do_report,
    "reset" : do_reset,
    "check" : do_check,
    "debugstatus" : do_debugstatus,
    }

def run(argv, ringmaster_class):
    usage = ("%prog [options] <control file> [command]\n\n"
             "commands: run (default), stop, show, report, reset, check")
    parser = OptionParser(usage=usage, prog="ringmaster")
    parser.add_option("--max-games", "-g", type="int",
                      help="maximum number of games to play in this run")
    parser.add_option("--parallel", "-j", type="int",
                      help="number of worker processes")
    parser.add_option("--quiet", "-q", action="store_true",
                      help="silent except for warnings and errors")
    parser.add_option("--log-gtp", action="store_true",
                      help="write GTP logs")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("no control file specified")
    if len(args) > 2:
        parser.error("too many arguments")
    if len(args) == 1:
        command = "run"
    else:
        command = args[1]
    try:
        action = _actions[command]
    except KeyError:
        parser.error("no such command: %s" % command)
    tourn_pathname = args[0]
    if not tourn_pathname.endswith(".tourn"):
        parser.error("not a .tourn file")
    try:
        if not os.path.exists(tourn_pathname):
            raise RingmasterError("control file %s not found" % tourn_pathname)
        ringmaster = ringmaster_class(tourn_pathname)
        exit_status = action(ringmaster, options)
    except RingmasterError, e:
        print >>sys.stderr, "ringmaster:", e
        exit_status = 1
    except KeyboardInterrupt:
        exit_status = 3
    except job_manager.JobSourceError, e:
        print >>sys.stderr, "ringmaster: internal error"
        print >>sys.stderr, e
        exit_status = 4
    except:
        print >>sys.stderr, "ringmaster: internal error"
        compact_tracebacks.log_traceback()
        exit_status = 4
    sys.exit(exit_status)

def main():
    run(sys.argv, Ringmaster)

if __name__ == "__main__":
    main()

