import sys

from gomill import gtp_controller

from gomill_tests import test_gtp_board
from gomill import gtp_boards


def test():
    controller = gtp_controller.Gtp_controller_protocol()

    c1 = gtp_controller.Subprocess_gtp_channel(
        "./player -m kiai.simple_montecarlo_player".split())
    controller.add_channel("first", c1)

    controller.enable_logging(sys.stdout)

    gtp_board = gtp_boards.Gtp_board(test_gtp_board.dummy_move_generator, [9])
    engine = test_gtp_board.kiai_dummy_engine(gtp_board)
    c2 = gtp_controller.Internal_gtp_channel(engine)

    #c2 = gtp_controller.Subprocess_gtp_channel(
    #    "gnugo --mode=gtp --boardsize=9".split())

    controller.add_channel("second", c2)


    def send_command(channel_id, command, *arguments):
        try:
            response = controller.do_command(channel_id, command, *arguments)
        except gtp_controller.GtpEngineError, e:
            response = None
        return response

    i = 0
    while i < 3:
        move = send_command("first", "genmove", "b").strip()
        send_command("first", "showboard")
        send_command("second", "play", "b", move)
        move = send_command("second", "genmove", "w").strip()
        send_command("second", "showboard")
        send_command("first", "play", "w", move)
        i += 1

    send_command("first", "play", "w", "resign")
    send_command("second", "asdasd", "w", move)
    #send_command("first", "quit")
    #send_command("second", "quit")

    print "Shutting down first"
    rusage = controller.close_channel("first")
    print "Shutting down second"
    controller.close_channel("second")

    print "Resource usage:"
    print rusage.ru_utime
    print rusage.ru_stime
    print rusage.ru_nvcsw
    print rusage.ru_nivcsw

if __name__ == "__main__":
    test()
