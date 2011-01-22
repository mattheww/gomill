"""Competitions made up of repeated matchups between specified players."""

from __future__ import division

from collections import defaultdict

from gomill import ascii_tables
from gomill import game_jobs
from gomill import competitions
from gomill import competition_schedulers
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.settings import *
from gomill.gomill_common import colour_name
from gomill.gomill_utils import format_float, format_percent


class Matchup(object):
    """Internal description of a matchup from the configuration file.

    Public attributes:
      id                -- matchup id (string)
      p1                -- player code
      p2                -- player code
      name              -- shortish string to show in reports
      event_description -- string to show as sgf event

    All Playoff matchup_settings are also available as attributes.

    If alternating is False, p1 plays black and p2 plays white; otherwise they
    alternate.

    p1 and p2 are always different.

    """
    def describe_details(self):
        # Not describing 'alternating', because it's obvious from the results
        s = "board size: %s   " % self.board_size
        if self.handicap is not None:
            s += "handicap: %s (%s)   " % (
                self.handicap, self.handicap_style)
        s += "komi: %s" % self.komi
        return s

    def make_game_id(self, game_number):
        return self._game_id_template % (self.id, game_number)

class Ghost_matchup(object):
    """Dummy Matchup object for matchups which have gone from the control file.

    This is used if the matchup appears in results.

    """
    def __init__(self, matchup_id, p1, p2):
        self.id = matchup_id
        self.p1 = p1
        self.p2 = p2
        self.name = "%s v %s" % (p1, p2)
        self.number_of_games = None

    def describe_details(self):
        return "?? (missing from control file)"


class _Required_in_matchup(object):
    def __str__(self):
        return "(no global default)"
_required_in_matchup = _Required_in_matchup()

class Matchup_setting(Setting):
    # Treat 'default' as a keyword-only argument
    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = _required_in_matchup
        Setting.__init__(self, *args, **kwargs)

# These settings can be specified both globally and in matchups.
# The global values (not stored) are defaults for the
# matchup values (stored as Matchup attributes).
matchup_settings = [
    Matchup_setting('board_size', competitions.interpret_board_size),
    Matchup_setting('komi', interpret_float),
    Matchup_setting('alternating', interpret_bool, default=False),
    Matchup_setting('handicap', allow_none(interpret_int), default=None),
    Matchup_setting('handicap_style', interpret_enum('fixed', 'free'),
                    default='fixed'),
    Matchup_setting('move_limit', interpret_positive_int, default=1000),
    Matchup_setting('scorer', interpret_enum('internal', 'players'),
                    default='players'),
    Matchup_setting('number_of_games', allow_none(interpret_int),
                    default=None),
    ]

class Matchup_config(Quiet_config):
    """Matchup description for use in control files."""
    # positional or keyword
    positional_arguments = ('player1', 'player2')
    # keyword-only
    keyword_arguments = (
        ('id', 'name') +
        tuple(setting.name for setting in matchup_settings))


