"""Command-line interface to the ringmaster."""

import os
import sys
from optparse import OptionParser

from ringmaster import Ringmaster, RingmasterError

def do_run(ringmaster, worker_count=None, max_games=None):
    if ringmaster.status_file_exists():
        ringmaster.load_status()
    else:
        ringmaster.set_clean_status()
    if worker_count is not None:
        ringmaster.set_parallel_worker_count(worker_count)
    ringmaster.run(max_games)
    ringmaster.report()

def do_show(ringmaster):
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.print_status_report()

def do_report(ringmaster):
    if not ringmaster.status_file_exists():
        raise RingmasterError("no status file")
    ringmaster.load_status()
    ringmaster.report()

def do_stop(ringmaster):
    try:
        f = open(ringmaster.command_pathname, "w")
        f.write("stop")
        f.close()
    except EnvironmentError, e:
        raise RingmasterError("error writing command file:\n%s" % e)

def do_reset(ringmaster):
    ringmaster.delete_state_and_output()


def main():
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
        if command not in ("run", "stop", "show", "report", "reset",
                           "check", "debugstatus"):
            parser.error("no such command: %s" % command)
    tourn_pathname = args[0]
    if not tourn_pathname.endswith(".tourn"):
        parser.error("not a .tourn file")
    exit_status = 0
    try:
        if not os.path.exists(tourn_pathname):
            raise RingmasterError("control file %s not found" % tourn_pathname)
        ringmaster = Ringmaster(tourn_pathname)
        if command == "run":
            if options.log_gtp:
                ringmaster.enable_gtp_logging()
            if options.quiet:
                ringmaster.set_quiet_mode()
            do_run(ringmaster, options.parallel, options.max_games)
        elif command == "show":
            do_show(ringmaster)
        elif command == "stop":
            do_stop(ringmaster)
        elif command == "report":
            do_report(ringmaster)
        elif command == "reset":
            do_reset(ringmaster)
        elif command == "check":
            if not ringmaster.check_players():
                exit_status = 1
        elif command == "debugstatus":
            ringmaster.print_status()
        else:
            raise AssertionError
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

if __name__ == "__main__":
    main()

