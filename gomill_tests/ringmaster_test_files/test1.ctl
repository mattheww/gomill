competition_type = 'playoff'

description = """\
gomill_tests playoff 'test1'.
"""

players = {
    'gtptest'  : Player("test", stderr=DISCARD),
    'failer'   : Player("test fail=startup", stderr=DISCARD),
    }

move_limit = 400
record_games = False
board_size = 9
komi = 7.5
scorer = "internal"

number_of_games = 400

matchups = [
    Matchup('gtptest', 'failer', handicap=6, handicap_style='fixed'),
    ]

