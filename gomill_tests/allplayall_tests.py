"""Tests for allplayalls.py"""

from gomill import competitions
from gomill import allplayalls
from gomill.competitions import (
    Player_config, NoGameAvailable, CompetitionError, ControlFileError)

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def default_config():
    return {
        'players' : {
            't1' : Player_config("test1"),
            't2' : Player_config("test2"),
            't3' : Player_config("test3"),
            },
        'board_size' : 13,
        'komi' : 7.5,
        'competitors' : [
            't1',
            't2',
            't3',
            ],
        }



def test_default_config(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    comp.initialise_from_control_file(config)
    tc.assertListEqual(comp.get_matchup_ids(),
                       ['0v1', '0v2', '1v0', '1v2', '2v0', '2v1'])
    m1v2 = comp.get_matchup('1v2')
    tc.assertEqual(m1v2.p1, 't2')
    tc.assertEqual(m1v2.p2, 't3')
    tc.assertEqual(m1v2.board_size, 13)
    tc.assertEqual(m1v2.komi, 7.5)
    tc.assertEqual(m1v2.move_limit, 1000)
    tc.assertEqual(m1v2.scorer, 'players')
    tc.assertEqual(m1v2.number_of_games, None)
    tc.assertIs(m1v2.alternating, True)
    tc.assertIs(m1v2.handicap, None)
    tc.assertEqual(m1v2.handicap_style, 'fixed')

def test_basic_config(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    config['description'] = "default\nconfig"
    config['board_size'] = 9
    config['komi'] = 0.5
    config['move_limit'] = 200
    config['scorer'] = 'internal'
    config['number_of_games'] = 20
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.description, "default\nconfig")
    m1v2 = comp.get_matchup('1v2')
    tc.assertEqual(m1v2.p1, 't2')
    tc.assertEqual(m1v2.p2, 't3')
    tc.assertEqual(m1v2.board_size, 9)
    tc.assertEqual(m1v2.komi, 0.5)
    tc.assertEqual(m1v2.move_limit, 200)
    tc.assertEqual(m1v2.scorer, 'internal')
    tc.assertEqual(m1v2.number_of_games, 20)
    tc.assertIs(m1v2.alternating, True)
    tc.assertIs(m1v2.handicap, None)
    tc.assertEqual(m1v2.handicap_style, 'fixed')

