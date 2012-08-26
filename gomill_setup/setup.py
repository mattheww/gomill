import glob
import imp
import os
import sys
from distutils import dir_util
from distutils.core import setup, Command

VERSION = "0.7.4"


try:
    from sphinx.setup_command import BuildDoc
except ImportError:
    BuildDoc = None

cmdclass = {}

if BuildDoc:
    cmdclass['build_sphinx'] = BuildDoc



def find_script(name):
    mode = os.F_OK | os.X_OK
    for dirname in os.environ.get('PATH', os.defpath).split(os.pathsep):
        if dirname == '':
            continue
        pathname = os.path.join(dirname, name)
        if os.path.exists(pathname) and os.access(pathname, mode):
            return pathname
    return None

def check_script(pathname):
    s = open(pathname).read()
    return 'from gomill import' in s

def find_package(name):
    try:
        f, pathname, _ = imp.find_module(name)
    except ImportError:
        return None
    if not isinstance(pathname, str):
        return None
    return os.path.realpath(pathname)

def find_egg_info(package, pathname):
    dirname = os.path.dirname(pathname)
    return glob.glob(os.path.join(dirname, "%s-*.egg-info" % package))


class uninstall(Command):
    description = "uninstall the currently available version"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        files_to_remove = []
        dirs_to_remove = []

        for script in self.distribution.scripts:
            pathname = find_script(script)
            if pathname is None:
                self.warn("could not find script '%s'" % script)
                continue
            if check_script(pathname):
                files_to_remove.append(pathname)
            else:
                self.warn("'%s' does not appear to be a gomill script; "
                          "not removing" % pathname)

        here = os.path.dirname(os.path.realpath(__file__))
        sys.path = [s for s in sys.path if os.path.realpath(s) != here]

        for package in self.distribution.packages:
            pathname = find_package(package)
            if pathname == here:
                # belt and braces
                pathname = None
            if pathname is None:
                self.warn("could not find package '%s'" % package)
                continue
            dirs_to_remove.append(pathname)
            egg_infos = find_egg_info(package, pathname)
            if len(egg_infos) > 1:
                self.warn("multiple .egg-info files; not removing any:\n%s"
                          % "\n".join(egg_infos))
                egg_info_pathname = None
            elif len(egg_infos) == 1:
                pathname = egg_infos[0]
                if os.path.isdir(pathname):
                    dirs_to_remove.append(pathname)
                else:
                    files_to_remove.append(pathname)

        for pathname in files_to_remove:
            self.execute(os.remove, (pathname,), "removing '%s'" % pathname)
        for pathname in dirs_to_remove:
            dir_util.remove_tree(pathname, dry_run=self.dry_run)

cmdclass['uninstall'] = uninstall


GOMILL_URL = "http://mjw.woodcraft.me.uk/gomill/"

LONG_DESCRIPTION = """\
Gomill is a suite of tools, and a Python library, for use in developing and
testing Go-playing programs. It is based around the Go Text Protocol (GTP) and
the Smart Game Format (SGF).

The principal tool is the ringmaster, which plays programs against each other
and keeps track of the results.

There is also experimental support for automatically tuning program parameters.

Download: http://mjw.woodcraft.me.uk/gomill/download/gomill-%(VERSION)s.tar.gz

Documentation: http://mjw.woodcraft.me.uk/gomill/download/gomill-doc-%(VERSION)s.tar.gz

Online Documentation: http://mjw.woodcraft.me.uk/gomill/doc/%(VERSION)s/

Changelog: http://mjw.woodcraft.me.uk/gomill/doc/%(VERSION)s/changes.html

Git: http://mjw.woodcraft.me.uk/gomill/git/

Gitweb: http://mjw.woodcraft.me.uk/gitweb/gomill/

""" % vars()

setup(name='gomill',
      version=VERSION,
      url=GOMILL_URL,
      download_url="%sdownload/gomill-%s.tar.gz" % (GOMILL_URL, VERSION),
      description="Tools for testing and tuning Go-playing programs",
      long_description=LONG_DESCRIPTION,
      author="Matthew Woodcraft",
      author_email="matthew@woodcraft.me.uk",
      packages=['gomill'],
      scripts=['ringmaster'],
      cmdclass=cmdclass,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Console",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Natural Language :: English",
          "Operating System :: POSIX",
          "Operating System :: MacOS :: MacOS X",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.5",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python",
          "Topic :: Games/Entertainment :: Board Games",
          "Topic :: Software Development :: Libraries :: Python Modules",
          ],
      keywords="go,baduk,weiqi,gtp,sgf",
      license="MIT",
      platforms="POSIX",
      )
