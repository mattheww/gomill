from gomill import gtp_engine
from gomill import gtp_controller
from gomill import gtp_proxy
from gomill.gtp_proxy import BackEndError

def handle_mytest(args):
    return "mytest: %s" % ",".join(args)

def test_communication_failure():
    proxy = gtp_proxy.Gtp_proxy()
    proxy.set_back_end_subprocess(
        "./player -m kiai.simple_montecarlo_player".split())

    assert proxy.pass_command("quit", []) == ""

    print "==="
    try:
        print proxy.pass_command("showboard", [])
    except BackEndError, e:
        print e
    else:
        raise AssertionError("no error talking to closed subprocess")

    is_error, response, end_session = proxy.engine.run_command("showboard", [])
    assert is_error
    print "==="
    print response
    print "==="


def test_general():
    def handle_mygenmove(args):
        return (proxy.pass_command('genmove', args) + "\n" +
                proxy.pass_command('gomill-explain_last_move', []))

    proxy = gtp_proxy.Gtp_proxy()
    # May raise BackEndError
    proxy.set_back_end_subprocess(
        "./player -m kiai.simple_montecarlo_player".split())
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

    assert (proxy.engine.handle_line(
            "gomill-passthrough known_command gomill-passthrough") ==
            ('= false\n\n', False))

def test_interatctive():
    def handle_mygenmove(args):
        return (proxy.pass_command('genmove', args) + "\n" +
                proxy.pass_command('gomill-explain_last_move', []))

    proxy = gtp_proxy.Gtp_proxy()
    # May raise BackEndError
    proxy.set_back_end_subprocess(
        "./player -m kiai.simple_montecarlo_player".split())
    proxy.engine.add_command('mygenmove', handle_mygenmove)
    proxy.engine.add_command("mytest", handle_mytest)
    gtp_engine.run_interactive_gtp_session(proxy.engine)


def test():
    test_communication_failure()
    test_general()
    #test_interactive()

if __name__ == "__main__":
    test()

