"""Run a game between two GTP engines."""

import os

from gomill.gomill_common import *
from gomill import gtp_controller
from gomill import handicap_layout
from gomill import boards
from gomill import sgf_writer
from gomill.gtp_controller import BadGtpResponse, GtpChannelError

def format_float(f):
    """Format a Python float in a friendly way."""
    if f == int(f):
        return str(int(f))
    else:
        return str(f)

class Game_result(object):
    """Description of a game result.

    Public attributes:
      player_b            -- player code
      player_w            -- player code
      winning_colour      -- 'b', 'w', or None
      winning_player      -- player code or None
      sgf_result          -- string describing the game's result (for sgf RE)
      detail              -- additional information (string)
      cpu_times           -- map player code -> float or None or '?'.

    Winning colour and winning player are None for a jigo, unknown result, or
    void game.

    cpu_times are user time + system time. '?' means that gomill-cpu_time gave
    an error.

    Game_results are suitable for pickling.

    """

    # These are just to make the .state file more compact.

    def __getstate__(self):
        return (
            self.player_b,
            self.player_w,
            self.winning_colour,
            self.winning_player,
            self.sgf_result,
            self.detail,
            self.cpu_times,
            )

    def __setstate__(self, state):
        (self.player_b,
         self.player_w,
         self.winning_colour,
         self.winning_player,
         self.sgf_result,
         self.detail,
         self.cpu_times,
         ) = state

    def describe(self):
        """Return a short human-readable description of the result."""
        if self.winning_player is not None:
            if self.player_b == self.winning_player:
                losing_player = self.player_w
            else:
                losing_player = self.player_b
            s = "%s beat %s " % (self.winning_player, losing_player)
        else:
            s = "%s vs %s " % (self.player_b, self.player_w)
        s += self.sgf_result
        if self.detail is not None:
            s += " (%s)" % self.detail
        return s

    def __repr__(self):
        return "<Game_result: %s>" % self.describe()


