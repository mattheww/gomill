"""Tests for allplayalls.py"""

from __future__ import with_statement

from textwrap import dedent
import cPickle as pickle

from gomill import competitions
from gomill import allplayalls
from gomill.gtp_games import Game_result
from gomill.game_jobs import Game_job, Game_job_result
from gomill.competitions import (
    Player_config, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.allplayalls import Competitor_config

from gomill_tests import competition_test_support
from gomill_tests import gomill_test_support
from gomill_tests import test_framework
from gomill_tests.competition_test_support import (
    fake_response, check_screen_report)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def check_short_report(tc, comp,
                       expected_grid, expected_matchups, expected_players,
                       competition_name="testcomp"):
    """Check that an allplayall's short report is as expected."""
    expected = ("allplayall: %s\n\n%s\n%s\n%s\n" %
                (competition_name, expected_grid,
                 expected_matchups, expected_players))
    tc.assertMultiLineEqual(competition_test_support.get_short_report(comp),
                            expected)

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
    comp.set_clean_status()
    tr = comp.get_tournament_results()
    tc.assertListEqual(tr.get_matchup_ids(), ['AvB', 'AvC', 'BvC'])
    mBvC = tr.get_matchup('BvC')
    tc.assertEqual(mBvC.player_1, 't2')
    tc.assertEqual(mBvC.player_2, 't3')
    tc.assertEqual(mBvC.board_size, 13)
    tc.assertEqual(mBvC.komi, 7.5)
    tc.assertEqual(mBvC.move_limit, 1000)
    tc.assertEqual(mBvC.scorer, 'players')
    tc.assertEqual(mBvC.internal_scorer_handicap_compensation, 'full')
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
    config['internal_scorer_handicap_compensation'] = 'short'
    config['rounds'] = 20
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.description, "default\nconfig")
    comp.set_clean_status()
    mBvC = comp.get_tournament_results().get_matchup('BvC')
    tc.assertEqual(mBvC.player_1, 't2')
    tc.assertEqual(mBvC.player_2, 't3')
    tc.assertEqual(mBvC.board_size, 9)
    tc.assertEqual(mBvC.komi, 0.5)
    tc.assertEqual(mBvC.move_limit, 200)
    tc.assertEqual(mBvC.scorer, 'internal')
    tc.assertEqual(mBvC.internal_scorer_handicap_compensation, 'short')
    tc.assertEqual(mBvC.number_of_games, 20)
    tc.assertIs(mBvC.alternating, True)
    tc.assertIs(mBvC.handicap, None)
    tc.assertEqual(mBvC.handicap_style, 'fixed')

