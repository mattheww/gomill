from gomill import gtp_engine
from gomill.gtp_engine import GtpError, GtpFatalError

def test():
    def handle_error(args):
        raise GtpError("normal error")

    def handle_fatal_error(args):
        raise GtpFatalError("fatal error")

    def handle_internal_error(args):
        os.path.join("foo", None)

    def handle_test(args):
        return "this respo\x7fnse\n\nne\x00eds\ncleanup\xa3"

    def handle_play(args):
        try:
            colour_s, vertex_s = args[:2]
        except ValueError:
            report_bad_arguments()
        colour = gtp_engine.interpret_colour(colour_s)
        vertex = gtp_engine.interpret_vertex(vertex_s, board_size=9)
        return str(vertex)

    def handle_komi(args):
        try:
            komi = gtp_engine.interpret_float(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        return komi

    engine = gtp_engine.Gtp_engine_protocol()
    engine.add_protocol_commands()
    engine.add_command('help', engine.handle_list_commands)
    engine.add_command('test', handle_test)
    engine.add_command('error', handle_error)
    engine.add_command('fatal', handle_fatal_error)
    engine.add_command('internal_error', handle_internal_error)
    engine.add_command('play', handle_play)
    engine.add_command('komi', handle_komi)
    engine.add_command('komi2', handle_komi)
    engine.remove_command('komi2')
    gtp_engine.run_interactive_gtp_session(engine)
    #gtp_engine.run_gtp_session(engine, sys.stdin, sys.stdout)

if __name__ == "__main__":
    test()
