"""Run games between two GTP engines."""

from gomill.utils import *
from gomill.common import *
from gomill import gameplay
from gomill.gtp_controller import BadGtpResponse

class Game_result(gameplay.Result):
    """Description of a game result.

    Public attributes in addition to gameplay.Result:
      game_id        -- string or None
      players        -- map colour -> player code
      player_b       -- player code
      player_w       -- player code
      winning_player -- player code or None
      losing_player  -- player code or None
      cpu_times      -- map player code -> float (representing seconds) or None

    Call set_players() before using these.

    Winning/losing player are None for a jigo, unknown result, or void game.

    cpu_times are user time + system time.

    Game_results are suitable for pickling.

    """
    def __init__(self):
        gameplay.Result.__init__(self)
        self.game_id = None

    def set_players(self, players):
        """Specify the player-code map.

        players -- map colour -> player code

        """
        self.players = players.copy()
        self.player_b = players['b']
        self.player_w = players['w']
        self.winning_player = self.players.get(self.winning_colour)
        self.cpu_times = {self.player_b : None, self.player_w : None}
        if self.is_forfeit:
            self.detail = "forfeit by %s: %s" % (
                self.players[self.losing_colour], self.detail)

    @property
    def losing_player(self):
        if self.winning_colour is None:
            return None
        return self.players.get(opponent_of(self.winning_colour))

    def __getstate__(self):
        return (
            self.player_b,
            self.player_w,
            self.winning_colour,
            self.sgf_result,
            self.detail,
            self.is_forfeit,
            self.game_id,
            self.cpu_times,
            )

    def __setstate__(self, state):
        (self.player_b,
         self.player_w,
         self.winning_colour,
         self.sgf_result,
         self.detail,
         self.is_forfeit,
         self.game_id,
         cpu_times,
         ) = state
        # In gomill 0.7 and earlier, cpu_time could be '?'; treat this as None
        for colour, cpu_time in cpu_times.items():
            if cpu_time == '?':
                cpu_times[colour] = None
        self.cpu_times = cpu_times
        self.players = {'b' : self.player_b, 'w' : self.player_w}
        self.winning_player = self.players.get(self.winning_colour)
        self.is_jigo = (self.sgf_result == "0")

    def soft_update_cpu_times(self, cpu_times):
        """Update the cpu_times dict.

        cpu_times -- (partial) dict colour -> float or None

        If a value is already set (not None), this method doesn't change it.

        """
        for colour, cpu_time in cpu_times.iteritems():
            if self.cpu_times[self.players[colour]] is not None:
                continue
            self.cpu_times[self.players[colour]] = cpu_time

    def describe(self):
        """Return a short human-readable description of the result."""
        if self.winning_colour is not None:
            s = "%s beat %s " % (self.winning_player, self.losing_player)
        else:
            s = "%s vs %s " % (self.players['b'], self.players['w'])
        if self.is_jigo:
            s += "jigo"
        else:
            s += self.sgf_result
        if self.detail is not None:
            s += " (%s)" % self.detail
        return s

    def __repr__(self):
        return "<Game_result: %s>" % self.describe()

class Gtp_game_score(gameplay.Game_score):
    """Description of the scoring of a passed-out game.

    Public attributes in addition to gameplay.Game_score:
      scorers_disgreed -- bool
      player_scores    -- map colour -> string or None

    scorers_disagreed True means the scorers disagreed about the winner (not
    just the margin).

    player_scores values are the response from the final_score GTP command (if
    the player was asked).

    """
    def __init__(self, winner, margin):
        gameplay.Game_score.__init__(self, winner, margin)
        self.scorers_disagreed = False
        self.player_scores = {'b' : None, 'w' : None}

    def get_detail(self):
        if self.scorers_disagreed:
            return "players disagreed"
        else:
            return gameplay.Game_score.get_detail(self)

