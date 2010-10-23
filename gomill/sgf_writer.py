"""Write SGF files.

Methods taking 'sgf value string' parameters expect 8-bit utf-8 strings.

Makes no attempt to compress point lists.

"""

import datetime

friendly_idents = {
    'komi'         : 'KM',
    'application'  : 'AP',
    'black-player' : 'PB',
    'white-player' : 'PW',
    'result'       : 'RE',
    'game-name'    : 'GN',
    'event'        : 'EV',
    'round'        : 'RO',
    'game-comment' : 'GC',
    'root-comment' : 'C',
    'handicap'     : 'HA',
    }

def escape(s):
    return s.replace("\\", "\\\\").replace("]", "\\]")

def block_format(l, width=79):
    lines = []
    line = ""
    for s in l:
        if len(line) + len(s) > width:
            lines.append(line)
            line = ""
        line += s
    if line:
        lines.append(line)
    return "\n".join(lines)

class Sgf_game(object):
    """Data to write to an SGF file

    Instantiate with the board size.

    """

    def __init__(self, size):
        if not 1 <= size <= 25:
            raise ValueError("Sgf_game: size must be in 1..25")
        self.size = size
        self.setup_stones = {'b' : set(), 'w' : set()}
        self.moves = []
        self.root_properties = {
            'GM' : '1',
            'FF' : '4',
            'SZ' : str(size),
            'CA' : 'utf-8',
            }

    def sgf_point(self, move):
        """Convert (row, col) to sgf letter-pair."""
        row, col = move
        row = self.size - row - 1
        col_s = "abcdefghijklmnopqrstuvwxy"[col]
        row_s = "abcdefghijklmnopqrstuvwxy"[row]
        return col_s + row_s

    def set_root_property(self, identifier, value):
        """Specify a property for the root node.

        identifier -- string (eg 'KM')
        value      -- sgf value string

        """
        self.root_properties[identifier] = str(value)

    def set(self, name, value):
        """Specify a property using a more verbose naming scheme.

        name  -- key from 'friendly_idents' above
        value -- sgf value string

        """
        self.set_root_property(friendly_idents[name], value)

    def add_date(self, date=None):
        """Set the DT property.

        date -- datetime.date (defaults to today)

        """
        if date is None:
            date = datetime.date.today()
        self.set_root_property('DT', date.strftime("%Y-%m-%d"))

    def add_move(self, colour, move, comment=None):
        """Add a single move, with an optional comment.

        colour  -- 'b' or 'w'
        move    -- (row, col), or None for pass
        comment -- sgf value string (optional)

        """
        colour = colour.upper()
        if colour not in ('B', 'W'):
            raise ValueError
        if move is None:
            # Prefer 'tt' where possible (FF[3] and older); '' is FF[4]
            if self.size <= 19:
                move_s = "tt"
            else:
                move_s = ""
        else:
            move_s = self.sgf_point(move)
        self.moves.append(("%s[%s]" % (colour, move_s), comment))

    def add_setup_stones(self, stones):
        """Specify setup stones for the root node.

        stones -- list of pairs (colour, (row, col))

        You can call this more than once.

        Doesn't check for illegal placements (ie, specifying a point as being
        both black and white).

        """
        for colour, move in stones:
            try:
                st = self.setup_stones[colour]
            except KeyError:
                raise ValueError
            st.add(self.sgf_point(move))

    def add_final_comment(self, comment):
        """Add a comment to the last node.

        comment -- sgf value string

        """
        if self.moves:
            move, existing = self.moves[-1]
            if not existing:
                new = comment
            else:
                new = existing + "\n\n" + comment
            self.moves[-1] = (move, new)
        else:
            existing = self.root_properties.get('C')
            if existing is None:
                self.set_root_property('C', comment)
            else:
                self.set_root_property('C', existing + "\n\n" + comment)

    def _finalise(self):
        # Add next-player when known and appropriate
        if self.moves and ('PL' not in self.root_properties):
            move, comment = self.moves[0]
            first_player = move[0]
            has_handicap = ('HA' in self.root_properties)
            if self.setup_stones['w']:
                specify_pl = True
            elif self.setup_stones['b'] and not has_handicap:
                specify_pl = True
            elif not has_handicap and first_player == 'W':
                specify_pl = True
            elif has_handicap and first_player == 'B':
                specify_pl = True
            else:
                specify_pl = False
            if specify_pl:
                self.set_root_property('PL', first_player)

    def as_string(self):
        """Return the SGF data as a string.

        Returns an 8-bit utf-8 string.

        (By default there will be a CA[utf-8] root property; if you change
        that, it's up to you to recode the returned result to match.)

        """
        self._finalise()
        l = []
        l.append("(;")
        for identifier, value in sorted(self.root_properties.items()):
            l.append("%s[%s]" % (identifier, escape(value)))
        for colour in ('b', 'w'):
            if self.setup_stones[colour]:
                l.append("A%s" % colour.upper())
                for move in sorted(self.setup_stones[colour]):
                    l.append("[%s]" % move)
        for move, comment in self.moves:
            l.append(";" + move)
            if comment:
                l.append("C[%s]" % escape(comment))
        l.append(")\n")
        return block_format(l)
