"""Test support code for testing Competitions and Ringmasters."""

import cPickle as pickle
from cStringIO import StringIO

from gomill import game_jobs
from gomill import gtp_games

def fake_response(job, winner):
    """Produce a response for the specified job.

    job      -- Game_job
    winner   -- winning colour (None for a jigo, 'unknown' for unknown result)

    The winning margin (if not a jigo) is 1.5.

    """
    players = {'b' : job.player_b.code, 'w' : job.player_w.code}
    if winner == 'unknown':
        winner = None
        is_unknown = True
    else:
        is_unknown = False
    result = gtp_games.Game_result(players, winner)
    result.game_id = job.game_id
    if winner is None:
        if is_unknown:
            result.sgf_result = "Void"
            result.detail = "fake unknown result"
        else:
            result.set_jigo()
    else:
        result.sgf_result += "1.5"
    response = game_jobs.Game_job_result()
    response.game_id = job.game_id
    response.game_result = result
    response.engine_names = {
        job.player_b.code : '%s engine:v1.2.3' % job.player_b.code,
        job.player_w.code : '%s engine' % job.player_w.code,
        }
    response.engine_descriptions = {
        job.player_b.code : '%s engine:v1.2.3' % job.player_b.code,
        job.player_w.code : '%s engine\ntestdescription' % job.player_w.code,
        }
    response.game_data = job.game_data
    response.warnings = []
    response.log_entries = []
    return response

def get_screen_report(comp):
    """Retrieve a competition's screen report."""
    out = StringIO()
    comp.write_screen_report(out)
    return out.getvalue()

def get_short_report(comp):
    """Retrieve a competition's short report."""
    out = StringIO()
    comp.write_short_report(out)
    return out.getvalue()

def check_screen_report(tc, comp, expected):
    """Check that a competition's screen report is as expected."""
    tc.assertMultiLineEqual(get_screen_report(comp), expected)

def check_round_trip(tc, comp, config):
    """Check that a competition round-trips through saved state.

    Makes a new Competition, loads it from comp's saved state, and checks that
    the resulting screen report is identical.

    Returns the new Competition.

    """
    comp2 = comp.__class__(comp.competition_code)
    comp2.initialise_from_control_file(config)
    status = pickle.loads(pickle.dumps(comp.get_status()))
    comp2.set_status(status)
    check_screen_report(tc, comp2, get_screen_report(comp))
    return comp2
