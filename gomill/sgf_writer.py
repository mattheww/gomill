"""Write SGF files."""

import datetime

friendly_idents = {
    'komi'         : 'KM',
    'application'  : 'AP',
    'black-player' : 'PB',
    'white-player' : 'PW',
    'result'       : 'RE',
    'event'        : 'EV',
    'round'        : 'RO',
    'game-comment' : 'GC',
    'root-comment' : 'C',
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
    def __init__(self, size):
        if not 1 <= size <= 25:
            raise ValueError("Sgf_game: size must be in 1..25")
        self.size = size
        self.moves = []
        self.root_properties = {
            'GM' : '1',
            'FF' : '4',
            'SZ' : str(size),
            }

    def set_root_property(self, identifier, value):
        self.root_properties[identifier] = str(value)

    def add_date(self, date=None):
        if date is None:
            date = datetime.date.today()
        self.set_root_property('DT', date.strftime("%Y-%m-%d"))

    def set(self, name, value):
        self.set_root_property(friendly_idents[name], value)

    def add_move(self, colour, move, comment=None):
        colour = colour.upper()
        if colour not in ('B', 'W'):
            raise ValueError
        if move is None:
            # Prefer 'tt' (FF[3] and older); '' is FF[4]
            if self.size <= 19:
                move_s = "tt"
            else:
                move_s = ""
        else:
            row, col = move
            row = self.size - row - 1
            col_s = "abcdefghijklmnopqrstuvwxy"[col]
            row_s = "abcdefghijklmnopqrstuvwxy"[row]
            move_s = col_s + row_s
        self.moves.append(("%s[%s]" % (colour, move_s), comment))

    def add_final_comment(self, s):
        if self.moves:
            move, comment = self.moves[-1]
            if not comment:
                comment = s
            else:
                comment += "\n\n" + s
            self.moves[-1] = (move, comment)
        else:
            comment = self.root_properties.get('C')
            if comment is not None:
                self.set_root_property('C', comment + "\n\n" + s)
            else:
                self.set_root_property('C', s)

    def as_string(self):
        l = []
        l.append("(;")
        for identifier, value in sorted(self.root_properties.items()):
            l.append("%s[%s]" % (identifier, escape(value)))
        for move, comment in self.moves:
            l.append(";" + move)
            if comment:
                l.append("C[%s]" % escape(comment))
        l.append(")\n")
        return block_format(l)
