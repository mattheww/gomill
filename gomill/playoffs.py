"""Competitions made up of repeated matchups between specified players."""

from gomill import game_jobs
from gomill import competitions
from gomill import tournaments
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.settings import *


class Matchup_config(Quiet_config):
    """Matchup description for use in control files."""
    # positional or keyword
    positional_arguments = ('player1', 'player2')
    # keyword-only
    keyword_arguments = (
        ('id', 'name') +
        tuple(setting.name for setting in tournaments.matchup_settings))


class Playoff(tournaments.Tournament):
    """A Tournament with explicitly listed matchups.

    The game ids are like '0_2', where 0 is the matchup id and 2 is the game
    number within the matchup.

    """

    def control_file_globals(self):
        result = Competition.control_file_globals(self)
        result.update({
            'Matchup' : Matchup_config,
            })
        return result


    special_settings = [
        Setting('matchups',
                interpret_sequence_of_quiet_configs(Matchup_config)),
        ]

    def _fix_up_matchup_arguments(self, matchup_id, matchup_config):
        """Process a Matchup_config and return its arguments.

        Returns arguments suitable for use with matchup_from_config().

        This does matchup_config.resolve_arguments(), and the following further
        checks and fixups:

        Checks that the player1 and player2 parameters exist, and that the
        player codes are present in self.players.

        Sets the 'id' argument if not already present.

        If player1 and player2 are the same, takes the following actions:
         - sets player2 to <player1>#2
         - if it doesn't already exist, creates <player1>#2 as a clone of
           player1 and adds it to self.players

        """
        arguments = matchup_config.resolve_arguments()
        if 'id' not in arguments:
            arguments['id'] = matchup_id
        try:
            player_1 = arguments['player1']
            player_2 = arguments['player2']
        except KeyError:
            raise ControlFileError("not enough arguments")
        if player_1 not in self.players:
            raise ControlFileError("unknown player %s" % player_1)
        if player_2 not in self.players:
            raise ControlFileError("unknown player %s" % player_2)
        # If both players are the same, make a clone.
        if player_1 == player_2:
            p2_code = player_1 + "#2"
            arguments['player2'] = p2_code
            if p2_code not in self.players:
                self.players[p2_code] = self.players[player_1].copy(p2_code)
        return arguments

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        try:
            matchup_defaults = load_settings(
                tournaments.matchup_settings, config, allow_missing=True)
        except ValueError, e:
            raise ControlFileError(str(e))

        # Check default handicap settings when possible, for friendlier error
        # reporting (would be caught in the matchup anyway).
        if 'board_size' in matchup_defaults:
            try:
                competitions.validate_handicap(
                    matchup_defaults['handicap'],
                    matchup_defaults['handicap_style'],
                    matchup_defaults['board_size'])
            except ControlFileError, e:
                raise ControlFileError("default %s" % e)

        try:
            specials = load_settings(self.special_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        # map matchup_id -> Matchup
        self.matchups = {}
        # Matchups in order of definition
        self.matchup_list = []
        if not specials['matchups']:
            raise ControlFileError("matchups: empty list")

        for i, matchup_config in enumerate(specials['matchups']):
            matchup_id = matchup_config.kwargs.get('id', str(i))
            try:
                arguments = self._fix_up_matchup_arguments(
                    matchup_id, matchup_config)
                m = self.matchup_from_config(arguments, matchup_defaults)
            except StandardError, e:
                raise ControlFileError("matchup %s: %s" % (matchup_id, e))
            if m.id in self.matchups:
                raise ControlFileError("duplicate matchup id '%s'" % m.id)
            self.matchups[m.id] = m
            self.matchup_list.append(m)


    # Can bump this to prevent people loading incompatible .status files.
    status_format_version = 1

    def get_player_checks(self):
        # For board size and komi, we check the values from the first matchup
        # the player appears in.
        used_players = {}
        for m in reversed(self.matchup_list):
            if m.number_of_games == 0:
                continue
            used_players[m.p1] = m
            used_players[m.p2] = m
        result = []
        for code, matchup in sorted(used_players.iteritems()):
            check = game_jobs.Player_check()
            check.player = self.players[code]
            check.board_size = matchup.board_size
            check.komi = matchup.komi
            result.append(check)
        return result


    def write_screen_report(self, out):
        self.write_matchup_reports(out)

    def write_short_report(self, out):
        def p(s):
            print >>out, s
        p("playoff: %s" % self.competition_code)
        if self.description:
            p(self.description)
        p('')
        self.write_screen_report(out)
        self.write_ghost_matchup_reports(out)
        p('')
        self.write_player_descriptions(out)
        p('')

    write_full_report = write_short_report

