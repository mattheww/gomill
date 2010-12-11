"""Competitions for all-play-all tournaments."""

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

        competitors = []
        for i, competitor_spec in enumerate(specials['competitors']):
            try:
                c = competitor_spec.resolve_arguments()
                if 'player' not in c:
                    raise ValueError("player not specified")
            except StandardError, e:
                code = competitor_spec.get_key()
                if code is None:
                    code = i
                raise ControlFileError("competitor %s: %s" % (code, e))
            competitors.append(c)

        # map matchup_id -> Matchup
        self.matchups = {}
        # Matchups in order of definition
        self.matchup_list = []
        for c1_i, c1 in enumerate(competitors):
            for c2_i, c2 in list(enumerate(competitors))[c1_i+1:]:
                ms = playoffs.Matchup_config(c1['player'], c2['player'])
                try:
                    m = self.matchup_from_config(ms, matchup_defaults)
                except StandardError, e:
                    raise ControlFileError("%s v %s: %s" %
                                           (c1['player'], c2['player'], e))
                m.id = "%dv%d" % (c1_i, c2_i)
                self.matchups[m.id] = m
                self.matchup_list.append(m)
