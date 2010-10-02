competition_type = 'playoff'

description = """\
gomill_tests playoff 'test1'.
"""

def gtp_test(**args):
    return Player("~/kiai/oneoffs/gtp_test_player",
                  environ={'PYTHONPATH' : '/home/mjw/kiai'},
                  stderr=DISCARD,
                  **args)

players = {
    'gtptest'  : gtp_test(),
    'failer'   : gtp_test(startup_gtp_commands=
                          ["gomill-delayed_error 9 protocol"]),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = "internal"

number_of_games = 400

matchups = [
    Matchup('failer',  'gtptest', handicap=6, handicap_style='fixed'),
    ]