class Playoff(Competition):
    """A Competition made up of repeated matchups between specified players.

    The game ids are like '0_2', where 0 is the matchup id and 2 is the game
    number within the matchup.

    """
    def __init__(self, competition_code, **kwargs):
        Competition.__init__(self, competition_code, **kwargs)
        self.working_matchups = set()
        self.probationary_matchups = set()

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

    def matchup_from_config(self, arguments, matchup_defaults):
        """Make a Matchup from a Matchup_config.

        arguments -- resolved arguments from a Matchup_config

        The 'id' argument must be present; the caller should add it if it
        wasn't there in the config file.

        The 'player1' and 'player2' arguments must be present; the caller
        should report an error before calling this function if they aren't.

        This function doesn't check that they are in self.players.

        Raises ControlFileError if there is an error in the configuration.

        Returns a Matchup with all attributes set.

        """
        matchup = Matchup()
        matchup.p1 = arguments['player1']
        matchup.p2 = arguments['player2']

        for setting in matchup_settings:
            if setting.name in arguments:
                try:
                    v = setting.interpret(arguments[setting.name])
                except ValueError, e:
                    raise ControlFileError(str(e))
            else:
                v = matchup_defaults[setting.name]
                if v is _required_in_matchup:
                    raise ControlFileError("'%s' not specified" % setting.name)
            setattr(matchup, setting.name, v)

        competitions.validate_handicap(
            matchup.handicap, matchup.handicap_style, matchup.board_size)

        matchup_id = arguments['id']
        try:
            matchup.id = interpret_identifier(matchup_id)
        except ValueError, e:
            raise ControlFileError("id: %s" % e)

        name = arguments.get('name')
        if name is None:
            name = "%s v %s" % (matchup.p1, matchup.p2)
            event_description = self.competition_code
        else:
            try:
                name = interpret_as_utf8(name)
            except ValueError, e:
                raise ControlFileError("name: %s" % e)
            event_description = "%s (%s)" % (self.competition_code, name)
        matchup.name = name
        matchup.event_description = event_description
        matchup._game_id_template = ("%s_" +
            competitions.leading_zero_template(matchup.number_of_games))

        return matchup

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
            matchup_defaults = load_settings(matchup_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        # Check default handicap settings when possible, for friendlier error
        # reporting (would be caught in the matchup anyway).
        if matchup_defaults['board_size'] is not _required_in_matchup:
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
            self.ghost_matchups[matchup_id] = Ghost_matchup(
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

        ms = Matchup_stats(results, matchup.p1, matchup.p2)
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
        p("\n".join(make_matchup_stats_table(ms).render()))

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

    def get_matchup_ids(self):
        """Return a list of all matchup ids, in definition order."""
        return [m.id for m in self.matchup_list]

    def get_matchups(self):
        """Return a map matchup id -> Matchup."""
        return self.matchups.copy()

    def get_matchup(self, matchup_id):
        """Return the Matchup with the specified id."""
        return self.matchups[matchup_id]

    def get_matchup_results(self, matchup_id):
        """Return the results for the specified matchup.

        Status must be loaded to use this.

        Returns a list of Game_results

        """
        return self.results[matchup_id][:]


class Matchup_stats(object):
    """Result statistics for games between a pair of players.

    Instantiate with
      results  -- list of gtp_games.Game_results
      player_x -- player code
      player_y -- player code
    The game results should all be for games between player_x and player_y.

    Public attributes:
      player_x    -- player code
      player_y    -- player code
      total       -- int (number of games)
      x_wins      -- float (score)
      y_wins      -- float (score)
      x_forfeits  -- int (number of games)
      y_forfeits  -- int (number of games)
      unknown     -- int (number of games)

    scores are multiples of 0.5 (as there may be jigos).

    """
    def __init__(self, results, player_x, player_y):
        self._results = results
        self.player_x = player_x
        self.player_y = player_y

        self.total = len(results)

        js = self._jigo_score = 0.5 * sum(r.is_jigo for r in results)
        self.unknown = sum(r.winning_player is None and not r.is_jigo
                           for r in results)

        self.x_wins = sum(r.winning_player == player_x for r in results) + js
        self.y_wins = sum(r.winning_player == player_y for r in results) + js

        self.x_forfeits = sum(r.winning_player == player_y and r.is_forfeit
                              for r in results)
        self.y_forfeits = sum(r.winning_player == player_x and r.is_forfeit
                              for r in results)

    def calculate_colour_breakdown(self):
        """Calculate futher statistics, broken down by colour played.

        Sets the following additional attributes:

        xb_played   -- int (number of games)
        xw_played   -- int (number of games)
        yb_played   -- int (number of games)
        yw_played   -- int (number of games)
        alternating -- bool
          when alternating is true =>
            b_wins   -- float (score)
            w_wins   -- float (score)
            xb_wins  -- float (score)
            xw_wins  -- float (score)
            yb_wins  -- float (score)
            yw_wins  -- float (score)
          else =>
            x_colour -- 'b' or 'w'
            y_colour -- 'b' or 'w'

        """
        results = self._results
        player_x = self.player_x
        player_y = self.player_y
        js = self._jigo_score

        self.xb_played = sum(r.player_b == player_x for r in results)
        self.xw_played = sum(r.player_w == player_x for r in results)
        self.yb_played = sum(r.player_b == player_y for r in results)
        self.yw_played = sum(r.player_w == player_y for r in results)

        if self.xw_played == 0 and self.yb_played == 0:
            self.alternating = False
            self.x_colour = 'b'
            self.y_colour = 'w'
        elif self.xb_played == 0 and self.yw_played == 0:
            self.alternating = False
            self.x_colour = 'w'
            self.y_colour = 'b'
        else:
            self.alternating = True
            self.b_wins = sum(r.winning_colour == 'b' for r in results) + js
            self.w_wins = sum(r.winning_colour == 'w' for r in results) + js
            self.xb_wins = sum(
                r.winning_player == player_x and r.winning_colour == 'b'
                for r in results) + js
            self.xw_wins = sum(
                r.winning_player == player_x and r.winning_colour == 'w'
                for r in results) + js
            self.yb_wins = sum(
                r.winning_player == player_y and r.winning_colour == 'b'
                for r in results) + js
            self.yw_wins = sum(
                r.winning_player == player_y and r.winning_colour == 'w'
                for r in results) + js

    def calculate_time_stats(self):
        """Calculate CPU time statistics.

        x_average_time -- float or None
        y_average_time -- float or None

        """
        player_x = self.player_x
        player_y = self.player_y
        x_times = [r.cpu_times[player_x] for r in self._results]
        x_known_times = [t for t in x_times if t is not None and t != '?']
        y_times = [r.cpu_times[player_y] for r in self._results]
        y_known_times = [t for t in y_times if t is not None and t != '?']
        if x_known_times:
            self.x_average_time = sum(x_known_times) / len(x_known_times)
        else:
            self.x_average_time = None
        if y_known_times:
            self.y_average_time = sum(y_known_times) / len(y_known_times)
        else:
            self.y_average_time = None


def make_matchup_stats_table(ms):
    """Produce an ascii table showing matchup statistics.

    ms -- Matchup_stats (with all statistics set)

    returns an ascii_tables.Table

    """
    ff = format_float
    pct = format_percent

    t = ascii_tables.Table(row_count=3)
    t.add_heading("") # player name
    i = t.add_column(align='left', right_padding=3)
    t.set_column_values(i, [ms.player_x, ms.player_y])

    t.add_heading("wins")
    i = t.add_column(align='right')
    t.set_column_values(i, [ff(ms.x_wins), ff(ms.y_wins)])

    t.add_heading("") # overall pct
    i = t.add_column(align='right')
    t.set_column_values(i, [pct(ms.x_wins, ms.total),
                            pct(ms.y_wins, ms.total)])

    if ms.alternating:
        t.columns[i].right_padding = 7
        t.add_heading("black", span=2)
        i = t.add_column(align='left')
        t.set_column_values(i, [ff(ms.xb_wins), ff(ms.yb_wins), ff(ms.b_wins)])
        i = t.add_column(align='right', right_padding=5)
        t.set_column_values(i, [pct(ms.xb_wins, ms.xb_played),
                                pct(ms.yb_wins, ms.yb_played),
                                pct(ms.b_wins, ms.total)])

        t.add_heading("white", span=2)
        i = t.add_column(align='left')
        t.set_column_values(i, [ff(ms.xw_wins), ff(ms.yw_wins), ff(ms.w_wins)])
        i = t.add_column(align='right', right_padding=3)
        t.set_column_values(i, [pct(ms.xw_wins, ms.xw_played),
                                pct(ms.yw_wins, ms.yw_played),
                                pct(ms.w_wins, ms.total)])
    else:
        t.columns[i].right_padding = 3
        t.add_heading("")
        i = t.add_column(align='left')
        t.set_column_values(i, ["(%s)" % colour_name(ms.x_colour),
                                "(%s)" % colour_name(ms.y_colour)])

    if ms.x_forfeits or ms.y_forfeits:
        t.add_heading("forfeits")
        i = t.add_column(align='right')
        t.set_column_values(i, [ms.x_forfeits, ms.y_forfeits])

    if ms.x_average_time or ms.y_average_time:
        if ms.x_average_time is not None:
            x_avg_time_s = "%7.2f" % ms.x_average_time
        else:
            x_avg_time_s = "   ----"
        if ms.y_average_time is not None:
            y_avg_time_s = "%7.2f" % ms.y_average_time
        else:
            y_avg_time_s = "   ----"
        t.add_heading("avg cpu")
        i = t.add_column(align='right', right_padding=2)
        t.set_column_values(i, [x_avg_time_s, y_avg_time_s])

    return t
