"""GTP proxy for use with kgsGtp.

This supports saving a game record after each game, if the underlying engine
supports gomill-savesgf.

"""
import os
import sys
from optparse import OptionParser

from gomill import gtp_engine
from gomill import gtp_proxy
from gomill.gtp_engine import GtpError
from gomill.gtp_controller import BadGtpResponse

class Kgs_proxy(object):
    """GTP proxy for use with kgsGtp.

    Instantiate with command line arguments.

    Calls sys.exit on fatal errors.

    """

    def __init__(self, command_line_args):
        parser = OptionParser(usage="%prog [options] <back end command> [args]")
        parser.disable_interspersed_args()
        parser.add_option("--sgf-dir", metavar="PATHNAME")
        parser.add_option("--filename-template", metavar="TEMPLATE",
                          help="eg '%03d.sgf'")
        opts, args = parser.parse_args(command_line_args)

        if not args:
            parser.error("must specify a command")
        self.subprocess_command = args

        self.filename_template = "%04d.sgf"
        try:
            opts.filename_template % 3
        except Exception:
            pass
        else:
            self.filename_template = opts.filename_template

        self.sgf_dir = opts.sgf_dir
        if self.sgf_dir:
            self.check_sgf_dir()
            self.do_savesgf = True
        else:
            self.do_savesgf = False

    def log(self, s):
        print >>sys.stderr, s

    def run(self):
        self.proxy = gtp_proxy.Gtp_proxy()
        try:
            self.proxy.set_back_end_subprocess(self.subprocess_command)
            self.proxy.engine.add_commands(
                {'genmove' :       self.handle_genmove,
                 'kgs-game_over' : self.handle_game_over,
                 })
            if (self.do_savesgf and
                not self.proxy.back_end_has_command("gomill-savesgf")):
                sys.exit("kgs_proxy: back end doesn't support gomill-savesgf")

            # Colour that we appear to be playing
            self.my_colour = None
            self.initialise_name()
        except gtp_proxy.BackEndError, e:
            sys.exit("kgs_proxy: %s" % e)
        try:
            self.proxy.run()
        except KeyboardInterrupt:
            sys.exit(1)

    def initialise_name(self):
        def shorten_version(name, version):
            """Clean up redundant version strings."""
            if version.lower().startswith(name.lower()):
                version = version[len(name):].lstrip()
            # For MoGo's stupidly long version string
            a, b, c = version.partition(". Please read http:")
            if b:
                version = a
            return version[:32].rstrip()

        self.my_name = None
        try:
            self.my_name = self.proxy.pass_command("name", [])
            version = self.proxy.pass_command("version", [])
            version = shorten_version(self.my_name, version)
            self.my_name += ":" + version
        except BadGtpResponse:
            pass

    def handle_genmove(self, args):
        try:
            self.my_colour = gtp_engine.interpret_colour(args[0])
        except IndexError:
            gtp_engine.report_bad_arguments()
        return self.proxy.pass_command("genmove", args)

    def check_sgf_dir(self):
        if not os.path.isdir(self.sgf_dir):
            sys.exit("kgs_proxy: can't find save game directory %s" %
                     self.sgf_dir)

    def choose_filename(self, existing):
        existing = set(existing)
        for i in xrange(10000):
            filename = self.filename_template % i
            if filename not in existing:
                return filename
        raise StandardError("too many sgf files")

    def handle_game_over(self, args):
        """Handler for kgs-game_over.

        kgsGtp doesn't send any arguments, so we don't know the result.

        """
        def escape_for_savesgf(s):
            return s.replace("\\", "\\\\").replace(" ", "\\ ")

        if self.do_savesgf:
            filename = self.choose_filename(os.listdir(self.sgf_dir))
            pathname = os.path.join(self.sgf_dir, filename)
            self.log("kgs_proxy: saving game record to %s" % pathname)
            args = [pathname]
            if self.my_colour is not None and self.my_name is not None:
                args.append("P%s=%s" % (self.my_colour.upper(),
                                        escape_for_savesgf(self.my_name)))
            try:
                self.proxy.handle_command("gomill-savesgf", args)
            except GtpError, e:
                # Hide error from kgsGtp, though I don't suppose it would care
                self.log("error: %s" % e)


def main():
    kgs_proxy = Kgs_proxy(sys.argv[1:])
    kgs_proxy.run()

if __name__ == "__main__":
    main()
