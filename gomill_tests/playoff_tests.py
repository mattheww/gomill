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
            Matchup_config('t2', 't1', id='m1'),
            Matchup_config('t1', 't2'),
            ],
        }
    comp.initialise_from_control_file(config)
    m0 = comp.get_matchup('0')
    m1 = comp.get_matchup('m1')
    m2 = comp.get_matchup('2')

    tc.assertListEqual(comp.get_matchup_ids(), ['0', 'm1', '2'])
    tc.assertDictEqual(comp.get_matchups(), {'0' : m0, 'm1' : m1, '2' : m2})

    tc.assertEqual(m0.p1, 't1')
    tc.assertEqual(m0.p2, 't2')
    tc.assertEqual(m0.board_size, 9)
    tc.assertEqual(m0.komi, 0.5)
    tc.assertIs(m0.alternating, True)
    tc.assertEqual(m0.handicap, 6)
    tc.assertEqual(m0.handicap_style, 'free')
    tc.assertEqual(m0.move_limit, 50)
    tc.assertEqual(m0.scorer, 'internal')
    tc.assertEqual(m0.number_of_games, 20)

    tc.assertEqual(m1.p1, 't2')
    tc.assertEqual(m1.p2, 't1')
    tc.assertEqual(m1.board_size, 13)
    tc.assertEqual(m1.komi, 7.5)
    tc.assertIs(m1.alternating, False)
    tc.assertEqual(m1.handicap, None)
    tc.assertEqual(m1.handicap_style, 'fixed')
    tc.assertEqual(m1.move_limit, 1000)
    tc.assertEqual(m1.scorer, 'players')
    tc.assertEqual(m1.number_of_games, None)


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

