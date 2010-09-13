import os

from gomill import competitions
cPlayer = competitions.Player_config

def test():
    comp = competitions.Competition('test')
    comp.set_base_directory("/base")
    config = {
        'players' : {
            't1' : cPlayer("test"),
            't2' : cPlayer("test", cwd="~/tmp/zzz"),
            't3' : cPlayer("test", cwd="rel/zzz"),
            't4' : cPlayer("test", cwd="."),
            }
        }
    comp.initialise_from_control_file(config)
    t1 = comp.players['t1']
    assert t1.cwd is None
    t2 = comp.players['t2']
    assert t2.cwd == os.path.expanduser("~") + "/tmp/zzz"
    t3 = comp.players['t3']
    assert t3.cwd == "/base/rel/zzz"
    t4 = comp.players['t4']
    print repr(t4.cwd)

if __name__ == "__main__":
    test()
