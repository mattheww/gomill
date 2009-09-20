"""Organise multiple GTP games.

"""

import os
import shlex
import sys

def log_to_stdout(s):
    print s

NoGameAvailable = object()

class Player_config(object):
    """Player description for use in tournament files."""
    def __init__(self, command_string, gtp_translations=None):
        # Ought to validate
        self.cmd_args = shlex.split(command_string)
        self.cmd_args[0] = os.path.expanduser(self.cmd_args[0])
        if gtp_translations is None:
            self.gtp_translations = {}
        else:
            self.gtp_translations = gtp_translations

control_file_globals = {
    'Player' : Player_config,
    }

class Competition(object):
    """A resumable processing job based on playing many GTP games.

    FIXME: This is base class for Tournament (and later tuners).

    """
    def __init__(self, competition_code):
        self.competition_code = competition_code
        self.logger = log_to_stdout

    def set_logger(self, logger):
        self.logger = logger

    def log(self, s):
        self.logger(s)

    def initialise_from_control_file(self, config):
        """Initialise competition data from the control file.

        config -- namespace produced by the control file.

        (When resuming from saved state, this is called before set_state()).

        """
        # Ought to validate.
        self.description = config['description']
        self.players = config.get('players', {})
        for player, s in config.get('player_commands', {}).items():
            self.players[player] = Player_config(s)
        self.board_size = config['board_size']
        self.komi = config['komi']
        self.move_limit = config['move_limit']
        self.use_internal_scorer = False
        self.preferred_scorers = None
        if 'scorer' in config:
            if config['scorer'] == "internal":
                self.use_internal_scorer = True
            elif config['scorer'] == "players":
                self.preferred_scorers = config.get('preferred_scorers')
            else:
                raise ValueError

    def get_status(self):
        """Return full state of the competition, so it can be resumed later.

        The returned result must be serialisable using json. In addition, it can
        include Game_result objects.

        """
        raise NotImplementedError

    def set_status(self, status):
        """Reset competition state to previously a reported value.

        'status' will be a value previously reported by get_status().

        """
        raise NotImplementedError

    def get_game(self):
        """Return the details of the next game to play.

        Returns a game_jobs.Game_job, or NoGameAvailable

        (Doesn't set sgf_pathname: the ringmaster does that).

        """
        raise NotImplementedError

    def process_game_result(self, response):
        """Process the results from a completed game.

        response -- game_jobs.Game_job_result

        """
        raise NotImplementedError

    def process_game_error(self, job, previous_error_count):
        """Process a report that a job failed.

        job                  -- game_jobs.Game_job
        previous_error_count -- int >= 0

        Returns a pair (stop_competition, retry_game)

        The job is one previously returned by get_game(). previous_error_count
        is the number of times that this particular job has failed before.

        Failed jobs are ones in which there was an error more serious than one
        which just causes an engine to forfeit the game. For example, the job
        will fail if one of the engines fails to respond to GTP commands at all,
        or (in particular) if it exits as soon as it's invoked because it
        doesn't like its command-line options.

        (Competition provides a default implementation which will retry a game
         once and then stop the competition, leaving the game to be retried on
         the next run.)

        """
        if previous_error_count > 0:
            return (True, True)
        else:
            return (False, True)

    def write_static_description(self, out):
        """Write a description of the competition.

        out -- writeable file-like object

        This reports on 'static' data, rather than the game results.

        """
        raise NotImplementedError

    def write_status_summary(self, out):
        """Write a summary of current competition status.

        out -- writeable file-like object

        This reports on the game results, and shouldn't duplicate information
        from write_static_description().

        """
        raise NotImplementedError

    def write_results_report(self, out):
        """Write a detailed report of a completed competition.

        out -- writeable file-like object

        This reports on the game results, and shouldn't duplicate information
        from write_static_description() or write_status_summary().

        """
        raise NotImplementedError

