"""Tests for competitions.py"""

import os

from gomill import competitions
from gomill.competitions import ControlFileError, Player_config

from gomill_tests import gomill_test_support

def make_tests(suite):
    suite.addTests(gomill_test_support.make_simple_tests(globals()))

def test_global_config(tc):
    comp = competitions.Competition('test')
    config = {
        'description' : "\nsome\ndescription  ",
        'players' : {},
        }
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.description, "some\ndescription")

def test_player_config(tc):
    comp = competitions.Competition('test')
    p1 = comp.game_jobs_player_from_config('pp', Player_config("cmd"))
    tc.assertEqual(p1.code, 'pp')
    tc.assertEqual(p1.cmd_args, ["cmd"])
    p2 = comp.game_jobs_player_from_config('pp', Player_config(command="cmd"))
    tc.assertEqual(p2.code, 'pp')
    tc.assertEqual(p2.cmd_args, ["cmd"])

    tc.assertRaisesRegexp(
        Exception, "'command' not specified",
        comp.game_jobs_player_from_config, 'pp',
        Player_config())
    tc.assertRaisesRegexp(
        Exception, "too many positional arguments",
        comp.game_jobs_player_from_config, 'pp',
        Player_config("cmd", "xxx"))
    tc.assertRaisesRegexp(
        Exception, "command specified as both positional and keyword argument",
        comp.game_jobs_player_from_config, 'pp',
        Player_config("cmd", command="cmd2"))
    tc.assertRaisesRegexp(
        Exception, "unknown argument 'unexpected'",
        comp.game_jobs_player_from_config, 'pp',
        Player_config("cmd", unexpected=3))

def test_bad_player(tc):
    comp = competitions.Competition('test')
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : None,
            }
        }
    tc.assertRaisesRegexp(
        ControlFileError, "'players': bad value for 't2': not a Player",
        comp.initialise_from_control_file, config)

def test_player_command(tc):
    comp = competitions.Competition('test')
    comp.set_base_directory("/base")
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("/bin/test foo"),
            't3' : Player_config(["bin/test", "foo"]),
            't4' : Player_config("~/test foo"),
            't5' : Player_config("~root"),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertEqual(comp.players['t1'].cmd_args, ["test"])
    tc.assertEqual(comp.players['t2'].cmd_args, ["/bin/test", "foo"])
    tc.assertEqual(comp.players['t3'].cmd_args, ["/base/bin/test", "foo"])
    tc.assertEqual(comp.players['t4'].cmd_args,
                   [os.path.expanduser("~") + "/test", "foo"])
    tc.assertEqual(comp.players['t5'].cmd_args, ["~root"])

def test_player_is_reliable_scorer(tc):
    comp = competitions.Competition('test')
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("test", is_reliable_scorer=False),
            't3' : Player_config("test", is_reliable_scorer=True),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertTrue(comp.players['t1'].is_reliable_scorer)
    tc.assertFalse(comp.players['t2'].is_reliable_scorer)
    tc.assertTrue(comp.players['t3'].is_reliable_scorer)

def test_player_cwd(tc):
    comp = competitions.Competition('test')
    comp.set_base_directory("/base")
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("test", cwd="/abs"),
            't3' : Player_config("test", cwd="rel/sub"),
            't4' : Player_config("test", cwd="."),
            't5' : Player_config("test", cwd="~/tmp/sub"),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertIsNone(comp.players['t1'].cwd)
    tc.assertEqual(comp.players['t2'].cwd, "/abs")
    tc.assertEqual(comp.players['t3'].cwd, "/base/rel/sub")
    tc.assertEqual(comp.players['t4'].cwd, "/base/.")
    tc.assertEqual(comp.players['t5'].cwd, os.path.expanduser("~") + "/tmp/sub")

def test_player_stderr(tc):
    comp = competitions.Competition('test')
    config = {
        'players' : {
            't1' : Player_config("test"),
            't2' : Player_config("test", discard_stderr=True),
            't3' : Player_config("test", discard_stderr=False),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertIs(comp.players['t1'].discard_stderr, False)
    tc.assertEqual(comp.players['t2'].discard_stderr, True)
    tc.assertIs(comp.players['t3'].discard_stderr, False)

def test_player_startup_gtp_commands(tc):
    comp = competitions.Competition('test')
    config = {
        'players' : {
            't1' : Player_config(
                "test", startup_gtp_commands=["foo"]),
            't2' : Player_config(
                "test", startup_gtp_commands=["foo bar baz"]),
            't3' : Player_config(
                "test", startup_gtp_commands=[["foo", "bar", "baz"]]),
            't4' : Player_config(
                "test", startup_gtp_commands=[
                    "xyzzy test",
                    ["foo", "bar", "baz"]]),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertListEqual(comp.players['t1'].startup_gtp_commands,
                       [("foo", [])])
    tc.assertListEqual(comp.players['t2'].startup_gtp_commands,
                       [("foo", ["bar", "baz"])])
    tc.assertListEqual(comp.players['t3'].startup_gtp_commands,
                       [("foo", ["bar", "baz"])])
    tc.assertListEqual(comp.players['t4'].startup_gtp_commands,
                       [("xyzzy", ["test"]),
                        ("foo", ["bar", "baz"])])

def test_player_gtp_aliases(tc):
    comp = competitions.Competition('test')
    config = {
        'players' : {
            't1' : Player_config(
                "test", gtp_aliases={'foo' : 'bar', 'baz' : 'quux'}),
            }
        }
    comp.initialise_from_control_file(config)
    tc.assertDictEqual(comp.players['t1'].gtp_aliases,
                       {'foo' : 'bar', 'baz' : 'quux'})

