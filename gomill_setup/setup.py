from distutils.core import setup

try:
    from sphinx.setup_command import BuildDoc
except ImportError:
    BuildDoc = None

if BuildDoc:
    cmdclass = {'build_sphinx' : BuildDoc}
else:
    cmdclass = {}

long_description = """\
Gomill is a suite of tools, and a Python library, for use in developing and
testing Go-playing programs. It is based around the Go Text Protocol (GTP) and
the Smart Game Format (SGF).

The principal tool is the ringmaster, which plays programs against each other
and keeps track of the results.
"""

setup(name='gomill',
      version="0.5",
      description="Go programming toolkit",
      long_description=long_description,
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
      keywords="go baduk weiqi",
      license="MIT",
      platforms="POSIX",
      )
