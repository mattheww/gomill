from gomill import gtp_engine
from gomill import gtp_controller
from gomill import gtp_proxy

def handle_mytest(args):
    return "mytest: %s" % ",".join(args)

def main():
    def handle_mygenmove(args):
        return (proxy.pass_command('genmove', args) + "\n" +
                proxy.pass_command('gomill-explain_last_move', []))

    channel = gtp_controller.Subprocess_gtp_channel(
        "./player -m kiai.simple_montecarlo_player".split())
    controller = gtp_controller.Gtp_controller_protocol()
    controller.add_channel("sub", channel)

    proxy = gtp_proxy.Gtp_proxy('sub', controller)
    proxy.engine.add_command('mygenmove', handle_mygenmove)
    proxy.engine.add_command("mytest", handle_mytest)

    assert proxy.back_end_has_command("help")
    assert proxy.back_end_has_command("help")
    assert not proxy.back_end_has_command("nonex")

    is_error, response, end_session = proxy.engine.run_command(
        "mygenmove", ["b"])
    assert not is_error
    assert not end_session
    print response

    is_error, response, end_session = proxy.engine.run_command("showboard", [])
    assert not is_error
    assert not end_session
    print response

    gtp_engine.run_interactive_gtp_session(proxy.engine)


if __name__ == "__main__":
    main()