class Game(object):
    """A single game between two GTP engines.

    Instantiate with:
      board_size -- int
      komi       -- float (default 0.0)
      move_limit -- int   (default 1000)

    The 'commands' values are lists of strings, as for subprocess.Popen.

    Normal use:

      game = Game(...)
      game.set_player_code('b', ...)
      game.set_player_code('w', ...)
      game.use_internal_scorer() or game.allow_scorer(...) [optional]
      game.set_move_callback...() [optional]
      game.set_player_subprocess('b', ...) or set_player_controller('b', ...)
      game.set_player_subprocess('w', ...) or set_player_controller('w', ...)
      game.ready('b')
      game.ready('w')
      game.request_engine_descriptions() [optional]
      game.set_handicap(...) [optional]
      game.run()
      game.close_players()
      game.make_sgf() or game.write_sgf(...) [optional]

    then retrieve the Game_result and moves.

    If neither use_internal_scorer() nor allow_scorer() is called, the game
    won't be scored.

    Public attributes for reading:
      players               -- map colour -> player code
      result                -- Game_result (None before the game is complete)
      moves                 -- list of tuples (colour, move, comment)
      engine_names          -- map player code -> string
      engine_descriptions   -- map player code -> string
      late_errors           -- list of strings

   Methods which communicate with engines may raise BadGtpResponse if the
   engine returns a failure response.

   Methods which communicate with engines will normally raise GtpChannelError
   if there is trouble communicating with the engine. But after the game result
   has been decided, they will set these errors aside; use the late_errors
   attribute to retrieve them.

   The late_errors attribute is set by close_players(); it includes errors set
   aside as above and also errors from closing (including failure responses
   from the final 'quit' command).


   This doesn't enforce any ko rule. It accepts self-capture moves.

   """

    def __init__(self, board_size, komi=0.0, move_limit=1000):
        self.players = {'b' : 'b', 'w' : 'w'}
        self.controllers = {}
        self.after_move_callback = None
        self.board_size = board_size
        self.komi = komi
        self.move_limit = move_limit
        self.allowed_scorers = []
        self.internal_scorer = False
        self.first_player = "b"
        self.engine_names = {}
        self.engine_descriptions = {}
        self.moves = []
        self.additional_sgf_props = []
        self.late_errors = []
        self.sgf_setup_stones = None
        self.result = None
        self.board = boards.Board(board_size)


    ## Configuration methods (callable before set_player_...)

    def set_player_code(self, colour, player_code):
        """Specify a player code.

        player_code -- short ascii string

        The player codes are used to identify the players in game results, sgf
        files, and the error messages.

        Setting these is optional but strongly encouraged. If not explicitly
        set, they will just be 'b' and 'w'.

        """
        self.players[colour] = str(player_code)

    def use_internal_scorer(self):
        """Set the scoring method to internal.

        The internal scorer uses area score, assuming all stones alive.

        """
        self.internal_scorer = True

    def allow_scorer(self, colour):
        """Allow the specified player to score the game.

        If this is called for both colours, the first player specified will be
        asked to score; if it doesn't support final-score, or final-score
        returns an error, the second engine will be asked.

        """
        self.allowed_scorers.append(colour)

    def set_move_callback(self, fn):
        """Specify a callback function to be called after every move.

        This function is called after each move is played, including passes but
        not resignations.

        It is passed three parameters: colour, move, board
          move is a pair (row, col), or None for a pass

        Treat the board parameter as read-only.

        Exceptions raised from the callback will be propagated unchanged out of
        run().

        """
        self.after_move_callback = fn


    ## Channel methods

    def set_player_controller(self, colour, controller):
        """Specify a player using a Gtp_controller.

        controller -- Gtp_controller

        """
        self.controllers[colour] = controller

    def set_player_subprocess(self, colour, command, **kwargs):
        """Specify the a player as a subprocess.

        command -- list of strings (as for subprocess.Popen)

        Additional keyword arguments are passed to the Subprocess_gtp_channel
        constructor.

        Propagates GtpChannelError if there's an error creating the
        subprocess.

        """
        try:
            channel = gtp_controller.Subprocess_gtp_channel(command, **kwargs)
        except GtpChannelError, e:
            raise GtpChannelError(
                "error starting subprocess for player %s:\n%s" %
                (self.players[colour], e))
        controller = gtp_controller.Gtp_controller(
            channel, "player %s" % self.players[colour])
        self.set_player_controller(colour, controller)

    def get_controller(self, colour):
        """Return the underlying Gtp_controller for the specified engine."""
        return self.controllers[colour]

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
        return self.controllers[colour].do_command(command, *arguments)

    def maybe_send_command(self, colour, command, *arguments):
        """Send the specified GTP command, if supported.

        Variant of send_command(): if the command isn't supported by the
        engine, or gives a failure response, returns None.

        """
        controller = self.controllers[colour]
        if controller.known_command(command):
            try:
                result = controller.do_command(command, *arguments)
            except BadGtpResponse:
                result = None
        else:
            result = None
        return result

    def known_command(self, colour, command):
        """Check whether the specified GTP command is supported."""
        return self.controllers[colour].known_command(command)

    def close_players(self):
        """Close both controllers (if they're open).

        Sets the late_errors attribute.

        If cpu times are not already set in the game result, sets them from the
        CPU usage of the engine subprocesses.

        """
        for colour in ("b", "w"):
            controller = self.controllers.get(colour)
            if controller is None:
                continue
            controller.safe_close()
            ru = controller.channel.resource_usage
            if (ru is not None and self.result is not None and
                self.result.cpu_times[self.players[colour]] is None):
                self.result.cpu_times[self.players[colour]] = \
                    ru.ru_utime + ru.ru_stime
            self.late_errors += controller.retrieve_error_messages()


    ## High-level methods

    def request_engine_descriptions(self):
        """Obtain the engines' name, version, and description by GTP.

        After you have called this, you can retrieve the results from the
        engine_names and engine_descriptions attributes.

        If this has been called, other methods will use the engine name and/or
        description when appropriate (ie, call this if you want proper engine
        names to appear in the SGF file).

        """

        def shorten_version(name, version):
            """Clean up redundant version strings."""
            if version.lower().startswith(name.lower()):
                version = version[len(name):].lstrip()
            # For MoGo's stupidly long version string
            a, b, c = version.partition(". Please read http:")
            if b:
                return a
            return version

        for colour in "b", "w":
            player = self.players[colour]
            desc = player
            name = player
            try:
                desc = name = self.send_command(colour, "name")
            except BadGtpResponse:
                pass
            try:
                version = self.send_command(colour, "version")
                version = shorten_version(name, version)
                desc = name + ":" + version
                name = name + ":" + version[:32].rstrip()
            except BadGtpResponse:
                pass
            self.engine_names[player] = name
            s = self.maybe_send_command(colour, "gomill-describe_engine")
            if s is not None:
                desc = s
            self.engine_descriptions[player] = desc

    def ready(self, colour, check_protocol_version=True):
        """Reset GTP game state for the player (board size, contents, komi).

        If check_protocol_version is true (which it is by default), rejects an
        engine that declares a GTP protocol version <> 2.

        """
        controller = self.controllers[colour]
        if check_protocol_version:
            controller.check_protocol_version()
        controller.do_command("boardsize", str(self.board_size))
        controller.do_command("clear_board")
        controller.do_command("komi", str(self.komi))

    def set_handicap(self, handicap, is_free):
        """Initialise the board position for a handicap.

        Raises ValueError if the number of stones isn't valid (see GTP spec).

        Raises BadGtpResponse if there's an invalid respone to
        place_free_handicap (doesn't check the response to fixed_handicap).

        """
        if is_free:
            max_points = handicap_layout.max_free_handicap_for_board_size(
                self.board_size)
            if not 2 <= handicap < max_points:
                raise ValueError
            vertices = self.send_command(
                "b", "place_free_handicap", str(handicap))
            try:
                points = [coords_from_vertex(vt, self.board_size)
                          for vt in vertices.split(" ")]
                if None in points:
                    raise ValueError("response included 'pass'")
                if len(set(points)) < len(points):
                    raise ValueError("duplicate point")
            except ValueError, e:
                raise BadGtpResponse(
                    "invalid response from place_free_handicap command "
                    "to %s: %s" % (self.players["b"], e))
            vertices = [format_vertex(coords) for coords in points]
            self.send_command("w", "set_free_handicap", *vertices)
        else:
            # May propagate ValueError
            points = handicap_layout.handicap_points(handicap, self.board_size)
            for colour in "b", "w":
                self.send_command(colour, "fixed_handicap", str(handicap))
        self.board.apply_setup(points, [], [])
        self.additional_sgf_props.append(('handicap', handicap))
        self.sgf_setup_stones = [("b", coords) for coords in points]
        self.first_player = "w"

    def _play_move(self, colour):
        opponent = opponent_of(colour)
        if self.known_command(colour, "gomill-genmove_claim"):
            genmove_command = "gomill-genmove_claim"
            may_claim = True
        else:
            genmove_command = "genmove"
            may_claim = False
        try:
            move_s = self.send_command(colour, genmove_command, colour).lower()
        except BadGtpResponse, e:
            self.winner = opponent
            self.forfeited = True
            self.forfeit_reason = str(e)
            return
        if move_s == "resign":
            self.winner = opponent
            self.seen_resignation = True
            return
        if may_claim and move_s == "claim":
            self.winner = colour
            self.seen_claim = True
            return
        try:
            move = coords_from_vertex(move_s, self.board_size)
        except ValueError:
            self.winner = opponent
            self.forfeited = True
            self.forfeit_reason = "%s attempted ill-formed move %s" % (
                self.players[colour], move_s)
            return
        comment = self.maybe_send_command(colour, "gomill-explain_last_move")
        if comment == "":
            comment = None
        if move is not None:
            row, col = move
            try:
                self.board.play(row, col, colour)
            except ValueError:
                self.winner = opponent
                self.forfeited = True
                self.forfeit_reason = (
                    "%s attempted move to occupied point %s" % (
                    self.players[colour], move_s))
                return
        if move is None:
            self.pass_count += 1
        else:
            self.pass_count = 0
        self.moves.append((colour, move, comment))
        if self.after_move_callback:
            self.after_move_callback(colour, move, self.board)
        try:
            self.send_command(opponent, "play", colour, move_s)
        except BadGtpResponse, e:
            # we assume the move was illegal, so 'colour' should lose
            self.winner = opponent
            self.forfeited = True
            self.forfeit_reason = str(e)

    def _handle_pass_pass(self):
        def ask(colour):
            final_score = self.maybe_send_command(colour, "final_score")
            if final_score is None:
                return False
            final_score = final_score.upper()
            if final_score == "0":
                self.margin = 0
                return True
            if final_score.startswith("B+"):
                self.winner = "b"
            elif final_score.startswith("W+"):
                self.winner = "w"
            else:
                return False
            try:
                self.margin = float(final_score[2:])
            except ValueError:
                return False
            return True
        if self.internal_scorer:
            score = self.board.area_score() - self.komi
            if score > 0:
                self.winner = "b"
                self.margin = score
            elif score < 0:
                self.winner = "w"
                self.margin = -score
            else:
                self.margin = 0
        else:
            for colour in self.allowed_scorers:
                if ask(colour):
                    break

    def run(self):
        """Run a complete game between the two players.

        Sets self.moves and self.result.

        Sets CPU times in the game result if available via GTP.

        """
        self.pass_count = 0
        self.winner = None
        self.seen_resignation = False
        self.seen_claim = False
        self.forfeited = False
        self.hit_move_limit = False
        self.margin = None
        self.forfeit_reason = None
        player = self.first_player
        move_count = 0
        while move_count < self.move_limit:
            self._play_move(player)
            if self.pass_count == 2:
                self._handle_pass_pass()
                break
            if self.winner is not None:
                break
            player = opponent_of(player)
            move_count += 1
        else:
            self.hit_move_limit = True
        self.calculate_result()
        self.calculate_cpu_times()

    def fake_run(self, winner):
        """Set state variables as if the game had been run (for testing).

        You don't need to use set_player_... to call this.

        winner -- 'b' or 'w'

        """
        self.winner = winner
        self.seen_resignation = False
        self.seen_claim = False
        self.forfeited = False
        self.hit_move_limit = False
        self.margin = 2
        self.forfeit_reason = None
        self.calculate_result()

    def calculate_result(self):
        """Set self.result.

        You shouldn't normally call this directly.

        """
        result = Game_result()
        result.player_b = self.players['b']
        result.player_w = self.players['w']
        result.winning_colour = self.winner
        result.winning_player = self.players.get(self.winner)
        result.detail = None
        result.cpu_times = {result.player_b : None, result.player_w : None}
        if self.hit_move_limit:
            result.sgf_result = "Void"
            result.detail = "hit move limit"
        elif self.seen_resignation:
            result.sgf_result = "%s+R" % self.winner.upper()
        elif self.seen_claim:
            result.sgf_result = "%s+C" % self.winner.upper()
        elif self.forfeited:
            result.sgf_result = "%s+F" % self.winner.upper()
            result.detail = "forfeit: %s" % self.forfeit_reason
        elif self.margin == 0:
            result.sgf_result = "0"
        elif self.margin is not None:
            result.sgf_result = "%s+%s" % (self.winner.upper(),
                                           format_float(self.margin))
        elif self.winner is None:
            result.sgf_result = "?"
            result.detail = "no score reported"
        else:
            # Players returned something like 'B+?'
            result.sgf_result = "%s+F" % self.winner.upper()
            result.detail = "unknown margin/reason"
        self.result = result

    def calculate_cpu_times(self):
        """Set CPU times in self.result.

        You shouldn't normally call this directly.

        """
        # The ugliness with cpu_time '?' is to avoid using the cpu time reported
        # by channel close() for engines which claim to support gomill-cpu_time
        # but give an error.
        for colour in ('b', 'w'):
            cpu_time = None
            controller = self.controllers[colour]
            if controller.safe_known_command('gomill-cpu_time'):
                try:
                    s = controller.safe_do_command('gomill-cpu_time')
                    cpu_time = float(s)
                except (BadGtpResponse, ValueError, TypeError):
                    cpu_time = "?"
            self.result.cpu_times[self.players[colour]] = cpu_time

    def make_sgf(self, game_end_message=None):
        """Return an SGF description of the game.

        Returns an Sgf_game object.

        game_end_message -- optional string to put in the final comment.

        If game_end_message is specified, it appears before the text describing
        'late errors'.

        """
        sgf_game = sgf_writer.Sgf_game(self.board_size)
        sgf_game.set('komi', self.komi)
        sgf_game.set('application', "gomill:?")
        for prop, value in self.additional_sgf_props:
            sgf_game.set(prop, value)
        sgf_game.add_date()
        if self.engine_names:
            sgf_game.set('black-player', self.engine_names[self.players['b']])
            sgf_game.set('white-player', self.engine_names[self.players['w']])
        if self.sgf_setup_stones:
            sgf_game.add_setup_stones(self.sgf_setup_stones)
        for colour, move, comment in self.moves:
            sgf_game.add_move(colour, move, comment)
        if self.result is not None:
            sgf_game.set('result', self.result.sgf_result)
            sgf_game.add_final_comment(self.result.describe())
        if game_end_message is not None:
            sgf_game.add_final_comment(game_end_message)
        if self.late_errors:
            sgf_game.add_final_comment("\n".join(self.late_errors))
        return sgf_game

    def write_sgf(self, pathname, game_end_message=None):
        """Write an SGF description of the game to the specified pathname."""
        sgf_game = self.make_sgf(game_end_message)
        f = open(pathname, "w")
        f.write(sgf_game.as_string())
        f.close()

