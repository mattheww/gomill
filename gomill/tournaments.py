"""Competitions made up of repeated matchups between specified players."""

from __future__ import division

from collections import defaultdict

from gomill import game_jobs
from gomill import competitions
from gomill.competitions import Competition, NoGameAvailable, Matchup_config
from gomill.settings import *


class Matchup(object):
    """Internal description of a matchup from the configuration file.

    Public attributes:
      p1             -- player code
      p2             -- player code
      name           -- shortish string to show in reports

    All Tournament matchup_settings are also available as attributes.

    If alternating is False, p1 plays black and p2 plays white; otherwise they
    alternate.

    """


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


class Tournament(Competition):
    """A Competition made up of repeated matchups between specified players."""

    # These settings can be specified both globally and in matchups.
    # The global values (stored as Tournament attributes) are defaults for the
    # matchup values (stored as Matchup attributes).
    matchup_settings = [
        Matchup_setting('board_size', competitions.interpret_board_size),
        Matchup_setting('komi', interpret_float),
        Matchup_setting('alternating', interpret_bool, default=False),
        Matchup_setting('handicap', allow_none(interpret_int), default=None),
        Matchup_setting('handicap_style', interpret_enum('fixed', 'free'),
                        default='fixed'),
        Matchup_setting('move_limit', interpret_int, default=1000),
        Matchup_setting('scorer', interpret_enum('internal', 'players'),
                        default='players'),
        ]

    global_settings = matchup_settings + [
        Setting('description', interpret_as_utf8, default=""),
        Setting('number_of_games', interpret_int),
        ]

    def matchup_from_config(self, matchup_config):
        """Make a Matchup from a Matchup_config.

        Raises ValueError if there is an error in the configuration.

        Returns a Matchup with all attributes set.

        """
        args = matchup_config.args
        kwargs = matchup_config.kwargs
        matchup = Matchup()
        argument_names = set(setting.name for setting in self.matchup_settings)
        argument_names.update(('name',))
        for key in kwargs:
            if key not in argument_names:
                raise ValueError("unknown argument '%s'" % key)
        if len(args) > 2:
            raise ValueError("too many arguments")
        if len(args) < 2:
            raise ValueError("not enough arguments")
        matchup.p1, matchup.p2 = args

        for setting in self.matchup_settings:
            if setting.name in kwargs:
                v = setting.interpret(kwargs[setting.name])
            else:
                v = getattr(self, setting.name)
                if v is _required_in_matchup:
                    raise ValueError("%s not specified" % setting.name)
            setattr(matchup, setting.name, v)

        competitions.validate_handicap(
            matchup.handicap, matchup.handicap_style, matchup.board_size)

        name = kwargs.get('name')
        if name is None:
            name = "%s v %s" % (matchup.p1, matchup.p2)
            # FIXME [[
            name += " %dx%d" % (matchup.board_size, matchup.board_size)
            name += " K%s" % matchup.komi
            if matchup.handicap:
                name += " H%d" % matchup.handicap
                if matchup.handicap_style == 'free':
                    name += "free"
            # ]]
        matchup.name = name
        return matchup

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        # Check default handicap settings when possible, for friendlier error
        # reporting (would be caught in the matchup anyway).
        if self.board_size is not _required_in_matchup:
            try:
                competitions.validate_handicap(
                    self.handicap, self.handicap_style, self.board_size)
            except ValueError, e:
                raise ValueError("default %s" % e)

        try:
            config_matchups = config['matchups']
        except KeyError, e:
            raise ValueError("%s not specified" % e)
        try:
            config_matchups = list(config_matchups)
        except StandardError:
            raise ValueError("'matchups': not a list")
        if not config_matchups:
            raise ValueError("no matchups specified")

        self.matchups = []
        for i, matchup in enumerate(config_matchups):
            if not isinstance(matchup, Matchup_config):
                raise ValueError("matchup entry %d is not a Matchup" % i)
            try:
                m = self.matchup_from_config(matchup)
                if m.p1 not in self.players:
                    raise ValueError("unknown player %s" % m.p1)
                if m.p2 not in self.players:
                    raise ValueError("unknown player %s" % m.p2)
            except ValueError, e:
                raise ValueError("matchup entry %d: %s" % (i, e))
            m.id = i
            self.matchups.append(m)

    def get_status(self):
        return {
            'results' : self.results,
            'next_game_number' : self.next_game_number,
            'engine_names' : self.engine_names,
            'engine_descriptions' : self.engine_descriptions,
            }

    def set_status(self, status):
        self.results = status['results']
        self.next_game_number = status['next_game_number']
        self.engine_names = status['engine_names']
        self.engine_descriptions = status['engine_descriptions']

    def set_clean_status(self):
        self.results = []
        self.next_game_number = 0
        self.engine_names = {}
        self.engine_descriptions = {}

    def _games_played(self):
        return len(self.results)

    def find_players(self, game_number):
        """Find the players for the next game.

        Returns a tuple (matchup index, black player code, white player code)

        """
        quot, rem = divmod(game_number, len(self.matchups))
        matchup = self.matchups[rem]
        if matchup.alternating and (quot % 2):
            pb, pw = matchup.p2, matchup.p1
        else:
            pb, pw = matchup.p1, matchup.p2
        return rem, pb, pw

    def get_game(self):
        game_number = self.next_game_number
        if (self.number_of_games is not None and
            game_number >= self.number_of_games):
            return NoGameAvailable
        self.next_game_number += 1

        matchup_id, player_b, player_w = self.find_players(game_number)
        matchup = self.matchups[matchup_id]
        job = game_jobs.Game_job()
        job.game_id = str(game_number)
        job.player_b = self.players[player_b]
        job.player_w = self.players[player_w]
        job.board_size = matchup.board_size
        job.komi = matchup.komi
        job.move_limit = matchup.move_limit
        job.handicap = matchup.handicap
        job.handicap_is_free = (matchup.handicap_style == 'free')
        job.use_internal_scorer = (matchup.scorer == 'internal')
        job.preferred_scorers = self.preferred_scorers
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        self.engine_names.update(response.engine_names)
        self.engine_descriptions.update(response.engine_descriptions)
        game_number = int(response.game_id)
        matchup_id, player_b, player_w = self.find_players(game_number)
        assert player_b == response.game_result.player_b
        assert player_w == response.game_result.player_w
        self.results.append((matchup_id, response.game_result))
        # This will show results in order of games finishing rather than game
        # number, but never mind.
        self.log_history("%4s %s" %
                         (response.game_id, response.game_result.describe()))

    def write_static_description(self, out):
        def p(s):
            print >>out, s
        p("tournament: %s" % self.competition_code)
        for code, description in sorted(self.engine_descriptions.items()):
            p("player %s: %s" % (code, description))
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)
        p(self.description)

    def write_status_summary(self, out):
        if self.number_of_games is None:
            print >>out, "%d games played" % self._games_played()
        else:
            print >>out, "%d/%d games played" % (
                self._games_played(), self.number_of_games)
        print >>out
        results_by_matchup_id = defaultdict(list)
        for matchup_id, result in self.results:
            results_by_matchup_id[matchup_id].append(result)
        for (i, matchup) in enumerate(self.matchups):
            results = results_by_matchup_id[i]
            if results:
                self.write_matchup_report(out, matchup, results)

    def write_results_report(self, out):
        pass

    def write_matchup_report(self, out, matchup, results):
        def p(s):
            print >>out, s
        total = len(results)
        assert total != 0
        player_x = matchup.p1
        player_y = matchup.p2
        x_wins = sum(r.winning_player == player_x for r in results)
        y_wins = sum(r.winning_player == player_y for r in results)
        unknown = sum(r.winning_player is None for r in results)
        b_wins = sum(r.winning_colour == 'b' for r in results)
        w_wins = sum(r.winning_colour == 'w' for r in results)
        xb_wins = sum(r.winning_player == player_x and r.winning_colour == 'b'
                      for r in results)
        xw_wins = sum(r.winning_player == player_x and r.winning_colour == 'w'
                      for r in results)
        yb_wins = sum(r.winning_player == player_y and r.winning_colour == 'b'
                      for r in results)
        yw_wins = sum(r.winning_player == player_y and r.winning_colour == 'w'
                      for r in results)
        xb_played = sum(r.player_b == player_x for r in results)
        xw_played = sum(r.player_w == player_x for r in results)
        yb_played = sum(r.player_b == player_y for r in results)
        yw_played = sum(r.player_w == player_y for r in results)

        x_times = [r.cpu_times[player_x] for r in results]
        x_known_times = [t for t in x_times if t is not None and t != '?']
        if x_known_times:
            x_avg_time_s = "%7.2f" % (sum(x_known_times) / len(x_known_times))
        else:
            x_avg_time_s = "----"
        y_times = [r.cpu_times[player_y] for r in results]
        y_known_times = [t for t in y_times if t is not None and t != '?']
        if y_known_times:
            y_avg_time_s = "%7.2f" % (sum(y_known_times) / len(y_known_times))
        else:
            y_avg_time_s = "----"

        p("%s (%d games)" % (matchup.name, total))
        def pct(n, baseline):
            if baseline == 0:
                if n == 0:
                    return "--"
                else:
                    return "??"
            return "%.2f%%" % (100 * n/baseline)
        if unknown > 0:
            p("unknown results: %d %s" % (unknown, pct(unknown, total)))

        pad = max(len(player_x), len(player_y)) + 2
        xname = player_x.ljust(pad)
        yname = player_y.ljust(pad)

        p(" " * (pad+17) + "   black         white        avg cpu")
        p("%s %4d %7s    %4d %7s  %4d %7s  %s"
          % (xname, x_wins, pct(x_wins, total),
             xb_wins, pct(xb_wins, xb_played),
             xw_wins, pct(xw_wins, xw_played),
             x_avg_time_s))
        p("%s %4d %7s    %4d %7s  %4d %7s  %s"
          % (yname, y_wins, pct(y_wins, total),
             yb_wins, pct(yb_wins, yb_played),
             yw_wins, pct(yw_wins, yw_played),
             y_avg_time_s))
        p(" " * (pad+17) + "%4d %7s  %4d %7s"
          % (b_wins, pct(b_wins, total), w_wins, pct(w_wins, total)))
        p("")

