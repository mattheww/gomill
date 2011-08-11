"""Split an SGF collection into separate files.

This demonstrates the parsing functions from the sgf_grammar module.

"""

import os
import sys
from optparse import OptionParser

from gomill import sgf_grammar
from gomill import sgf

def split_sgf_collection(pathname):
    f = open(pathname)
    sgf_src = f.read()
    f.close()
    dirname, basename = os.path.split(pathname)
    root, ext = os.path.splitext(basename)
    try:
        coarse_games = sgf_grammar.parse_sgf_collection(sgf_src)
    except ValueError, e:
        raise StandardError("error parsing file: %s" % e)
    for i, coarse_game in enumerate(coarse_games):
        sgf_game = sgf.Sgf_game.from_coarse_game_tree(coarse_game)
        sgf_game.get_root().add_comment_text(
            "Split from %s (game %d)" % (basename, i+1))
        split_pathname = os.path.join(dirname, "%s_%d%s" % (root, i+1, ext))
        with open(split_pathname, "wb") as f:
            f.write(sgf_game.serialise())


_description = """\
Split a file containing an SGF game collection into multiple files.
"""

def main(argv):
    parser = OptionParser(usage="%prog <filename>",
                          description=_description)
    opts, args = parser.parse_args(argv)
    if not args:
        parser.error("not enough arguments")
    pathname = args[0]
    if len(args) > 1:
        parser.error("too many arguments")
    try:
        split_sgf_collection(pathname)
    except Exception, e:
        print >>sys.stderr, "sgf_splitter:", str(e)
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])

