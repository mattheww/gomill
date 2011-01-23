"""Competitions made up of repeated matchups between specified players."""

from __future__ import division

from collections import defaultdict

from gomill import game_jobs
from gomill import competitions
from gomill import competition_schedulers
from gomill import tournaments
from gomill import tournament_results
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.settings import *
from gomill.gomill_utils import format_percent


class Matchup_config(Quiet_config):
    """Matchup description for use in control files."""
    # positional or keyword
    positional_arguments = ('player1', 'player2')
    # keyword-only
    keyword_arguments = (
        ('id', 'name') +
        tuple(setting.name for setting in tournaments.matchup_settings))


class Playoff(tournaments.Tournament):
    """A Tournament with explicitl listed matchups.

    The game ids are like '0_2', where 0 is the matchup id and 2 is the game
    number within the matchup.

    """

    def control_file_globals(self):
        result = Competition.control_file_globals(self)
        result.update({
            'Matchup' : Matchup_config,
            })
        return result


    global_settings = Competition.global_settings

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
                tournaments.matchup_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        # Check default handicap settings when possible, for friendlier error
        # reporting (would be caught in the matchup anyway).
        if matchup_defaults['board_size'] is not tournaments._required_in_matchup:
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


    # State attributes (*: in persistent state):
    #  *results               -- map matchup id -> list of Game_results
    #  *scheduler             -- Group_scheduler (group codes are matchup ids)
    #  *engine_names          -- map player code -> string
    #  *engine_descriptions   -- map player code -> string
    #   working_matchups      -- set of matchup ids
    #       (matchups which have successfully completed a game in this run)
    #   probationary_matchups -- set of matchup ids
    #       (matchups which failed to complete their last game)
    #   ghost_matchups        -- map matchup id -> Ghost_matchup
    #       (matchups which have been removed from the control file)

    def _check_results(self):
        """Check that the current results are consistent with the control file.

        This is run when reloading state.

        Raises CompetitionError if they're not.

        (In general, control file changes are permitted. The only thing we
        reject is results for a currently-defined matchup whose players aren't
        correct.)

        """
        # We guarantee that results for a given matchup always have consistent
        # players, so we need only check the first result.
        for matchup in self.matchup_list:
            results = self.results[matchup.id]
            if not results:
                continue
            result = results[0]
            seen_players = sorted(result.players.itervalues())
            expected_players = sorted((matchup.p1, matchup.p2))
            if seen_players != expected_players:
                raise CompetitionError(
                    "existing results for matchup %s "
                    "are inconsistent with control file:\n"
                    "result players are %s;\n"
                    "control file players are %s" %
                    (matchup.id,
                     ",".join(seen_players), ",".join(expected_players)))

    def _set_ghost_matchups(self):
        self.ghost_matchups = {}
        live = set(self.matchups)
        for matchup_id, results in self.results.iteritems():
            if matchup_id in live:
                continue
            result = results[0]
            # p1 and p2 might not be the right way round, but it doesn't matter.
            self.ghost_matchups[matchup_id] = tournaments.Ghost_matchup(
                matchup_id, result.player_b, result.player_w)

    def _set_scheduler_groups(self):
        self.scheduler.set_groups(
            [(m.id, m.number_of_games) for m in self.matchup_list] +
            [(id, 0) for id in self.ghost_matchups])

    def set_clean_status(self):
        self.results = defaultdict(list)
        self.engine_names = {}
        self.engine_descriptions = {}
        self.scheduler = competition_schedulers.Group_scheduler()
        self.ghost_matchups = {}
        self._set_scheduler_groups()

    # Can bump this to prevent people loading incompatible .status files.
    status_format_version = 1

    def get_status(self):
        return {
            'results' : self.results,
            'scheduler' : self.scheduler,
            'engine_names' : self.engine_names,
            'engine_descriptions' : self.engine_descriptions,
            }

    def set_status(self, status):
        self.results = status['results']
        self._check_results()
        self._set_ghost_matchups()
        self.scheduler = status['scheduler']
        self._set_scheduler_groups()
        self.scheduler.rollback()
        self.engine_names = status['engine_names']
        self.engine_descriptions = status['engine_descriptions']

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

    def get_game(self):
        matchup_id, game_number = self.scheduler.issue()
        if matchup_id is None:
            return NoGameAvailable
        matchup = self.matchups[matchup_id]
        if matchup.alternating and (game_number % 2):
            player_b, player_w = matchup.p2, matchup.p1
        else:
            player_b, player_w = matchup.p1, matchup.p2
        game_id = matchup.make_game_id(game_number)

        job = game_jobs.Game_job()
        job.game_id = game_id
        job.game_data = (matchup_id, game_number)
        job.player_b = self.players[player_b]
        job.player_w = self.players[player_w]
        job.board_size = matchup.board_size
        job.komi = matchup.komi
        job.move_limit = matchup.move_limit
        job.handicap = matchup.handicap
        job.handicap_is_free = (matchup.handicap_style == 'free')
        job.use_internal_scorer = (matchup.scorer == 'internal')
        job.sgf_event = matchup.event_description
        return job

    def process_game_result(self, response):
        self.engine_names.update(response.engine_names)
        self.engine_descriptions.update(response.engine_descriptions)
        matchup_id, game_number = response.game_data
        game_id = response.game_id
        self.working_matchups.add(matchup_id)
        self.probationary_matchups.discard(matchup_id)
        self.scheduler.fix(matchup_id, game_number)
        self.results[matchup_id].append(response.game_result)
        self.log_history("%7s %s" % (game_id, response.game_result.describe()))

    def process_game_error(self, job, previous_error_count):
        # ignoring previous_error_count, as we can consider all jobs for the
        # same matchup to be equivalent.
        stop_competition = False
        retry_game = False
        matchup_id, game_data = job.game_data
        if (matchup_id not in self.working_matchups or
            matchup_id in self.probationary_matchups):
            stop_competition = True
        else:
            self.probationary_matchups.add(matchup_id)
            retry_game = True
        return stop_competition, retry_game


    def write_matchup_report(self, out, matchup, results):
        """Write the summary block for the specified matchup to 'out'

        results -- nonempty list of Game_results

        """
        # The control file might have changed since the results were recorded.
        # We are guaranteed that the player codes correspond, but nothing else.

        # We use the current matchup to describe 'background' information, as
        # that isn't available any other way, but we look to the results where
        # we can.

        def p(s):
            print >>out, s

        ms = tournament_results.Matchup_stats(results, matchup.p1, matchup.p2)
        ms.calculate_colour_breakdown()
        ms.calculate_time_stats()

        if matchup.number_of_games is None:
            played_s = "%d" % ms.total
        else:
            played_s = "%d/%d" % (ms.total, matchup.number_of_games)
        p("%s (%s games)" % (matchup.name, played_s))
        if ms.unknown > 0:
            p("unknown results: %d %s" %
              (ms.unknown, format_percent(ms.unknown, ms.total)))

        p(matchup.describe_details())
        p("\n".join(tournament_results.make_matchup_stats_table(ms).render()))

    def write_screen_report(self, out):
        first = True
        for matchup in self.matchup_list:
            results = self.results[matchup.id]
            if not results:
                continue
            if first:
                first = False
            else:
                print >>out
            self.write_matchup_report(out, matchup, results)

    def write_ghost_report(self, out):
        for matchup_id, matchup in sorted(self.ghost_matchups.iteritems()):
            print >>out
            results = self.results[matchup_id]
            self.write_matchup_report(out, matchup, results)

    def write_short_report(self, out):
        def p(s):
            print >>out, s
        p("playoff: %s" % self.competition_code)
        if self.description:
            p(self.description)
        p('')
        self.write_screen_report(out)
        self.write_ghost_report(out)
        p('')
        for code, description in sorted(self.engine_descriptions.items()):
            p("player %s: %s" % (code, description))
        p('')

    write_full_report = write_short_report

    def get_tournament_results(self):
        return tournament_results.Tournament_results(
            self.matchup_list, self.results)

