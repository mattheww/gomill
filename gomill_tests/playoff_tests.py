"""Tests for playoffs.py"""

from __future__ import with_statement

from cStringIO import StringIO

from gomill import competitions
from gomill import playoffs
from gomill.gtp_games import Game_result
from gomill.game_jobs import Game_job, Game_job_result
from gomill.competitions import (Player_config, ControlFileError,
                                 NoGameAvailable)
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


def test_play(tc):
    comp = playoffs.Playoff('testcomp')
    config = {
        'players' : {
            't1' : Player_config("test1"),
            't2' : Player_config("test2"),
            },
        'board_size' : 12,
        'komi' : 3.5,
        'matchups' : [
            Matchup_config('t1', 't2', alternating=True),
            ],
        }
    comp.initialise_from_control_file(config)
    comp.set_clean_status()

    job1 = comp.get_game()
    tc.assertIsInstance(job1, Game_job)
    tc.assertEqual(job1.game_id, '0_0')
    tc.assertEqual(job1.player_b.code, 't1')
    tc.assertEqual(job1.player_w.code, 't2')
    tc.assertEqual(job1.board_size, 12)
    tc.assertEqual(job1.komi, 3.5)
    tc.assertEqual(job1.move_limit, 1000)
    tc.assertEqual(job1.game_data, ('0', 0))
    tc.assertIsNone(job1.sgf_filename)
    tc.assertIsNone(job1.sgf_dirname)
    tc.assertIsNone(job1.void_sgf_dirname)
    tc.assertEqual(job1.sgf_event, 'testcomp')
    tc.assertIsNone(job1.gtp_log_pathname)

    job2 = comp.get_game()
    tc.assertIsInstance(job2, Game_job)
    tc.assertEqual(job2.game_id, '0_1')
    tc.assertEqual(job2.player_b.code, 't2')
    tc.assertEqual(job2.player_w.code, 't1')

    result1 = Game_result({'b' : 't1', 'w' : 't2'}, 'b')
    result1.sgf_result = "B+8.5"
    response1 = Game_job_result()
    response1.game_id = job1.game_id
    response1.game_result = result1
    response1.engine_names = {}
    response1.engine_descriptions = {}
    response1.game_data = job1.game_data
    comp.process_game_result(response1)

    out = StringIO()
    comp.write_screen_report(out)
    tc.assertMultiLineEqual(
        out.getvalue(),
        "t1 v t2 (1 games)\n"
        "board size: 12   komi: 3.5\n"
        "     wins\n"
        "t1      1 100.00%   (black)\n"
        "t2      0   0.00%   (white)\n")

    tc.assertListEqual(comp.get_matchup_results('0'), [('0_0', result1)])

def test_game_id_format(tc):
    comp = playoffs.Playoff('testcomp')
    config = {
        'players' : {
            't1' : Player_config("test1"),
            },
        'board_size' : 12,
        'komi' : 3.5,
        'matchups' : [
            Matchup_config('t1', 't1', number_of_games=1000),
            ],
        }
    comp.initialise_from_control_file(config)
    comp.set_clean_status()
    tc.assertEqual(comp.get_game().game_id, '0_000')
