"""Tests for playoffs.py"""

from __future__ import with_statement

from textwrap import dedent
import cPickle as pickle

from gomill import competitions
from gomill import playoffs
from gomill.gtp_games import Game_result
from gomill.game_jobs import Game_job, Game_job_result
from gomill.competitions import (
    Player_config, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.playoffs import Matchup_config

from gomill_tests import competition_test_support
from gomill_tests import gomill_test_support
from gomill_tests import test_framework
from gomill_tests.competition_test_support import (
    fake_response, check_screen_report)

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))


def check_short_report(tc, comp, expected_matchups, expected_players,
                       competition_name="testcomp"):
    """Check that a playoff's short report is as expected."""
    expected = ("playoff: %s\n\n%s\n%s\n" %
                (competition_name, expected_matchups, expected_players))
    tc.assertMultiLineEqual(competition_test_support.get_short_report(comp),
                            expected)

expected_fake_players = dedent("""\
    player t1: t1 engine
    testdescription
    player t2: t2 engine:v1.2.3
    """)


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

    def check_short_report(self, *args, **kwargs):
        """Check that the short report is as expected."""
        check_short_report(self.tc, self.comp, *args, **kwargs)


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
    config['description'] = "default\nconfig"
    config['matchups'] = [
            Matchup_config(
                't1',  't2', board_size=9, komi=0.5, alternating=True,
                handicap=6, handicap_style='free',
                move_limit=50,
                scorer="internal", internal_scorer_handicap_compensation='no',
                number_of_games=20),
            Matchup_config('t2', 't1', id='m1'),
            Matchup_config('t1', 't2'),
            ]
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.description, "default\nconfig")

    comp.set_clean_status()
    tr = comp.get_tournament_results()
    m0 = tr.get_matchup('0')
    m1 = tr.get_matchup('m1')
    m2 = tr.get_matchup('2')

    tc.assertListEqual(tr.get_matchup_ids(), ['0', 'm1', '2'])
    tc.assertDictEqual(tr.get_matchups(), {'0' : m0, 'm1' : m1, '2' : m2})

    tc.assertEqual(m0.player_1, 't1')
    tc.assertEqual(m0.player_2, 't2')
    tc.assertEqual(m0.board_size, 9)
    tc.assertEqual(m0.komi, 0.5)
    tc.assertIs(m0.alternating, True)
    tc.assertEqual(m0.handicap, 6)
    tc.assertEqual(m0.handicap_style, 'free')
    tc.assertEqual(m0.move_limit, 50)
    tc.assertEqual(m0.scorer, 'internal')
    tc.assertEqual(m0.internal_scorer_handicap_compensation, 'no')
    tc.assertEqual(m0.number_of_games, 20)

    tc.assertEqual(m1.player_1, 't2')
    tc.assertEqual(m1.player_2, 't1')
    tc.assertEqual(m1.board_size, 13)
    tc.assertEqual(m1.komi, 7.5)
    tc.assertIs(m1.alternating, False)
    tc.assertEqual(m1.handicap, None)
    tc.assertEqual(m1.handicap_style, 'fixed')
    tc.assertEqual(m1.move_limit, 1000)
    tc.assertEqual(m1.scorer, 'players')
    tc.assertEqual(m1.internal_scorer_handicap_compensation, 'full')
    tc.assertEqual(m1.number_of_games, None)

def test_nonsense_matchup_config(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(99)
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    'matchups': item 1: not a Matchup"""))

def test_bad_matchup_config(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(Matchup_config())
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 1: not enough arguments"""))

def test_bad_matchup_config_bad_id(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(Matchup_config('t1', 't2', id=99))
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 1: 'id': not a string"""))

def test_bad_matchup_config_bad_setting(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(Matchup_config('t1', 't2', board_size="X"))
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 1: 'board_size': invalid integer"""))

def test_bad_matchup_config_unknown_player(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(Matchup_config('t1', 'nonex'))
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 1: unknown player nonex"""))

def test_bad_matchup_config_no_board_size(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    del config['board_size']
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 0: 'board_size' not specified"""))

