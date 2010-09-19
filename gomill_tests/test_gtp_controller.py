import sys
import os

from gomill import gtp_controller

from gomill_tests import test_gtp_state
from gomill import gtp_states

def test_gmp():
    devnull = open(os.devnull, "w")
    # oops, we forgot --mode=gtp
    gnugo = gtp_controller.Subprocess_gtp_channel(
        ["gnugo"], stderr=devnull)
    devnull.close()
    controller = gtp_controller.Gtp_controller(gnugo, "gnugo")
    try:
        controller.check_protocol_version()
    except gtp_controller.GtpProtocolError, e:
        print e
    else:
        raise AssertionError("no protocol error")


def test_misc():
    # Enable diagnostics to stderr, but send them to /dev/null
    devnull = open(os.devnull, "w")
    c1 = gtp_controller.Subprocess_gtp_channel(
        "./player -m kiai.simple_montecarlo_player --diag=t".split(),
        stderr=devnull.fileno())
    devnull.close()
    controller1 = gtp_controller.Gtp_controller(c1, "first")

    #controller1.channel.enable_logging(sys.stdout, ' first: ')

    gtp_state = gtp_states.Gtp_state(test_gtp_state.dummy_move_generator, [9])
    engine = test_gtp_state.kiai_dummy_engine(gtp_state)
    c2 = gtp_controller.Internal_gtp_channel(engine)

    #c2 = gtp_controller.Subprocess_gtp_channel(
    #    "gnugo --mode=gtp --boardsize=9".split())

    controller2 = gtp_controller.Gtp_controller(c2, "second")
    #controller2.channel.enable_logging(sys.stdout, ' second: ')


    def send_command(controller, command, *arguments):
        try:
            response = controller.do_command(command, *arguments)
        except gtp_controller.GtpEngineError, e:
            response = None
        return response

    i = 0
    while i < 3:
        move = send_command(controller1, "genmove", "b").strip()
        send_command(controller1, "showboard")
        send_command(controller2, "play", "b", move)
        move = send_command(controller2, "genmove", "w").strip()
        send_command(controller2, "showboard")
        send_command(controller1, "play", "w", move)
        i += 1

    send_command(controller1, "play", "w", "resign")
    send_command(controller2, "asdasd", "w", move)
    #send_command(controller1, "quit")
    #send_command(controller2, "quit")

    print "Shutting down first"
    rusage = controller1.close_channel()
    print "Shutting down second"
    controller2.close_channel()

    print "Resource usage:"
    print rusage.ru_utime
    print rusage.ru_stime
    print rusage.ru_nvcsw
    print rusage.ru_nivcsw

if __name__ == "__main__":
    test_gmp()
    test_misc()
