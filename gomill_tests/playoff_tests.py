"""Tests for playoffs.py"""

from gomill import competitions
from gomill import playoffs

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_basic_config(tc):
    Player_config = competitions.Player_config
    Matchup_config = playoffs.Matchup_config
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
            Matchup_config(
                't2',  't1'),
            ],
        }
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.matchups[0].p1, 't1')
    tc.assertEqual(comp.matchups[0].p2, 't2')
    tc.assertEqual(comp.matchups[0].board_size, 9)
    tc.assertEqual(comp.matchups[0].komi, 0.5)
    tc.assertIs(comp.matchups[0].alternating, True)
    tc.assertEqual(comp.matchups[0].handicap, 6)
    tc.assertEqual(comp.matchups[0].handicap_style, 'free')
    tc.assertEqual(comp.matchups[0].move_limit, 50)
    tc.assertEqual(comp.matchups[0].scorer, 'internal')
    tc.assertEqual(comp.matchups[0].number_of_games, 20)

    tc.assertEqual(comp.matchups[1].p1, 't2')
    tc.assertEqual(comp.matchups[1].p2, 't1')
    tc.assertEqual(comp.matchups[1].board_size, 13)
    tc.assertEqual(comp.matchups[1].komi, 7.5)
    tc.assertIs(comp.matchups[1].alternating, False)
    tc.assertEqual(comp.matchups[1].handicap, None)
    tc.assertEqual(comp.matchups[1].handicap_style, 'fixed')
    tc.assertEqual(comp.matchups[1].move_limit, 1000)
    tc.assertEqual(comp.matchups[1].scorer, 'players')
    tc.assertEqual(comp.matchups[1].number_of_games, None)

