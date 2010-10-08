"""Tests for playoffs.py"""

from __future__ import with_statement

import cPickle as pickle
from cStringIO import StringIO

from gomill import competitions
from gomill import playoffs
from gomill.gtp_games import Game_result
from gomill.game_jobs import Game_job, Game_job_result
from gomill.competitions import (
    Player_config, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.playoffs import Matchup_config

from gomill_tests import gomill_test_support
from gomill_tests import test_framework

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def get_screen_report(comp):
    """Retrieve a competition's screen report."""
    out = StringIO()
    comp.write_screen_report(out)
    return out.getvalue()

def check_screen_report(tc, comp, expected):
    """Check that a competition's screen report is as expected."""
    tc.assertMultiLineEqual(get_screen_report(comp), expected)

def fake_response(job, winner):
    """Produce a response for the specified job."""
    players = {'b' : job.player_b.code, 'w' : job.player_w.code}
    result = Game_result(players, winner)
    response = Game_job_result()
    response.game_id = job.game_id
    response.game_result = result
    response.engine_names = {}
    response.engine_descriptions = {}
    response.game_data = job.game_data
    return response

class Playoff_fixture(test_framework.Fixture):
    """Fixture setting up a Playoff.

    attributes:
      comp       -- Playoff

    """
    def __init__(self, tc, config=None):
        if config is None:
            config = default_config()
        self.tc = tc
        self.comp = playoffs.Playoff('testcomp')
        self.comp.initialise_from_control_file(config)
        self.comp.set_clean_status()

    def check_screen_report(self, expected):
        """Check that the screen report is as expected."""
        check_screen_report(self.tc, self.comp, expected)


def default_config():
    return {
        'players' : {
            't1' : Player_config("test1"),
            't2' : Player_config("test2"),
            },
        'board_size' : 13,
        'komi' : 7.5,
        'matchups' : [
            Matchup_config('t1', 't2', alternating=True),
            ],
        }


def test_basic_config(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'] = [
            Matchup_config(
                't1',  't2', board_size=9, komi=0.5, alternating=True,
                handicap=6, handicap_style='free',
                move_limit=50, scorer="internal", number_of_games=20),
            Matchup_config('t2', 't1', id='m1'),
            Matchup_config('t1', 't2'),
            ]
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
    comp = playoffs.Playoff('testcomp')
    config = default_config()
    config['board_size'] = 12
    config['handicap'] = 6
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertEqual(str(ar.exception),
                   "default fixed handicap out of range for board size 12")


def test_game_id_format(tc):
    config = default_config()
    config['matchups'][0] = Matchup_config('t1', 't2', number_of_games=1000)
    fx = Playoff_fixture(tc, config)
    tc.assertEqual(fx.comp.get_game().game_id, '0_000')


def test_play(tc):
    fx = Playoff_fixture(tc)

    job1 = fx.comp.get_game()
    tc.assertIsInstance(job1, Game_job)
    tc.assertEqual(job1.game_id, '0_0')
    tc.assertEqual(job1.player_b.code, 't1')
    tc.assertEqual(job1.player_w.code, 't2')
    tc.assertEqual(job1.board_size, 13)
    tc.assertEqual(job1.komi, 7.5)
    tc.assertEqual(job1.move_limit, 1000)
    tc.assertEqual(job1.game_data, ('0', 0))
    tc.assertIsNone(job1.sgf_filename)
    tc.assertIsNone(job1.sgf_dirname)
    tc.assertIsNone(job1.void_sgf_dirname)
    tc.assertEqual(job1.sgf_event, 'testcomp')
    tc.assertIsNone(job1.gtp_log_pathname)

    job2 = fx.comp.get_game()
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
    fx.comp.process_game_result(response1)

    fx.check_screen_report(
        "t1 v t2 (1 games)\n"
        "board size: 13   komi: 7.5\n"
        "     wins\n"
        "t1      1 100.00%   (black)\n"
        "t2      0   0.00%   (white)\n")

    tc.assertListEqual(fx.comp.get_matchup_results('0'), [('0_0', result1)])

def test_play_many(tc):
    fx = Playoff_fixture(tc)

    jobs = [fx.comp.get_game() for _ in range(8)]
    for i in [0, 3]:
        response = fake_response(jobs[i], 'b')
        fx.comp.process_game_result(response)
    jobs += [fx.comp.get_game() for _ in range(3)]
    for i in [4, 2, 6, 7]:
        response = fake_response(jobs[i], 'w')
        fx.comp.process_game_result(response)

    fx.check_screen_report(
        "t1 v t2 (6 games)\n"
        "board size: 13   komi: 7.5\n"
        "     wins              black        white\n"
        "t1      2 33.33%       1 25.00%     1 50.00%\n"
        "t2      4 66.67%       1 50.00%     3 75.00%\n"
        "                       2 33.33%     4 66.67%\n")

    tc.assertEqual(len(fx.comp.get_matchup_results('0')), 6)

    #tc.assertEqual(fx.comp.scheduler.allocators['0'].issued, 11)
    #tc.assertEqual(fx.comp.scheduler.allocators['0'].fixed, 6)

    comp2 = playoffs.Playoff('testcomp')
    comp2.initialise_from_control_file(default_config())
    status = pickle.loads(pickle.dumps(fx.comp.get_status()))
    comp2.set_status(status)

    #tc.assertEqual(comp2.scheduler.allocators['0'].issued, 6)
    #tc.assertEqual(comp2.scheduler.allocators['0'].fixed, 6)

    jobs2 = [comp2.get_game() for _ in range(4)]
    tc.assertListEqual([job.game_id for job in jobs2],
                       ['0_1', '0_5', '0_8', '0_9'])
    tc.assertEqual(len(comp2.get_matchup_results('0')), 6)
    check_screen_report(tc, comp2, get_screen_report(fx.comp))

def test_matchup_change(tc):
    fx = Playoff_fixture(tc)

    jobs = [fx.comp.get_game() for _ in range(8)]
    for i in [0, 2, 3, 4, 6, 7]:
        response = fake_response(jobs[i], ('b' if i in (0, 3) else 'w'))
        fx.comp.process_game_result(response)

    fx.check_screen_report(
        "t1 v t2 (6 games)\n"
        "board size: 13   komi: 7.5\n"
        "     wins              black        white\n"
        "t1      2 33.33%       1 25.00%     1 50.00%\n"
        "t2      4 66.67%       1 50.00%     3 75.00%\n"
        "                       2 33.33%     4 66.67%\n")

    config2 = default_config()
    config2['players']['t3'] = Player_config("test3")
    config2['matchups'][0] = Matchup_config('t1', 't3', alternating=True)
    comp2 = playoffs.Playoff('testcomp')
    comp2.initialise_from_control_file(config2)

    status = pickle.loads(pickle.dumps(fx.comp.get_status()))
    with tc.assertRaises(CompetitionError) as ar:
        comp2.set_status(status)
    tc.assertEqual(
        str(ar.exception),
        "existing results for matchup 0 are inconsistent with control file:\n"
        "result players are t1,t2;\n"
        "control file players are t1,t3")

