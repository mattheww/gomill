"""Tests for allplayalls.py"""

from gomill import competitions
from gomill import allplayalls
from gomill.competitions import (
    Player_config, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.allplayalls import Competitor_config

from gomill_tests import gomill_test_support
from gomill_tests import test_framework

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


class Allplayall_fixture(test_framework.Fixture):
    """Fixture setting up a Allplayall.

    attributes:
      comp       -- Allplayall

    """
    def __init__(self, tc, config=None):
        if config is None:
            config = default_config()
        self.tc = tc
        self.comp = allplayalls.Allplayall('testcomp')
        self.comp.initialise_from_control_file(config)
        self.comp.set_clean_status()

    def check_screen_report(self, expected):
        """Check that the screen report is as expected."""
        check_screen_report(self.tc, self.comp, expected)

    def check_short_report(self, *args, **kwargs):
        """Check that the short report is as expected."""
        check_short_report(self.tc, self.comp, *args, **kwargs)


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
            Competitor_config('t1'),
            Competitor_config('t2'),
            't3',
            ],
        }



def test_default_config(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    comp.initialise_from_control_file(config)
    tc.assertListEqual(comp.get_matchup_ids(),
                       ['AvB', 'AvC', 'BvC'])
    mBvC = comp.get_matchup('BvC')
    tc.assertEqual(mBvC.p1, 't2')
    tc.assertEqual(mBvC.p2, 't3')
    tc.assertEqual(mBvC.board_size, 13)
    tc.assertEqual(mBvC.komi, 7.5)
    tc.assertEqual(mBvC.move_limit, 1000)
    tc.assertEqual(mBvC.scorer, 'players')
    tc.assertEqual(mBvC.number_of_games, None)
    tc.assertIs(mBvC.alternating, True)
    tc.assertIs(mBvC.handicap, None)
    tc.assertEqual(mBvC.handicap_style, 'fixed')

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
    mBvC = comp.get_matchup('BvC')
    tc.assertEqual(mBvC.p1, 't2')
    tc.assertEqual(mBvC.p2, 't3')
    tc.assertEqual(mBvC.board_size, 9)
    tc.assertEqual(mBvC.komi, 0.5)
    tc.assertEqual(mBvC.move_limit, 200)
    tc.assertEqual(mBvC.scorer, 'internal')
    tc.assertEqual(mBvC.number_of_games, 20)
    tc.assertIs(mBvC.alternating, True)
    tc.assertIs(mBvC.handicap, None)
    tc.assertEqual(mBvC.handicap_style, 'fixed')

def test_duplicate_player(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    config['competitors'].append('t2')
    tc.assertRaisesRegexp(
        ControlFileError, "duplicate competitor: t2",
        comp.initialise_from_control_file, config)

def test_game_id_format(tc):
    config = default_config()
    config['number_of_games'] = 1000
    fx = Allplayall_fixture(tc, config)
    tc.assertEqual(fx.comp.get_game().game_id, 'AvB_000')
