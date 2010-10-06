"""Tests for playoffs.py"""

from gomill import competitions
from gomill import playoffs
from gomill.competitions import Player_config, ControlFileError
from gomill.playoffs import Matchup_config

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_basic_config(tc):
    comp = playoffs.Playoff('test')
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("test"),
            },
        'board_size' : 13,
        'komi' : 7.5,
        'matchups' : [
            Matchup_config(
                't1',  't2', board_size=9, komi=0.5, alternating=True,
                handicap=6, handicap_style='free',
                move_limit=50, scorer="internal", number_of_games=20),
            Matchup_config('t2',  't1', id='simple',),
            ],
        }
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.matchups['0'].p1, 't1')
    tc.assertEqual(comp.matchups['0'].p2, 't2')
    tc.assertEqual(comp.matchups['0'].board_size, 9)
    tc.assertEqual(comp.matchups['0'].komi, 0.5)
    tc.assertIs(comp.matchups['0'].alternating, True)
    tc.assertEqual(comp.matchups['0'].handicap, 6)
    tc.assertEqual(comp.matchups['0'].handicap_style, 'free')
    tc.assertEqual(comp.matchups['0'].move_limit, 50)
    tc.assertEqual(comp.matchups['0'].scorer, 'internal')
    tc.assertEqual(comp.matchups['0'].number_of_games, 20)

    tc.assertEqual(comp.matchups['simple'].p1, 't2')
    tc.assertEqual(comp.matchups['simple'].p2, 't1')
    tc.assertEqual(comp.matchups['simple'].board_size, 13)
    tc.assertEqual(comp.matchups['simple'].komi, 7.5)
    tc.assertIs(comp.matchups['simple'].alternating, False)
    tc.assertEqual(comp.matchups['simple'].handicap, None)
    tc.assertEqual(comp.matchups['simple'].handicap_style, 'fixed')
    tc.assertEqual(comp.matchups['simple'].move_limit, 1000)
    tc.assertEqual(comp.matchups['simple'].scorer, 'players')
    tc.assertEqual(comp.matchups['simple'].number_of_games, None)

def test_global_handicap_validation(tc):
    comp = playoffs.Playoff('test')
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("test"),
            },
        'board_size' : 12,
        'handicap' : 6,
        'komi' : 7.5,
        'matchups' : [
            Matchup_config('t1',  't2'),
            ],
        }
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertEqual(str(ar.exception),
                   "default fixed handicap out of range for board size 12")

