"""Run a game between two GTP engines."""

from gomill_common import *
from gomill import gtp_controller
from gomill import boards
from gomill import sgf_writer
from gomill.gtp_controller import (
    GtpProtocolError, GtpTransportError, GtpEngineError)

def format_gtp_float(f):
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

    """
    def describe(self):
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

class Game(object):
    """A single game between two GTP engines.

    Instantiate with:
      players    -- map colour -> player code
      commands   -- map colour -> command used to launch the program
      board_size -- int
      komi       -- float
      move_limit -- int

    Player codes are short strings used to identify the players in error
    messages and the game result.

    The 'commands' values are lists of strings, as for subprocess.Popen.

    Normal use:

      game = Game(...)
      game.use_internal_scorer() or game.use_players_to_score(...)
      game.start_players()
      game.request_engine_descriptions() [optional]
      game.run()
      game.close_players()
      game.make_sgf()

    then retrieve the Game_result and moves.

    Public attributes for reading:
      players               -- map colour -> player code (as passed in)
      result                -- Game_result
      moves                 -- list of tuples (colour, move, comment)
      engine_names          -- map colour -> string
      engine_descriptions   -- map colour -> string

   Methods which communicate with engines may raise GtpTransportError or
   GtpProtocolError (eg if the engine has gone away.)

   """

    def __init__(self, players, commands, board_size, komi, move_limit):
        self.players = players
        self.commands = commands
        self.board_size = board_size
        self.komi = komi
        self.move_limit = move_limit
        self.moves = []
        self.result = None
        self.board = boards.Board(board_size)
        self.internal_scorer = False
        self.player_scorers = []
        self.engine_names = {'b' : "unknown", 'w' : "unknown"}
        self.engine_descriptions = {'b' : "unknown", 'w' : "unknown"}
        self.engine_resource_usage = {'b' : None, 'w' : None}
        self.gtp_translations = {'b' : {}, 'w' : {}}

    def use_internal_scorer(self, b=True):
        """Set the scoring method to internal.

        The internal scorer uses area score, assuming all stones alive.

        """
        self.internal_scorer = True

    def use_players_to_score(self, preferred_scorers=None):
        """Specify which players' scores to trust.

        The internal scorer uses area score, assuming all stones alive.

        """
        if preferred_scorers is None:
            self.player_scorers = ['b', 'w']
        else:
            self.player_scorers = []
            for player in preferred_scorers:
                if player == self.players['b']:
                    self.player_scorers.append('b')
                if player == self.players['w']:
                    self.player_scorers.append('w')

    def set_gtp_translations(self, translations):
        """Set GTP command translations.

        translations -- map colour -> (map command string -> command string)

        """
        self.gtp_translations = translations

    def _translate_gtp_command(self, colour, command):
        return self.gtp_translations[colour].get(command, command)

    def _send_command(self, colour, command, arguments):
        try:
            response = self.controller.do_command(colour, command, *arguments)
        except GtpEngineError, e:
            raise GtpEngineError(
                "error from command '%s' to player %s: %s" %
                (command, self.players[colour], e))
        except GtpTransportError, e:
            raise GtpTransportError(
                "transport error sending command '%s' to player %s: %s" %
                (command, self.players[colour], e))
        except GtpProtocolError, e:
            raise GtpProtocolError(
                "protocol error sending command '%s' to player %s: %s" %
                (command, self.players[colour], e))
        return response

    def send_command(self, colour, command, *arguments):
        """Send the specified GTP command to one of the players.

        colour    -- player to talk to ('b' or 'w')
        command   -- gtp command (list of strings)
        arguments -- gtp arguments (strings)

        Returns the response as a string.

        Raises GtpEngineError if the engine returns an error response.

        """
        command = self._translate_gtp_command(colour, command)
        return self._send_command(colour, command, arguments)

    def maybe_send_command(self, colour, command, *arguments):
        """Send the specified GTP command, if supported.

        Variant of send_command(): if the command isn't supported by the engine,
        or gives an error response, returns None.

        """
        command = self._translate_gtp_command(colour, command)
        if self.controller.known_command(colour, command):
            try:
                result = self._send_command(colour, command, arguments)
            except GtpEngineError:
                result = None
        else:
            result = None
        return result

    def known_command(self, colour, command):
        """Check whether the specified GTP command is supported."""
        command = self._translate_gtp_command(colour, command)
        return self.controller.known_command(colour, command)

    def start_players(self):
        """Start the engine subprocesses."""
        self.controller = gtp_controller.Gtp_controller_protocol()
        for colour in ("b", "w"):
            try:
                channel = gtp_controller.Subprocess_gtp_channel(
                    self.commands[colour])
            except GtpTransportError, e:
                raise GtpTransportError("error creating player %s:\n%s" %
                                        (self.players[colour], e))
            self.controller.add_channel(colour, channel)
            self.send_command(colour, "boardsize", str(self.board_size))
            self.send_command(colour, "clear_board")
            self.send_command(colour, "komi", str(self.komi))

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
            except GtpEngineError:
                pass
            try:
                version = self.send_command(colour, "version")
                version = shorten_version(name, version)
                desc = name + ":" + version
                name = name + ":" + version[:32].rstrip()
            except GtpEngineError:
                pass
            self.engine_names[player] = name
            s = self.maybe_send_command(colour, "gomill-describe_engine")
            if s is not None:
                desc = s
            self.engine_descriptions[player] = desc

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
        except GtpEngineError, e:
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
        try:
            self.send_command(opponent, "play", colour, move_s)
        except GtpEngineError, e:
            # we assume the move was illegal, so 'colour' should lose
            self.winner = opponent
            self.forfeited = True
            self.forfeit_reason = str(e)

    def _handle_pass_pass(self):
        def ask(colour):
            try:
                final_score = self.send_command(colour, "final_score")
            except GtpEngineError:
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
            for colour in self.player_scorers:
                if ask(colour):
                    break

    def run(self):
        """Run a complete game between the two players.

        Sets game.moves.

        """
        self.pass_count = 0
        self.winner = None
        self.seen_resignation = False
        self.seen_claim = False
        self.forfeited = False
        self.hit_move_limit = False
        self.margin = None
        self.forfeit_reason = None
        player = "b"
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

        You don't need to use start_players to call this.

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
        self.result.cpu_times = {'b' : None, 'w' : None}

    def calculate_result(self):
        """Set self.result."""
        result = Game_result()
        result.player_b = self.players['b']
        result.player_w = self.players['w']
        result.winning_colour = self.winner
        result.winning_player = self.players.get(self.winner)
        result.detail = None
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
                                           format_gtp_float(self.margin))
        elif self.winner is None:
            result.sgf_result = "?"
            result.detail = "no score reported"
        else:
            # Players returned something like 'B+?'
            result.sgf_result = "%s+F" % self.winner.upper()
            result.detail = "unknown margin/reason"
        self.result = result

    def calculate_cpu_times(self):
        """Set CPU times in self.result."""
        # The ugliness with cpu_time '?' is to avoid using the cpu time reported
        # by channel close() for engines which claim to support gomill-cpu_time
        # but give an error.
        self.result.cpu_times = {}
        for colour in ('b', 'w'):
            if self.known_command(colour, 'gomill-cpu_time'):
                try:
                    s = self.send_command(colour, 'gomill-cpu_time')
                    cpu_time = float(s)
                except (GtpEngineError, ValueError):
                    cpu_time = "?"
            else:
                cpu_time = None
            self.result.cpu_times[self.players[colour]] = cpu_time

    def close_players(self):
        """Close both channels (if they're open).

        Catches arbitrary exceptions and reraises as StandardError with a
        description.

        If cpu times are not already set in the game result, sets them from the
        CPU usage of the engine subprocesses.

        """
        errors = []
        for colour in ("b", "w"):
            if self.controller.has_channel(colour):
                try:
                    # Mogo doesn't behave well if we just close its input,
                    # so try to quit first.
                    self.controller.do_command(colour, "quit")
                except StandardError:
                    pass
                try:
                    ru = self.controller.close_channel(colour)
                except StandardError, e:
                    errors.append("error closing player %s:\n%s" % (colour, e))
                else:
                    if (ru is not None and self.result is not None and
                        self.result.cpu_times[self.players[colour]] is None):
                        self.result.cpu_times[self.players[colour]] = \
                            ru.ru_utime + ru.ru_stime
        if errors:
            raise StandardError("\n".join(errors))

    def make_sgf(self):
        """Return an SGF description of the game.

        Returns an Sgf_game object.

        """
        sgf_game = sgf_writer.Sgf_game(self.board_size)
        sgf_game.set('komi', self.komi)
        sgf_game.set('application', "gokit:?")
        sgf_game.add_date()
        if self.engine_names:
            sgf_game.set('black-player', self.engine_names[self.players['b']])
            sgf_game.set('white-player', self.engine_names[self.players['w']])
        for colour, move, comment in self.moves:
            sgf_game.add_move(colour, move, comment)
        if self.result is not None:
            sgf_game.set('result', self.result.sgf_result)
            sgf_game.add_final_comment(self.result.describe())
        return sgf_game

    def write_sgf(self, pathname):
        """Write an SGF description of the game to the specified pathname."""
        sgf_game = self.make_sgf()
        f = open(pathname, "w")
        f.write(sgf_game.as_string())
        f.close()
