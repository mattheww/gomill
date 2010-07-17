from gomill import gtp_engine
from gomill import gtp_controller
from gomill import gtp_proxy

def main():
    controller = gtp_controller.Gtp_controller_protocol()
    channel = gtp_controller.Subprocess_gtp_channel(
        "./player -m kiai.simple_montecarlo_player".split())
    controller.add_channel("sub", channel)

    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_controller(controller, 'sub')
    engine = proxy.make_engine()

    is_error, response, end_session = engine.run_command("showboard", [])
    assert not is_error
    assert not end_session
    print response

    gtp_engine.run_interactive_gtp_session(engine)

if __name__ == "__main__":
    main()