def test_bad_matchup_config_bad_handicap(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'].append(Matchup_config('t1', 't2', handicap=10))
    with tc.assertRaises(ControlFileError) as ar:
        comp.initialise_from_control_file(config)
    tc.assertMultiLineEqual(str(ar.exception), dedent("""\
    matchup 1: fixed handicap out of range for board size 13"""))

def test_matchup_config_board_size_in_matchup_only(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    del config['board_size']
    config['matchups'] = [Matchup_config('t1', 't2', alternating=True,
                                         board_size=9)]
    comp.initialise_from_control_file(config)
    comp.set_clean_status()
    tr = comp.get_tournament_results()
    m0 = tr.get_matchup('0')
    tc.assertEqual(m0.board_size, 9)

def test_matchup_name(tc):
    comp = playoffs.Playoff('test')
    config = default_config()
    config['matchups'] = [Matchup_config('t1', 't2', name="asd")]
    comp.initialise_from_control_file(config)
    comp.set_clean_status()
    tr = comp.get_tournament_results()
    m0 = tr.get_matchup('0')
    tc.assertEqual(m0.name, "asd")

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

def test_get_player_checks(tc):
    comp = playoffs.Playoff('testcomp')
    config = default_config()
    config['players']['t3'] = Player_config("test3")
    config['matchups'].append(
        Matchup_config('t1', 't3', number_of_games=0),
        ),
    comp.initialise_from_control_file(config)
    checks = comp.get_player_checks()
    tc.assertEqual(len(checks), 2)
    tc.assertEqual(checks[0].board_size, 13)
    tc.assertEqual(checks[0].komi, 7.5)
    tc.assertEqual(checks[0].player.code, "t1")
    tc.assertEqual(checks[0].player.cmd_args, ['test1'])
    tc.assertEqual(checks[1].player.code, "t2")
    tc.assertEqual(checks[1].player.cmd_args, ['test2'])

def test_play(tc):
    fx = Playoff_fixture(tc)
    tc.assertIsNone(fx.comp.description)

    job1 = fx.comp.get_game()
    tc.assertIsInstance(job1, Game_job)
    tc.assertEqual(job1.game_id, '0_0')
    tc.assertEqual(job1.player_b.code, 't1')
    tc.assertEqual(job1.player_w.code, 't2')
    tc.assertEqual(job1.board_size, 13)
    tc.assertEqual(job1.komi, 7.5)
    tc.assertEqual(job1.move_limit, 1000)
    tc.assertIs(job1.use_internal_scorer, False)
    tc.assertEqual(job1.internal_scorer_handicap_compensation, 'full')
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
    response1.engine_names = {
        't1' : 't1 engine:v1.2.3',
        't2' : 't2 engine',
        }
    response1.engine_descriptions = {
        't1' : 't1 engine:v1.2.3',
        't2' : 't2 engine\ntest \xc2\xa3description',
        }
    response1.game_data = job1.game_data
    fx.comp.process_game_result(response1)

    expected_report = dedent("""\
    t1 v t2 (1 games)
    board size: 13   komi: 7.5
         wins
    t1      1 100.00%   (black)
    t2      0   0.00%   (white)
    """)
    expected_players = dedent("""\
    player t1: t1 engine:v1.2.3
    player t2: t2 engine
    test \xc2\xa3description
    """)
    fx.check_screen_report(expected_report)
    fx.check_short_report(expected_report, expected_players)

    tc.assertListEqual(
        fx.comp.get_tournament_results().get_matchup_results('0'), [result1])

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

    fx.check_screen_report(dedent("""\
    t1 v t2 (6 games)
    board size: 13   komi: 7.5
         wins              black        white
    t1      2 33.33%       1 25.00%     1 50.00%
    t2      4 66.67%       1 50.00%     3 75.00%
                           2 33.33%     4 66.67%
    """))

    tc.assertEqual(
        len(fx.comp.get_tournament_results().get_matchup_results('0')), 6)

    #tc.assertEqual(fx.comp.scheduler.allocators['0'].issued, 11)
    #tc.assertEqual(fx.comp.scheduler.allocators['0'].fixed, 6)

    comp2 = competition_test_support.check_round_trip(
        tc, fx.comp, default_config())

    #tc.assertEqual(comp2.scheduler.allocators['0'].issued, 6)
    #tc.assertEqual(comp2.scheduler.allocators['0'].fixed, 6)

    jobs2 = [comp2.get_game() for _ in range(4)]
    tc.assertListEqual([job.game_id for job in jobs2],
                       ['0_1', '0_5', '0_8', '0_9'])
    tr = comp2.get_tournament_results()
    tc.assertEqual(len(tr.get_matchup_results('0')), 6)
    ms = tr.get_matchup_stats('0')
    tc.assertEqual(ms.total, 6)
    tc.assertEqual(ms.wins_1, 2)
    tc.assertEqual(ms.wins_b, 2)

def test_jigo_reporting(tc):
    fx = Playoff_fixture(tc)

    def winner(i):
        if i in (0, 3):
            return 'b'
        elif i in (2, 4):
            return 'w'
        else:
            return None
    jobs = [fx.comp.get_game() for _ in range(8)]
    for i in range(6):
        response = fake_response(jobs[i], winner(i))
        fx.comp.process_game_result(response)
    fx.check_screen_report(dedent("""\
    t1 v t2 (6 games)
    board size: 13   komi: 7.5
         wins              black        white
    t1      2 33.33%       2 66.67%     1  33.33%
    t2      4 66.67%       2 66.67%     3 100.00%
                           3 50.00%     3  50.00%
    """))

    response = fake_response(jobs[6], None)
    fx.comp.process_game_result(response)
    fx.check_screen_report(dedent("""\
    t1 v t2 (7 games)
    board size: 13   komi: 7.5
         wins              black          white
    t1    2.5 35.71%       2.5 62.50%     1.5 50.00%
    t2    4.5 64.29%       2.5 83.33%     3.5 87.50%
                           3.5 50.00%     3.5 50.00%
    """))

def test_unknown_result_reporting(tc):
    fx = Playoff_fixture(tc)

    def winner(i):
        if i in (0, 3):
            return 'b'
        elif i in (2, 4):
            return 'w'
        else:
            return 'unknown'
    jobs = [fx.comp.get_game() for _ in range(8)]
    for i in range(6):
        response = fake_response(jobs[i], winner(i))
        fx.comp.process_game_result(response)
    fx.check_screen_report(dedent("""\
    t1 v t2 (6 games)
    unknown results: 2 33.33%
    board size: 13   komi: 7.5
         wins              black        white
    t1      1 16.67%       1 33.33%     0  0.00%
    t2      3 50.00%       1 33.33%     2 66.67%
                           2 33.33%     2 33.33%
    """))

def test_self_play(tc):
    config = default_config()
    config['matchups'] = [
        Matchup_config('t1', 't1', alternating=True),
        Matchup_config('t1', 't1', alternating=False),
        ]
    fx = Playoff_fixture(tc, config)

    jobs = [fx.comp.get_game() for _ in range(20)]
    for i, job in enumerate(jobs):
        response = fake_response(job, 'b' if i < 9 else 'w')
        fx.comp.process_game_result(response)
    fx.check_screen_report(dedent("""\
    t1 v t1#2 (10 games)
    board size: 13   komi: 7.5
           wins              black        white
    t1        6 60.00%       3 60.00%     3 60.00%
    t1#2      4 40.00%       2 40.00%     2 40.00%
                             5 50.00%     5 50.00%

    t1 v t1#2 (10 games)
    board size: 13   komi: 7.5
           wins
    t1        4 40.00%   (black)
    t1#2      6 60.00%   (white)
    """))

    competition_test_support.check_round_trip(tc, fx.comp, config)


def test_bad_state(tc):
    fx = Playoff_fixture(tc)
    bad_status = fx.comp.get_status()
    del bad_status['scheduler']

    comp2 = playoffs.Playoff('testcomp')
    comp2.initialise_from_control_file(default_config())
    tc.assertRaises(KeyError, comp2.set_status, bad_status)

def test_matchup_change(tc):
    fx = Playoff_fixture(tc)

    jobs = [fx.comp.get_game() for _ in range(8)]
    for i in [0, 2, 3, 4, 6, 7]:
        response = fake_response(jobs[i], ('b' if i in (0, 3) else 'w'))
        fx.comp.process_game_result(response)

    fx.check_screen_report(dedent("""\
    t1 v t2 (6 games)
    board size: 13   komi: 7.5
         wins              black        white
    t1      2 33.33%       1 25.00%     1 50.00%
    t2      4 66.67%       1 50.00%     3 75.00%
                           2 33.33%     4 66.67%
    """))

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

def test_matchup_reappearance(tc):
    # Test that if a matchup is removed and added again, we remember the game
    # number. Test that we report the 'ghost' matchup in the short report (but
    # not the screen report).
    config1 = default_config()
    config1['matchups'].append(Matchup_config('t2', 't1'))
    config2 = default_config()
    config3 = default_config()
    config3['matchups'].append(Matchup_config('t2', 't1'))

    comp1 = playoffs.Playoff('testcomp')
    comp1.initialise_from_control_file(config1)
    comp1.set_clean_status()
    jobs1 = [comp1.get_game() for _ in range(8)]
    for job in jobs1:
        comp1.process_game_result(fake_response(job, 'b'))
    tc.assertListEqual(
        [job.game_id for job in jobs1],
        ['0_0', '1_0', '0_1', '1_1', '0_2', '1_2', '0_3', '1_3'])
    expected_matchups_1 = dedent("""\
    t1 v t2 (4 games)
    board size: 13   komi: 7.5
         wins              black         white
    t1      2 50.00%       2 100.00%     0 0.00%
    t2      2 50.00%       2 100.00%     0 0.00%
                           4 100.00%     0 0.00%

    t2 v t1 (4 games)
    board size: 13   komi: 7.5
         wins
    t2      4 100.00%   (black)
    t1      0   0.00%   (white)
    """)
    check_screen_report(tc, comp1, expected_matchups_1)
    check_short_report(tc, comp1, expected_matchups_1, expected_fake_players)

    comp2 = playoffs.Playoff('testcomp')
    comp2.initialise_from_control_file(config2)
    comp2.set_status(pickle.loads(pickle.dumps(comp1.get_status())))
    jobs2 = [comp2.get_game() for _ in range(4)]
    tc.assertListEqual(
        [job.game_id for job in jobs2],
        ['0_4', '0_5', '0_6', '0_7'])
    for job in jobs2:
        comp2.process_game_result(fake_response(job, 'b'))
    expected_matchups_2 = dedent("""\
    t1 v t2 (8 games)
    board size: 13   komi: 7.5
         wins              black         white
    t1      4 50.00%       4 100.00%     0 0.00%
    t2      4 50.00%       4 100.00%     0 0.00%
                           8 100.00%     0 0.00%
    """)
    check_screen_report(tc, comp2, expected_matchups_2)
    expected_matchups_2b = dedent("""\
    t2 v t1 (4 games)
    ?? (missing from control file)
         wins
    t2      4 100.00%   (black)
    t1      0   0.00%   (white)
    """)
    check_short_report(
        tc, comp2,
        expected_matchups_2 + "\n" + expected_matchups_2b,
        expected_fake_players)

    comp3 = playoffs.Playoff('testcomp')
    comp3.initialise_from_control_file(config3)
    comp3.set_status(pickle.loads(pickle.dumps(comp2.get_status())))
    jobs3 = [comp3.get_game() for _ in range(8)]
    tc.assertListEqual(
        [job.game_id for job in jobs3],
        ['1_4', '1_5', '1_6', '1_7', '0_8', '1_8', '0_9', '1_9'])
    expected_matchups_3 = dedent("""\
    t1 v t2 (8 games)
    board size: 13   komi: 7.5
         wins              black         white
    t1      4 50.00%       4 100.00%     0 0.00%
    t2      4 50.00%       4 100.00%     0 0.00%
                           8 100.00%     0 0.00%

    t2 v t1 (4 games)
    board size: 13   komi: 7.5
         wins
    t2      4 100.00%   (black)
    t1      0   0.00%   (white)
    """)
    check_screen_report(tc, comp3, expected_matchups_3)
    check_short_report(tc, comp3, expected_matchups_3, expected_fake_players)

