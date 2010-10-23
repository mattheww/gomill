"""Test support code for testing Competitions and Ringmasters."""

from gomill import game_jobs
from gomill import gtp_games

def fake_response(job, winner):
    """Produce a response for the specified job.

    job      -- Game_job
    winner   -- winning colour (None for a jigo)

    The winning margin (if not a jigo) is 1.5.

    """
    players = {'b' : job.player_b.code, 'w' : job.player_w.code}
    result = gtp_games.Game_result(players, winner)
    response = game_jobs.Game_job_result()
    if winner is None:
        result.set_jigo()
    else:
        result.sgf_result += "1.5"
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

