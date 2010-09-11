"""Organise processing jobs based around playing many GTP games."""

import os
import shlex
import sys

from gomill import game_jobs
from gomill import gtp_controller
from gomill import handicap_layout
from gomill.settings import *


def log_discard(s):
    pass

NoGameAvailable = object()

class CompetitionError(StandardError):
    """Error from competition code.

    This is intended for errors from user-provided functions, but it might also
    indicate a bug in tuner code.

    The ringmaster should display the error and terminate immediately.

    """

class ControlFileError(StandardError):
    """Error interpreting the control file."""


class Player_config(object):
    """Player description for use in control files."""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

class Control_file_token(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "<%s>" % self.name

STDERR = Control_file_token('STDERR')
LOG = Control_file_token('LOG')
DISCARD = Control_file_token('DISCARD')


_player_settings = [
    Setting('command_string', interpret_8bit_string),
    Setting('is_reliable_scorer', interpret_bool, default=True),
    Setting('gtp_translations', interpret_map, default=dict),
    Setting('startup_gtp_commands', interpret_sequence, default=list),
    Setting('stderr', interpret_enum(STDERR, LOG, DISCARD), default=LOG),
    ]

class Competition(object):
    """A resumable processing job based around playing many GTP games.

    This is an abstract base class.

    """

    def __init__(self, competition_code):
        self.competition_code = competition_code
        self.event_logger = log_discard
        self.history_logger = log_discard

    def control_file_globals(self):
        """Specify names and values to make available to the control file.

        Returns a dict suitable for use as the control file's namespace.

        """
        return {
            'Player' : Player_config,
            'STDERR' : STDERR,
            'LOG' : LOG,
            'DISCARD' : DISCARD,
            }

    def set_event_logger(self, logger):
        """Set a callback for the event log.

        logger -- function taking a string argument

        Until this is called, event log output is silently discarded.

        """
        self.event_logger = logger

    def set_history_logger(self, logger):
        """Set a callback for the history log.

        logger -- function taking a string argument

        Until this is called, event log output is silently discarded.

        """
        self.history_logger = logger

    def log_event(self, s):
        """Write a message to the event log.

        The event log logs all game starts and finishes; competitions can add
        lines to mark things like the start of new generations.

        A newline is added to the message.

        """
        self.event_logger(s)

    def log_history(self, s):
        """Write a message to the history log.

        The history log is used to show things like game results and tuning
        event intermediate status.

        A newline is added to the message.

        """
        self.history_logger(s)

    # List of Settings, for overriding in subclasses.
    global_settings = []

    def initialise_from_control_file(self, config):
        """Initialise competition data from the control file.

        config -- namespace produced by the control file.

        (When resuming from saved state, this is called before set_state()).

        This processes all global_settings and sets attributes (named by the
        setting names).

        It also handles the following settings and sets the corresponding
        attributes:
          players -- map player code -> game_jobs.Player

        Raises ControlFileError with a description if the control file has a bad
        or missing value.

        """
        # This is called for all commands, so it mustn't log anything.

        # Implementations in subclasses should have their own backstop exception
        # handlers, so they can at least show what part of the control file was
        # being interpreted when the exception occurred.

        # We should accept that there may be unexpected exceptions, because
        # control files are allowed to do things like substitute list-like
        # objects for Python lists.

        try:
            to_set = load_settings(self.global_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))
        for name, value in to_set.items():
            setattr(self, name, value)

        try:
            specials = load_settings(
                [Setting('players', interpret_map)], config)
        except ValueError, e:
            raise ControlFileError(str(e))

        self.players = {}
        try:
            # pre-check player codes before trying to sort them, just in case.
            for player_code, _ in specials['players']:
                if not isinstance(player_code, basestring):
                    raise ControlFileError("bad player code (not a string)")
            for player_code, player_config in sorted(specials['players']):
                try:
                    player_code = interpret_identifier(player_code)
                except ValueError, e:
                    if isinstance(player_code, unicode):
                        player_code = player_code.encode("ascii", "replace")
                    raise ControlFileError(
                        "bad code (%s): %s" % (e, player_code))
                if not isinstance(player_config, Player_config):
                    raise ControlFileError(
                        "player %s is not a Player" % player_code)
                try:
                    player = self.game_jobs_player_from_config(
                        player_code, player_config)
                except StandardError, e:
                    raise ControlFileError("player %s: %s" % (player_code, e))
                self.players[player_code] = player
        except ControlFileError, e:
            raise ControlFileError("'players' : %s" % e)
        except StandardError, e:
            raise ControlFileError("'players': unexpected error: %s" % e)

    def game_jobs_player_from_config(self, code, player_config):
        """Make a game_jobs.Player from a Player_config.

        Raises ControlFileError with a description if there is an error in the
        configuration.

        Returns an incomplete game_jobs.Player (see get_game() for details).

        """
        if len(player_config.args) > 1:
            raise ControlFileError("too many arguments")
        if player_config.args:
            if 'command_string' in player_config.kwargs:
                raise ControlFileError(
                    "command_string specified both implicitly and explicitly")
            player_config.kwargs['command_string'] = player_config.args[0]

        config = load_settings(_player_settings, player_config.kwargs,
                               strict=True)

        player = game_jobs.Player()
        player.code = code

        try:
            player.cmd_args = shlex.split(config['command_string'])
            player.cmd_args[0] = os.path.expanduser(player.cmd_args[0])
        except StandardError, e:
            raise ControlFileError("'command_string': %s" % e)

        player.is_reliable_scorer = config['is_reliable_scorer']

        player.startup_gtp_commands = []
        try:
            for s in config['startup_gtp_commands']:
                try:
                    words = s.split()
                    if not all(gtp_controller.is_well_formed_gtp_word(word)
                               for word in words):
                        raise StandardError
                except StandardError:
                    raise ValueError("invalid command string %s" % s)
                player.startup_gtp_commands.append((words[0], words[1:]))
        except ValueError, e:
            raise ControlFileError("'startup_gtp_commands': %s" % e)

        player.gtp_translations = {}
        try:
            for cmd1, cmd2 in config['gtp_translations']:
                if not gtp_controller.is_well_formed_gtp_word(cmd1):
                    raise ValueError("invalid command %s" % cmd1)
                if not gtp_controller.is_well_formed_gtp_word(cmd2):
                    raise ValueError("invalid command %s" % cmd2)
                player.gtp_translations[cmd1] = cmd2
        except ValueError, e:
            raise ControlFileError("'gtp_translations': %s" % e)

        player._stderr = config['stderr']

        return player


    def set_clean_status(self):
        """Reset competition state to its initial value."""
        # This is called before logging is set up, so it mustn't log anything.
        raise NotImplementedError

    def get_status(self):
        """Return full state of the competition, so it can be resumed later.

        The returned result must be pickleable.

        """
        raise NotImplementedError

    def set_status(self, status):
        """Reset competition state to a previously reported value.

        'status' will be a value previously reported by get_status().

        """
        # This is called for the 'show' command, so it mustn't log anything.
        raise NotImplementedError

    def get_players_to_check(self):
        """List the Players for check_players() to check.

        Returns a list of game_jobs.Player objects. Their stderr_pathname
        attribute will be ignored.

        This is called without the competition status being set.

        """
        raise NotImplementedError

    def get_game(self):
        """Return the details of the next game to play.

        Returns a game_jobs.Game_job, or NoGameAvailable.

        The Game_job is incomplete in the following ways (which are left to the
        ringmaster to finish off):
         - sgf_pathname isn't set
         - gtp_log_pathname isn't set
         - the Players' stderr_pathname isn't set; instead they have a _stderr
           attribute with value STDERR, LOG, or DISCARD.

        """
        raise NotImplementedError

    def process_game_result(self, response):
        """Process the results from a completed game.

        response -- game_jobs.Game_job_result

        This may return a text description of the game result, to override the
        default (it should normally include response.game_result.sgf_result).

        """
        raise NotImplementedError

    def process_game_error(self, job, previous_error_count):
        """Process a report that a job failed.

        job                  -- game_jobs.Game_job
        previous_error_count -- int >= 0

        Returns a pair of bools (stop_competition, retry_game)

        If stop_competition is True, the ringmaster will stop starting new
        games. Otherwise, if retry_game is true the ringmaster will try running
        the same game again.

        The job is one previously returned by get_game(). previous_error_count
        is the number of times that this particular job has failed before.

        Failed jobs are ones in which there was an error more serious than one
        which just causes an engine to forfeit the game. For example, the job
        will fail if one of the engines fails to respond to GTP commands at all,
        or (in particular) if it exits as soon as it's invoked because it
        doesn't like its command-line options.

        """
        raise NotImplementedError

    def write_screen_report(self, out):
        """Write a one-screen summary of current competition status.

        out -- writeable file-like object

        This is supposed to fit comfortably on one screen; it's normally
        displayed continuously by the ringmaster. Aim for about 30 lines.

        It should end with a newline, but not have additional blank lines at
        the end.

        This should focus on describing incomplete competitions usefully.

        """
        raise NotImplementedError

    def write_short_report(self, out):
        """Write a short report of the competition status/results.

        out -- writeable file-like object

        This is used for the ringmaster's 'show' command.

        It should end with a newline, but not have additional blank lines at
        the end.

        This should be useful for both completed and incomplete competitions.

        """
        raise NotImplementedError

    def write_full_report(self, out):
        """Write a detailed report of competition status/results.

        out -- writeable file-like object

        This is used for the ringmaster's 'report' command.

        It should end with a newline.

        This should focus on describing completed competitions well.

        """
        raise NotImplementedError


## Helper functions for settings

def interpret_board_size(i):
    i = interpret_int(i)
    if i < 2:
        raise ValueError("too small")
    if i > 25:
        raise ValueError("too large")
    return i

def validate_handicap(handicap, handicap_style, board_size):
    """Check whether a handicap is allowed.

    handicap       -- int or None
    handicap_style -- 'free' or 'fixed'
    board_size     -- int

    Raises ControlFileError with a description if it isn't.

    """
    if handicap is None:
        return True
    if handicap < 2:
        raise ControlFileError("handicap too small")
    if handicap_style == 'fixed':
        limit = handicap_layout.max_fixed_handicap_for_board_size(board_size)
    else:
        limit = handicap_layout.max_free_handicap_for_board_size(board_size)
    if handicap > limit:
        raise ControlFileError(
            "%s handicap out of range for board size %d" %
            (handicap_style, board_size))

