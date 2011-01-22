"""Retrieving and reporting on tournament results."""

from __future__ import division

from gomill import ascii_tables
from gomill.gomill_utils import format_float, format_percent
from gomill.gomill_common import colour_name


class Tournament_results(object):
    """Provide access to results of a single tournament.

    The tournament results are catalogued in terms of 'matchups', with each
    matchup corresponding to a pair of players. Each matchup has an id, which is
    a short string.

    """
    def __init__(self, matchup_list, results):
        self.matchup_list = matchup_list
        self.results = results
        self.matchups = dict((m.id, m) for m in matchup_list)

    def get_matchup_ids(self):
        """Return a list of all matchup ids, in definition order."""
        return [m.id for m in self.matchup_list]

    def get_matchup(self, matchup_id):
        """Return the Matchup with the specified id.

        Returns an object with public attributes
          id                -- matchup id (string)
          p1                -- player code
          p2                -- player code
          name              -- shortish string to show in reports
          event_description -- string to show as sgf event
        And public methods:
          describe_details() -- return a string describing the matchup

        (treat the returned object as read-only)

        """
        return self.matchups[matchup_id]

    def get_matchups(self):
        """Return a map matchup id -> Matchup.

        See get_matchups() for a description of Matchup objects.

        """
        return self.matchups.copy()

    def get_matchup_results(self, matchup_id):
        """Return the results for the specified matchup.

        Returns a list of gtp_games.Game_results

        The Game_results all have game_id set.

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
