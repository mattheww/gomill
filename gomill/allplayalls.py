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

class Allplayall(playoffs.Playoff):
    """A Competition in which each player repeatedly plays each other player.

    The game ids are like 0v1_2, where 0 and 1 are the competitor numbers and 2
    is the game number between those two competitors.

    """
    def __init__(self, competition_code, **kwargs):
        playoffs.Playoff.__init__(self, competition_code, **kwargs)

    special_settings = [
        #Setting('competitors',
        #        interpret_sequence_of_quiet_configs(FIXME)),
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
        #FIXME
        specials = {'competitors' : config['competitors']}

        # map matchup_id -> Matchup
        self.matchups = {}
        # Matchups in order of definition
        self.matchup_list = []
        if not specials['competitors']:
            raise ControlFileError("competitors: empty list")

        for c1_i, c1 in enumerate(specials['competitors']):
            for c2_i, c2 in enumerate(specials['competitors']):
                if c1_i == c2_i:
                    continue
                ms = playoffs.Matchup_config(c1, c2)
                try:
                    m = self.matchup_from_config(ms, matchup_defaults)
                except StandardError, e:
                    # FIXME: Be careful once we have a Quiet_config
                    raise ControlFileError("%s v %s: %s" % (c1, c2, e))
                m.id = "%dv%d" % (c1_i, c2_i)
                self.matchups[m.id] = m
                self.matchup_list.append(m)
