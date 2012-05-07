"""Run a game between two GTP engines."""

from gomill.utils import *
from gomill.common import *
from gomill import gameplay
from gomill import gtp_controller
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
      cpu_times      -- map player code -> float or None or '?'

    Call set_players() before using these.

    Winning/losing player are None for a jigo, unknown result, or void game.

    cpu_times are user time + system time. '?' means that gomill-cpu_time gave
    an error.

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
         self.cpu_times,
         ) = state
        self.players = {'b' : self.player_b, 'w' : self.player_w}
        self.winning_player = self.players.get(self.winning_colour)
        self.is_jigo = (self.sgf_result == "0")

    def soft_update_cpu_times(self, cpu_times):
        """Update the cpu_times dict.

        cpu_times -- dict colour -> float or None or '?'

        If a value is already set (not None), this method doesn't change it.

        """
        for colour in ('b', 'w'):
            if self.cpu_times[self.players[colour]] is not None:
                continue
            self.cpu_times[self.players[colour]] = cpu_times[colour]

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

    This is instantiated and configured by its 'owning' Game.

    """

    def __init__(self, game_controller):
        # A new _Gtp_backend is created for each game.
        # But this implementation is written to work correctly if it is used
        # in multiple games, anyway.

        self.gc = game_controller
        self.claim_allowed = {'b' : False, 'w' : False}
        self.allowed_scorers = []
        self.internal_scorer = False
        self.handicap_compensation = "no"

        # We find out these from the Game_runner (from start_new_game and the
        # handicap methods). We remember komi and handicap for the sake of the
        # internal scorer.
        self.board_size = None
        self.komi = None
        self.handicap = None

    def start_new_game(self, board_size, komi):
        """Reset the engines' GTP game state (board size, contents, komi)."""
        self.board_size = board_size
        self.komi = komi
        self.handicap = None
        for colour in "b", "w":
            self.gc.send_command(colour, "boardsize", str(board_size))
            self.gc.send_command(colour, "clear_board")
            self.gc.send_command(colour, "komi", str(komi))

    def get_free_handicap(self, handicap):
        self.handicap = handicap
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
        self.handicap = handicap
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