def describe_scoring(result, game_score):
    """Return a multiline string describing a game's scoring.

    result     -- Game_result
    game_score -- Gtp_game_score or None

    (This is normally just result.describe(), but we add more information if
     the scorers returned different results.)

    """
    def normalise_score(s):
        s = s.upper()
        if s.endswith(".0"):
            s = s[:-2]
        return s
    l = [result.describe()]

    if game_score is not None:
        sgf_result = result.sgf_result
        score_b = game_score.player_scores['b']
        score_w = game_score.player_scores['w']
        if ((score_b is not None and normalise_score(score_b) != sgf_result) or
            (score_w is not None and normalise_score(score_w) != sgf_result)):
            for score, code in ((score_b, result.player_b),
                                (score_w, result.player_w)):
                if score is not None:
                    l.append("%s final_score: %s" % (code, score))
    return "\n".join(l)


class _Gtp_backend(gameplay.Backend):
    """Concrete implementation of gameplay.Backend for GTP.

    This is instantiated and configured by its 'owning' Gtp_game.

    """

    def __init__(self, game_controller, board_size, komi):
        # A new _Gtp_backend is created for each game.
        # But this implementation is written to work correctly if it is used
        # in multiple games, anyway.

        self.gc = game_controller
        self.board_size = board_size
        self.komi = komi
        self.claim_allowed = {'b' : False, 'w' : False}
        self.allowed_scorers = []
        self.internal_scorer = False
        self.handicap_compensation = "no"
        self.handicap = None

    def start_new_game(self, board_size, komi):
        """Reset the engines' GTP game state (board size, contents, komi)."""
        assert board_size == self.board_size
        assert komi == self.komi
        self.gc.set_cautious_mode(False)
        for colour in "b", "w":
            self.gc.send_command(colour, "boardsize", str(board_size))
            self.gc.send_command(colour, "clear_board")
            self.gc.send_command(colour, "komi", str(komi))

    def end_game(self):
        self.gc.set_cautious_mode(True)

    def get_free_handicap(self, handicap):
        assert handicap == self.handicap
        vertices = self.gc.send_command(
            "b", "place_free_handicap", str(handicap))
        try:
            points = [move_from_vertex(vt, self.board_size)
                      for vt in vertices.split(" ")]
            if None in points:
                raise ValueError("response included 'pass'")
            if len(set(points)) < len(points):
                raise ValueError("duplicate point")
        except ValueError, e:
            raise BadGtpResponse(
                "invalid response from place_free_handicap command "
                "to %s: %s" % (self.gc.players["b"], e))
        return points

    def notify_free_handicap(self, points):
        vertices = [format_vertex(point) for point in points]
        self.gc.send_command("w", "set_free_handicap", *vertices)

    def notify_fixed_handicap(self, colour, handicap, points):
        assert handicap == self.handicap
        vertices = self.gc.send_command(colour, "fixed_handicap", str(handicap))
        try:
            seen_points = [move_from_vertex(vt, self.board_size)
                           for vt in vertices.split(" ")]
            if set(seen_points) != set(points):
                raise ValueError
        except ValueError:
            raise BadGtpResponse(
                "bad response from fixed_handicap command "
                "to %s: %s" % (self.gc.players[colour], vertices))

    def get_move(self, colour):
        if (self.claim_allowed[colour] and
            self.gc.known_command(colour, "gomill-genmove_ex")):
            genmove_command = ["gomill-genmove_ex", colour, "claim"]
            may_claim = True
        else:
            genmove_command = ["genmove", colour]
            may_claim = False
        try:
            raw_move = self.gc.send_command(colour, *genmove_command)
        except BadGtpResponse, e:
            return 'forfeit', str(e)
        move_s = raw_move.lower()
        if move_s == "resign":
            return 'resign', None
        if may_claim and move_s == "claim":
            return 'claim', None
        try:
            move = move_from_vertex(move_s, self.board_size)
        except ValueError:
            return 'forfeit', "attempted ill-formed move %s" % raw_move
        return 'move', move

    def get_last_move_comment(self, colour):
        comment = self.gc.maybe_send_command(colour, "gomill-explain_last_move")
        comment = sanitise_utf8(comment)
        if comment == "":
            comment = None
        return comment

    def notify_move(self, colour, move):
        vertex = format_vertex(move)
        try:
            self.gc.send_command(colour, "play", opponent_of(colour), vertex)
        except BadGtpResponse, e:
            if e.gtp_error_message == "illegal move":
                return 'reject', ("%s claims move %s is illegal"
                                  % (self.gc.players[colour], vertex))
            else:
                # If the game is over, this could be a channel error reported
                # by cautious mode; that's fine (see test_pass_and_exit())
                return 'error', str(e)
        return 'accept', None

    def _score_game_gtp(self):
        winners = []
        margins = []
        raw_scores = []
        for colour in self.allowed_scorers:
            final_score = self.gc.maybe_send_command(colour, "final_score")
            if final_score is None:
                continue
            raw_scores.append((colour, final_score))
            final_score = final_score.upper()
            if final_score == "0":
                winners.append(None)
                margins.append(0)
                continue
            if final_score.startswith("B+"):
                winners.append("b")
            elif final_score.startswith("W+"):
                winners.append("w")
            else:
                continue
            try:
                margin = float(final_score[2:])
                if margin <= 0:
                    margin = None
            except ValueError:
                margin = None
            margins.append(margin)
        scorers_disagreed = False
        if len(set(winners)) == 1:
            winner = winners[0]
            if len(set(margins)) == 1:
                margin = margins[0]
            else:
                margin = None
        else:
            if len(set(winners)) > 1:
                scorers_disagreed = True
            winner = None
            margin = None
        score = Gtp_game_score(winner, margin)
        score.scorers_disagreed = scorers_disagreed
        for colour, raw_score in raw_scores:
            score.player_scores[colour] = raw_score
        return score

    def score_game(self, board):
        if self.internal_scorer:
            game_score = Gtp_game_score.from_position(
                board, self.komi, self.handicap_compensation, self.handicap)
        else:
            game_score = self._score_game_gtp()
        return game_score


