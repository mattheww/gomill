"""Common code for all tournament types."""

from gomill import tournament_results
from gomill import competitions
from gomill.competitions import (
    Competition, NoGameAvailable, CompetitionError, ControlFileError)
from gomill.settings import *

class Matchup(tournament_results.Matchup_description):
    """Internal description of a matchup from the configuration file.

    Additional attributes:
      event_description -- string to show as sgf event

    """
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



class Tournament(Competition):
    """A Competition based on a number of matchups.

    """
    def __init__(self, competition_code, **kwargs):
        Competition.__init__(self, competition_code, **kwargs)
        self.working_matchups = set()
        self.probationary_matchups = set()

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