def test_unknown_player(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    config['competitors'].append('nonex')
    tc.assertRaisesRegexp(
        ControlFileError, "competitor nonex: unknown player",
        comp.initialise_from_control_file, config)

def test_duplicate_player(tc):
    comp = allplayalls.Allplayall('test')
    config = default_config()
    config['competitors'].append('t2')
    tc.assertRaisesRegexp(
        ControlFileError, "duplicate competitor: t2",
        comp.initialise_from_control_file, config)

def test_game_id_format(tc):
    config = default_config()
    config['rounds'] = 1000
    fx = Allplayall_fixture(tc, config)
    tc.assertEqual(fx.comp.get_game().game_id, 'AvB_000')

def test_get_player_checks(tc):
    fx = Allplayall_fixture(tc)
    checks = fx.comp.get_player_checks()
    tc.assertEqual(len(checks), 3)
    tc.assertEqual(checks[0].board_size, 13)
    tc.assertEqual(checks[0].komi, 7.5)
    tc.assertEqual(checks[0].player.code, "t1")
    tc.assertEqual(checks[0].player.cmd_args, ['test1'])
    tc.assertEqual(checks[1].player.code, "t2")
    tc.assertEqual(checks[1].player.cmd_args, ['test2'])
    tc.assertEqual(checks[2].player.code, "t3")
    tc.assertEqual(checks[2].player.cmd_args, ['test3'])

def test_play(tc):
    fx = Allplayall_fixture(tc)
    tc.assertIsNone(fx.comp.description)

    job1 = fx.comp.get_game()
    tc.assertIsInstance(job1, Game_job)
    tc.assertEqual(job1.game_id, 'AvB_0')
    tc.assertEqual(job1.player_b.code, 't1')
    tc.assertEqual(job1.player_w.code, 't2')
    tc.assertEqual(job1.board_size, 13)
    tc.assertEqual(job1.komi, 7.5)
    tc.assertEqual(job1.move_limit, 1000)
    tc.assertIs(job1.use_internal_scorer, False)
    tc.assertEqual(job1.internal_scorer_handicap_compensation, 'full')
    tc.assertEqual(job1.game_data, ('AvB', 0))
    tc.assertIsNone(job1.sgf_filename)
    tc.assertIsNone(job1.sgf_dirname)
    tc.assertIsNone(job1.void_sgf_dirname)
    tc.assertEqual(job1.sgf_event, 'testcomp')
    tc.assertIsNone(job1.gtp_log_pathname)

    job2 = fx.comp.get_game()
    tc.assertIsInstance(job2, Game_job)
    tc.assertEqual(job2.game_id, 'AvC_0')
    tc.assertEqual(job2.player_b.code, 't1')
    tc.assertEqual(job2.player_w.code, 't3')

    response1 = fake_response(job1, 'b')
    fx.comp.process_game_result(response1)
    response2 = fake_response(job2, None)
    fx.comp.process_game_result(response2)

    expected_grid = dedent("""\
    2 games played

          A       B   C
    A t1         1-0 0.5-0.5
    B t2 0-1         0-0
    C t3 0.5-0.5 0-0
    """)
    expected_matchups = dedent("""\
    t1 v t2 (1 games)
    board size: 13   komi: 7.5
         wins
    t1      1 100.00%   (black)
    t2      0   0.00%   (white)

    t1 v t3 (1 games)
    board size: 13   komi: 7.5
         wins
    t1    0.5 50.00%   (black)
    t3    0.5 50.00%   (white)
    """)
    expected_players = dedent("""\
    player t1: t1 engine:v1.2.3
    player t2: t2 engine
    testdescription
    player t3: t3 engine
    testdescription
    """)
    fx.check_screen_report(expected_grid)
    fx.check_short_report(expected_grid, expected_matchups, expected_players)

    avb_results = fx.comp.get_tournament_results().get_matchup_results('AvB')
    tc.assertEqual(avb_results, [response1.game_result])

def test_play_many(tc):
    config = default_config()
    config['rounds'] = 30
    fx = Allplayall_fixture(tc, config)

    jobs = [fx.comp.get_game() for _ in xrange(57)]
    for i in xrange(57):
        response = fake_response(jobs[i], 'b')
        fx.comp.process_game_result(response)

    fx.check_screen_report(dedent("""\
    57/90 games played

          A    B    C
    A t1      10-9 10-9
    B t2 9-10      10-9
    C t3 9-10 9-10
    """))

    tc.assertEqual(
        len(fx.comp.get_tournament_results().get_matchup_results('AvB')), 19)

    comp2 = competition_test_support.check_round_trip(tc, fx.comp, config)
    jobs2 = [comp2.get_game() for _ in range(4)]
    tc.assertListEqual([job.game_id for job in jobs2],
                       ['AvB_19', 'AvC_19', 'BvC_19', 'AvB_20'])
    tr = comp2.get_tournament_results()
    tc.assertEqual(len(tr.get_matchup_results('AvB')), 19)
    ms = tr.get_matchup_stats('AvB')
    tc.assertEqual(ms.total, 19)
    tc.assertEqual(ms.wins_1, 10)
    tc.assertIs(ms.alternating, True)

def test_competitor_change(tc):
    fx = Allplayall_fixture(tc)
    status = pickle.loads(pickle.dumps(fx.comp.get_status()))

    config2 = default_config()
    del config2['competitors'][2]
    comp2 = allplayalls.Allplayall('testcomp')
    comp2.initialise_from_control_file(config2)
    with tc.assertRaises(CompetitionError) as ar:
        comp2.set_status(status)
    tc.assertEqual(
        str(ar.exception),
        "competitor has been removed from control file")

    config3 = default_config()
    config3['players']['t4'] = Player_config("test4")
    config3['competitors'][2] = 't4'
    comp3 = allplayalls.Allplayall('testcomp')
    comp3.initialise_from_control_file(config3)
    with tc.assertRaises(CompetitionError) as ar:
        comp3.set_status(status)
    tc.assertEqual(
        str(ar.exception),
        "competitors have changed in the control file")

    config4 = default_config()
    config4['players']['t4'] = Player_config("test4")
    config4['competitors'].append('t4')
    comp4 = allplayalls.Allplayall('testcomp')
    comp4.initialise_from_control_file(config4)
    comp4.set_status(status)

