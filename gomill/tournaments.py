"""Competitions made up of repeated matchups between specified players."""

from gomill import game_jobs
from gomill.competitions import Competition, NoGameAvailable


class Tournament(Competition):
    """A Competition made up of repeated matchups between specified players."""
    def __init__(self, competition_code):
        Competition.__init__(self, competition_code)
        self.engine_names = {}
        self.engine_descriptions = {}
        self.results = []
        self.next_game_number = 0

    def initialise_from_control_file(self, config):
        # FIXME: Some of this will move down to Competition.

        # Ought to validate.
        self.description = config['description']
        self.players = config.get('players', {})
        for player, s in config.get('player_commands', {}).items():
            self.players[player] = Player_config(s)

        self.board_size = config['board_size']
        self.komi = config['komi']
        self.move_limit = config['move_limit']
        self.number_of_games = config.get('number_of_games')
        self.record_games = config['record_games']
        self.use_internal_scorer = False
        self.preferred_scorers = None
        if 'scorer' in config:
            if config['scorer'] == "internal":
                self.use_internal_scorer = True
            elif config['scorer'] == "players":
                self.preferred_scorers = config.get('preferred_scorers')
            else:
                raise ValueError

        uses_legacy_matchups = ('player_x' in config or
                                'player_y' in config or
                                'alternating' in config)
        if uses_legacy_matchups:
            if 'matchups' in config:
                raise ValueError
            self.matchups = [(config['player_x'], config['player_y'])]
            if config['alternating']:
                self.matchups.append((config['player_y'], config['player_x']))
        else:
            self.matchups = config['matchups']
        for p1, p2 in self.matchups:
            if p1 not in self.players or p2 not in self.players:
                raise ValueError

    def get_status(self):
        """Return full state of the competition, so it can be resumed later.

        The returned result must be serialisable using json. In addition, it cal
        include Game_result objects.

        """
        return {
            'results' : self.results,
            'next_game_number' : self.next_game_number,
            'engine_names' : self.engine_names,
            'engine_descriptions' : self.engine_descriptions,
            }

    def set_status(self, status):
        """Reset competition state to previously a reported value.

        'status' will be a value previously reported by get_status().

        """
        self.results = status['results']
        self.next_game_number = status['next_game_number']
        self.engine_names = status['engine_names']
        self.engine_descriptions = status['engine_descriptions']

    def _games_played(self):
        return len(self.results)

    def brief_progress_message(self):
        """Return a one-line description of competition progress."""
        if self.number_of_games is None:
            return "%d games played" % self._games_played()
        else:
            return "%d/%d games played" % (
                self._games_played(), self.number_of_games)

    def get_game(self):
        """Return the details of the next game to play.

        Returns a game_jobs.Game_job, or NoGameAvailable

        (Doesn't set sgf_dir_pathname: the ringmaster does that).

        """
        game_number = self.next_game_number
        if (self.number_of_games is not None and
            game_number >= self.number_of_games):
            return NoGameAvailable
        self.next_game_number += 1
        player_b, player_w = self.matchups[game_number % len(self.matchups)]
        commands = {'b' : self.players[player_b].cmd_args,
                    'w' : self.players[player_w].cmd_args}
        gtp_translations = {'b' : self.players[player_b].gtp_translations,
                            'w' : self.players[player_w].gtp_translations}
        players = {'b' : player_b, 'w' : player_w}

        job = game_jobs.Game_job()
        job.game_id = str(game_number)
        job.players = players
        job.commands = commands
        job.gtp_translations = gtp_translations
        job.board_size = self.board_size
        job.komi = self.komi
        job.move_limit = self.move_limit
        job.use_internal_scorer = self.use_internal_scorer
        job.preferred_scorers = self.preferred_scorers
        job.record_sgf = self.record_games
        job.sgf_event = self.competition_code
        return job

    def process_game_result(self, response):
        """Process the results from a completed game.

        response -- game_jobs.Game_job_result

        """
        self.engine_names.update(response.engine_names)
        self.engine_descriptions.update(response.engine_names)
        self.results.append(response.game_result)

    def write_static_description(self, out):
        """Write a description of the competition.

        out -- writeable file-like object

        This reports on 'static' data, rather than the game results.

        """
        def p(s):
            print >>out, s
        p("tournament: %s" % self.competition_code)
        for code, description in sorted(self.engine_descriptions.items()):
            p("player %s: %s" % (code, description))
        p("board size: %s" % self.board_size)
        p("komi: %s" % self.komi)
        p(self.description)

    def write_status_summary(self, out):
        """Write a summary of current competition status.

        out -- writeable file-like object

        This reports on the game results, and shouldn't duplicate information
        from write_static_description().

        """
        # matchups without regard to colour choice
        pairings = sorted(set(tuple(sorted(t)) for t in self.matchups))
        for player_x, player_y in pairings:
            self.write_pairing_report(out, player_x, player_y)

    def write_results_report(self, out):
        """Write a detailed report of a completed competition.

        out -- writeable file-like object

        This reports on the game results, and shouldn't duplicate information
        from write_static_description() or write_status_summary().

        """
        def p(s):
            print >>out, s
        for i, result in enumerate(self.results):
            p("%3d %s" % (i, result.describe()))

    def write_pairing_report(self, out, player_x, player_y):
        def p(s):
            print >>out, s
        results = [r for r in self.results
                   if (r.player_b == player_x and r.player_w == player_y) or
                      (r.player_b == player_y and r.player_w == player_x)]
        total = len(results)
        if total == 0:
            return
        x_wins = len([1 for r in results if r.winning_player == player_x])
        y_wins = len([1 for r in results if r.winning_player == player_y])
        unknown = len([1 for r in results if r.winning_player is None])
        b_wins = len([1 for r in results if r.winning_colour == 'b'])
        w_wins = len([1 for r in results if r.winning_colour == 'w'])
        xb_wins = len([1 for r in results if
                       r.winning_player == player_x and
                       r.winning_colour == 'b'])
        xw_wins = len([1 for r in results if
                       r.winning_player == player_x and
                       r.winning_colour == 'w'])
        yb_wins = len([1 for r in results if
                       r.winning_player == player_y and
                       r.winning_colour == 'b'])
        yw_wins = len([1 for r in results if
                       r.winning_player == player_y and
                       r.winning_colour == 'w'])
        xb_played = len([1 for r in results if
                         r.player_b == player_x])
        xw_played = len([1 for r in results if
                         r.player_w == player_x])
        yb_played = len([1 for r in results if
                         r.player_b == player_y])
        yw_played = len([1 for r in results if
                         r.player_w == player_y])

        x_times = [r.cpu_times[player_x] for r in results]
        x_known_times = [t for t in x_times if t is not None and t != '?']
        if x_known_times:
            x_avg_time_s = "%7.2f" % (sum(x_known_times) / len(x_known_times))
        else:
            x_avg_time = "----"
        y_times = [r.cpu_times[player_y] for r in results]
        y_known_times = [t for t in y_times if t is not None and t != '?']
        if y_known_times:
            y_avg_time_s = "%7.2f" % (sum(y_known_times) / len(y_known_times))
        else:
            y_avg_time = "----"

        p("%s vs %s (%d games)" % (player_x, player_y, total))
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

