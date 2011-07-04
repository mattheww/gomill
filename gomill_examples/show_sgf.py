"""Show the position from an SGF file.

This demonstrates the sgf_reader and ascii_boards modules.

"""

import sys
from optparse import OptionParser

from gomill import sgf_reader
from gomill import ascii_boards

def show_sgf_file(pathname, move_number):
    f = open(pathname)
    sgf_src = f.read()
    f.close()
    try:
        sgf_game = sgf_reader.sgf_game_from_string(sgf_src)
    except ValueError:
        raise StandardError("bad sgf file")

    try:
        board, moves = sgf_reader.get_setup_and_moves(sgf_game)
    except ValueError, e:
        raise StandardError(str(e))
    if move_number is not None:
        move_number = max(0, move_number-1)
        moves = moves[:move_number]

    for colour, coords in moves:
        if coords is None:
            continue
        row, col = coords
        try:
            board.play(row, col, colour)
        except ValueError:
            raise StandardError("illegal move in sgf file")

    print ascii_boards.render_board(board)
    print

_description = """\
Show the position from an SGF file. If a move number is specified, the position
before that move is shown (this is to match the behaviour of GTP loadsgf).
"""

def main(argv):
    parser = OptionParser(usage="%prog <filename> [move number]",
                          description=_description)
    opts, args = parser.parse_args(argv)
    if not args:
        parser.error("not enough arguments")
    pathname = args[0]
    if len(args) > 2:
        parser.error("too many arguments")
    if len(args) == 2:
        try:
            move_number = int(args[1])
        except ValueError:
            parser.error("invalid integer value: %s" % args[1])
    else:
        move_number = None
    try:
        show_sgf_file(pathname, move_number)
    except Exception, e:
        print >>sys.stderr, "show_sgf:", str(e)
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])