class Game(object):
    """A single game between two GTP engines.

    Instantiate with:
      board_size -- int
      komi       -- int or float (default 0)
      move_limit -- int   (default 1000)

    Normal use:

      game = Game(...)
      game.set_player_code('b', ...)
      game.set_player_code('w', ...)
      game.use_internal_scorer() or game.allow_scorer(...) [optional]
      game.set_move_callback...() [optional]
      game.set_player_subprocess('b', ...) or set_player_controller('b', ...)
      game.set_player_subprocess('w', ...) or set_player_controller('w', ...)
      game.request_engine_descriptions() [optional]
      game.ready()
      game.set_handicap(...) [optional]
      game.run()
      game.close_players()
      game.make_sgf() or game.write_sgf(...) [optional]

    then retrieve the Game_result and moves.

    If neither use_internal_scorer() nor allow_scorer() is called, the game
    won't be scored.

    Public attributes for reading:
      players               -- map colour -> player code
      game_id               -- string or None
      result                -- Game_result (None before the game is complete)
      moves                 -- list of tuples (colour, move, comment)
                               move is a pair (row, col), or None for a pass
      engine_names          -- map player code -> string
      engine_descriptions   -- map player code -> string

    Methods which communicate with engines may raise BadGtpResponse if the
    engine returns a failure response.

    Methods which communicate with engines will normally raise GtpChannelError
    if there is trouble communicating with the engine. But after the game result
    has been decided, they will set these errors aside; retrieve them with
    describe_late_errors().

    This enforces a simple ko rule, but no superko rule. It accepts self-capture
    moves.

    """

    def __init__(self, board_size, komi=0.0, move_limit=1000):
        self.game_controller = gtp_controller.Game_controller()
        self.backend = _Gtp_backend(self.game_controller)
        self.game_runner = gameplay.Game_runner(
            self.backend, board_size, komi, move_limit)
        self.game_runner.set_result_class(Game_result)
        self.game_id = None
        self.result = None

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

        """
        self.backend.allowed_scorers.append(colour)

    def set_claim_allowed(self, colour, b=True):
        """Allow the specified player to claim a win.

        This will have no effect if the engine doesn't implement
        gomill-genmove_ex.

        """
        self.backend.claim_allowed[colour] = bool(b)

    def set_move_callback(self, fn):
        self.game_runner.set_move_callback(fn)


    ## Game-controller API

    @property
    def players(self):
        return self.game_controller.players

    @property
    def engine_names(self):
        return self.game_controller.engine_names

    @property
    def engine_descriptions(self):
        return self.game_controller.engine_descriptions

    def set_player_code(self, colour, player_code):
        self.game_controller.set_player_code(colour, player_code)

    def close_players(self):
        """Close both controllers (if they're open).

        Retrieves the late errors for describe_late_errors().

        If cpu times are not already set in the game result, sets them from the
        CPU usage of the engine subprocesses.

        """
        self.game_controller.close_players()
        if self.result is not None:
            self.result.soft_update_cpu_times(
                self.game_controller.get_resource_usage_cpu_times())

    def send_command(self, colour, command, *arguments):
        """Send the specified GTP command to one of the players.

        colour    -- player to talk to ('b' or 'w')
        command   -- gtp command name (string)
        arguments -- gtp arguments (strings)

        Returns the response as a string.

        Raises BadGtpResponse if the engine returns a failure response.

        You can use this at any time between set_player_...() and
        close_players().

        """
        return self.game_controller.send_command(colour, command, *arguments)

    def describe_late_errors(self):
        return self.game_controller.describe_late_errors()

    def set_player_controller(self, colour, controller,
                              check_protocol_version=True):
        self.game_controller.set_player_controller(
            colour, controller, check_protocol_version)

    def set_player_subprocess(self, colour, command,
                              check_protocol_version=True, **kwargs):
        self.game_controller.set_player_subprocess(
            colour, command, check_protocol_version, **kwargs)

    def get_controller(self, colour):
        """Return the Gtp_controller for the specified colour."""
        return self.game_controller.get_controller(colour)

    def request_engine_descriptions(self):
        """Obtain the engines' name, version, and description by GTP.

        After you have called this, you can retrieve the results from the
        engine_names and engine_descriptions attributes.

        If this has been called, other methods will use the engine name and/or
        description when appropriate (ie, call this if you want proper engine
        names to appear in the SGF file).

        """
        self.game_controller.request_engine_descriptions()


    ## Game-running API

    @property
    def moves(self):
        return self.game_runner.moves

    def ready(self):
        """Initialise the engines' GTP game state (board size, contents, komi).

        May propagate GtpChannelError or BadGtpResponse.

        """
        self.game_runner.prepare()

    def set_handicap(self, handicap, is_free):
        """Arrange for the game to be played at a handicap.

        handicap -- int (number of stones)
        is_free  -- bool

        Raises ValueError if the number of stones isn't valid (see GTP spec).

        Raises BadGtpResponse if there's an invalid or failure response to
        place_free_handicap, set_free_handicap, or fixed_handicap.

        May propagate GtpChannelError.

        """
        self.game_runner.set_handicap(handicap, is_free)

    def run(self):
        """Run a complete game between the two players.

        Sets the 'result' and 'moves' attributes.

        If a move is illegal, or the other player rejects it, it is not
        included in 'moves' (result.detail indicates what the move was).

        May propagate GtpChannelError or BadGtpResponse.

        Propagates any exceptions from any after-move callback.

        If an exception is propagated, 'moves' will reflect the moves made so
        far, and 'result' will not be set.

        """
        self.game_runner.run()
        self.result = self.game_runner.result
        self.result.set_players(self.players)
        self.result.game_id = self.game_id
        self.result.soft_update_cpu_times(
            self.game_controller.get_gtp_cpu_times())

    def describe_scoring(self):
        """Return a multiline string describing the game's scoring.

        This always includes the game result, and may have additional
        information if the players disagreed or returned strange results.

        """
        return describe_scoring(self.result,
                                self.game_runner.get_game_score())

    def make_sgf(self, game_end_message=None):
        """Return an SGF description of the game.

        Returns an Sgf_game object.

        game_end_message -- optional string to put in the final comment.

        This adds the following to the result of Game_runner.make_sgf:
          PB PW  (if request_engine_descriptions() was called)
          GN     (if the game_id is set)

        It also adds the following to the last node's comment:
          describe_scoring() output
          any game_end_message
          describe_late_errors() output

        """
        sgf_game = self.game_runner.make_sgf()
        root = sgf_game.get_root()
        if self.engine_names:
            root.set('PB', self.engine_names[self.players['b']])
            root.set('PW', self.engine_names[self.players['w']])
        if self.game_id:
            root.set('GN', self.game_id)
        last_node = sgf_game.get_last_node()
        if self.result is not None:
            last_node.add_comment_text(self.describe_scoring())
        if game_end_message is not None:
            last_node.add_comment_text(game_end_message)
        late_error_messages = self.describe_late_errors()
        if late_error_messages is not None:
            last_node.add_comment_text(late_error_messages)
        return sgf_game

    def write_sgf(self, pathname, game_end_message=None):
        """Write an SGF description of the game to the specified pathname."""
        sgf_game = self.make_sgf(game_end_message)
        f = open(pathname, "w")
        f.write(sgf_game.serialise())
        f.close()