class Gtp_game(object):
    """Manage a single game between two GTP engines.

    Instantiate with:
      game_controller -- gtp_controller.Game_controller
      board_size      -- int
      komi            -- int or float (default 0)
      move_limit      -- int or None  (default None)

    Normal use:
      game = Gtp_game(...)
      Any combination of:
        game.set_game_id(...)
        game.use_internal_scorer() or game.allow_scorer(...)
        game.set_claim_allowed(...)
        game.set_move_callback(...)
      game.prepare()
      game.set_handicap(...) [optional]
      game.run()
      Any combination of:
        game.get_moves()
        game.describe_scoring()
        game.make_sgf()

    then retrieve the Game_result.

    If neither use_internal_scorer() nor allow_scorer() is called, the game
    won't be scored.

    The game controller's player codes are used to identify the players in game
    results, SGF files, and the error messages.


    Public attributes for reading:
      game_id         -- string or None
      result          -- Game_result (None before the game is complete)
      cpu_time_errors -- set of colours (None before the game is complete)

    cpu_time_errors indicates engines which claim to support CPU time reporting
    but reported an error. (This is provided to allow higher levels to use
    resource-usage cpu time for other engines, without doing so if
    gomill-cpu_time gives an error.)

    See Game_runner for the Go rules that are used, and details of move_limit.

    """

    def __init__(self, game_controller, board_size, komi=0.0, move_limit=None):
        self.game_controller = game_controller
        self.backend = _Gtp_backend(self.game_controller, board_size, komi)
        self.game_runner = gameplay.Game_runner(
            self.backend, board_size, komi, move_limit)
        self.game_runner.set_result_class(Game_result)
        self.game_id = None
        self.result = None
        self.cpu_time_errors = None

    ## Configuration API

    def set_game_id(self, game_id):
        """Specify a game id.

        game_id -- string

        The game id is reported in the game result, and used as a default game
        name in the SGF file.

        If you don't set it, it will have value None.

        """
        self.game_id = str(game_id)

    def use_internal_scorer(self, handicap_compensation='no'):
        """Set the scoring method to internal.

        handicap_compensation -- 'no' (default), 'short', or 'full'.

        The internal scorer uses area score, assuming all stones alive.
        See gameplay.score_game() for details.

        """
        self.backend.internal_scorer = True
        if handicap_compensation not in ('no', 'short', 'full'):
            raise ValueError("bad handicap_compensation value: %s" %
                             handicap_compensation)
        self.backend.handicap_compensation = handicap_compensation

    def allow_scorer(self, colour):
        """Allow the specified player to score the game.

        If this is called for both colours, both are asked to score.

        See 'details of scoring' in errors.rst for more information.

        """
        self.backend.allowed_scorers.append(colour)

    def set_claim_allowed(self, colour, b=True):
        """Allow the specified player to claim a win.

        This will have no effect if the engine doesn't implement
        gomill-genmove_ex.

        """
        self.backend.claim_allowed[colour] = bool(b)

    def set_move_callback(self, fn):
        """Specify a callback function to be called after every move.

        See gameplay.Game_runner.set_move_callback().

        """
        self.game_runner.set_move_callback(fn)


    ## Game-running API

    def prepare(self):
        """Initialise the engines' GTP game state (board size, contents, komi).

        Propagates BadGtpResponse if an engine returns a failure response to
        any of the initialisation commands.

        Propagates GtpChannelError if there is trouble communicating with an
        engine.

        (Switches the game controller to non-cautious mode.)

        """
        self.game_runner.prepare()

    def set_handicap(self, handicap, is_free):
        """Arrange for the game to be played at a handicap.

        handicap -- int (number of stones)
        is_free  -- bool

        Raises ValueError if the number of stones isn't valid (see GTP spec).

        Propagates BadGtpResponse if an engine returns an invalid or failure
        response to place_free_handicap, set_free_handicap, or fixed_handicap.

        Propagates GtpChannelError if there is trouble communicating with an
        engine.

        """
        self.backend.handicap = handicap
        self.game_runner.set_handicap(handicap, is_free)

    def run(self):
        """Run a complete game between the two players.

        Sets the 'result' and 'cpu_time_errors' attributes.

        Won't propagate BadGtpResponse (if engine returns an invalid or failure
        response, the game will be forfeited).

        Propagates GtpChannelError if there is trouble communicating with an
        engine before the result has been determined. Afterwards, sets errors
        aside; retrieve them with game_controller.describe_late_errors().

        Propagates any exceptions from any after-move callback.

        If an exception is propagated, 'result' will not be set, but
        get_moves() will reflect the moves which were completed.

        If no exception is propagated, the game controller will be left in
        cautious mode (otherwise it might be in either mode).

        """
        self.game_runner.run()
        self.result = self.game_runner.result
        self.result.set_players(self.game_controller.players)
        self.result.game_id = self.game_id
        cpu_times, self.cpu_time_errors = \
            self.game_controller.get_gtp_cpu_times()
        self.result.soft_update_cpu_times(cpu_times)

    def get_moves(self):
        """Retrieve a list of the moves played.

        Returns a list of tuples (colour, move, comment)
          move is a pair (row, col), or None for a pass

        Returns an empty list if run() has not been called.

        If the game ended due to an illegal move (or a move rejected by the
        other player), that move is not included (result.detail indicates what
        it was).

        """
        return self.game_runner.get_moves()

    def get_final_diagnostics(self):
        return self.game_runner.get_final_diagnostics()

    def get_game_score(self):
        """Retrieve scoring details from a passed-out game.

        Returns a Gtp_game_score.

        Returns None if the game was not passed out.

        """
        return self.game_runner.get_game_score()

    def describe_scoring(self):
        """Return a multiline string describing the game's scoring.

        This always includes the game result and detail, and may have
        additional information if the players disagreed or returned strange
        results.

        """
        return describe_scoring(self.result, self.get_game_score())

    def make_sgf(self):
        """Return an SGF description of the game.

        Returns an Sgf_game object.

        This adds the following to the result of Game_runner.make_sgf:
          PB PW
          GN     (if the game_id is set)

        It also adds the following to the last node's comment:
          describe_scoring() output

        """
        sgf_game = self.game_runner.make_sgf()
        root = sgf_game.get_root()
        for colour, prop in (('b', 'PB'), ('w', 'PW')):
            ed = self.game_controller.engine_descriptions[colour]
            root.set(prop, ed.get_short_description() or
                           self.game_controller.players[colour])
        if self.game_id:
            root.set('GN', self.game_id)
        last_node = sgf_game.get_last_node()
        if self.result is not None:
            last_node.add_comment_text(self.describe_scoring())
        return sgf_game

