"""Competitions for all-play-all tournaments."""

from gomill import ascii_tables
from gomill import competitions
from gomill import playoffs
from gomill.competitions import (
    Competition, CompetitionError, ControlFileError)
from gomill.settings import *


matchup_settings = [
    Setting('board_size', competitions.interpret_board_size),
    Setting('komi', interpret_float),
    Setting('move_limit', interpret_positive_int, default=1000),
    Setting('scorer', interpret_enum('internal', 'players'),
            default='players'),
    Setting('number_of_games', allow_none(interpret_int), default=None),
    ]

class Competitor_config(Quiet_config):
    """Competitor description for use in control files."""
    # positional or keyword
    positional_arguments = ('player',)
    # keyword-only
    keyword_arguments = ()

class Competitor_spec(object):
    """Internal description of a competitor spec from the configuration file.

    Public attributes:
      player      -- player code
      short_code  -- eg 'A' or 'ZZ'

    """


class Allplayall(playoffs.Playoff):
    """A Competition in which each player repeatedly plays each other player.

    The game ids are like 0v1_2, where 0 and 1 are the competitor numbers and 2
    is the game number between those two competitors.

    """
    def __init__(self, competition_code, **kwargs):
        playoffs.Playoff.__init__(self, competition_code, **kwargs)

    def control_file_globals(self):
        result = Competition.control_file_globals(self)
        result.update({
            'Competitor' : Competitor_config,
            })
        return result


    special_settings = [
        Setting('competitors',
                interpret_sequence_of_quiet_configs(
                    Competitor_config, allow_simple_values=True)),
        ]

    def competitor_spec_from_config(self, i, competitor_config):
        """Make a Competitor_spec from a Competitor_config.

        i -- ordinal number of the competitor.

        Raises ControlFileError if there is an error in the configuration.

        Returns a Competitor_spec with all attributes set.

        """
        arguments = competitor_config.resolve_arguments()
        cspec = Competitor_spec()

        if 'player' not in arguments:
            raise ValueError("player not specified")
        cspec.player = arguments['player']
        if cspec.player not in self.players:
            raise ControlFileError("unknown player %s" % cspec.player)

        def let(n):
            return chr(ord('A') + n)
        if i < 26:
            cspec.short_code = let(i)
        elif i < 26*27:
            n, m = divmod(i, 26)
            cspec.short_code = let(n-1) + let(m)
        else:
            raise ValueError("too many competitors")
        return cspec

    def initialise_from_control_file(self, config):
        Competition.initialise_from_control_file(self, config)

        try:
            matchup_defaults = load_settings(matchup_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))
        matchup_defaults['handicap'] = None
        matchup_defaults['handicap_style'] = 'fixed'
        matchup_defaults['alternating'] = True

        try:
            specials = load_settings(self.special_settings, config)
        except ValueError, e:
            raise ControlFileError(str(e))

        if not specials['competitors']:
            raise ControlFileError("competitors: empty list")
        self.competitors = []
        for i, competitor_spec in enumerate(specials['competitors']):
            try:
                cspec = self.competitor_spec_from_config(i, competitor_spec)
            except StandardError, e:
                code = competitor_spec.get_key()
                if code is None:
                    code = i
                raise ControlFileError("competitor %s: %s" % (code, e))
            self.competitors.append(cspec)

        # map matchup_id -> Matchup
        self.matchups = {}
        # Matchups in order of definition
        self.matchup_list = []
        for c1_i, c1 in enumerate(self.competitors):
            for c2_i, c2 in list(enumerate(self.competitors))[c1_i+1:]:
                ms = playoffs.Matchup_config(c1.player, c2.player)
                try:
                    m = self.matchup_from_config(ms, matchup_defaults)
                except StandardError, e:
                    raise ControlFileError("%s v %s: %s" %
                                           (c1.player, c2.player, e))
                m.id = "%dv%d" % (c1_i, c2_i)
                self.matchups[m.id] = m
                self.matchup_list.append(m)

    def write_screen_report(self, out):
        t = ascii_tables.Table(row_count=len(self.competitors))
        t.add_heading("") # player short_code
        i = t.add_column(align='left')
        t.set_column_values(i, (c.short_code for c in self.competitors))

        t.add_heading("") # player code
        i = t.add_column(align='left')
        t.set_column_values(i, (c.player for c in self.competitors))

        for c2_i, c2 in enumerate(self.competitors):
            t.add_heading(" " + c2.short_code)
            i = t.add_column(align='left')
            column_values = []
            for c1_i, c1 in enumerate(self.competitors):
                if c1_i == c2_i:
                    column_values.append("")
                    continue
                if c1_i < c2_i:
                    matchup_id = "%dv%d" % (c1_i, c2_i)
                    matchup = self.matchups[matchup_id]
                    player_x = matchup.p1
                    player_y = matchup.p2
                else:
                    matchup_id = "%dv%d" % (c2_i, c1_i)
                    matchup = self.matchups[matchup_id]
                    player_x = matchup.p2
                    player_y = matchup.p1
                results = [r[1] for r in self.results[matchup.id]]
                js = jigo_scores = 0.5 * sum(r.is_jigo for r in results)
                x_wins = sum(r.winning_player == player_x for r in results) + js
                y_wins = sum(r.winning_player == player_y for r in results) + js
                column_values.append("%d-%d" % (x_wins, y_wins))
            t.set_column_values(i, column_values)
        print >>out, "\n".join(t.render())

    def write_short_report(self, out):
        def p(s):
            print >>out, s
        p("playoff: %s" % self.competition_code)
        if self.description:
            p(self.description)
        p('')
        self.write_screen_report(out)
        p('')
        playoffs.Playoff.write_screen_report(self, out)
        p('')
        for code, description in sorted(self.engine_descriptions.items()):
            p("player %s: %s" % (code, description))
        p('')
