from distutils.core import setup

try:
    from sphinx.setup_command import BuildDoc
except ImportError:
    BuildDoc = None

if BuildDoc:
    cmdclass = {'build_sphinx' : BuildDoc}
else:
    cmdclass = {}

setup(name='gomill',
      version="0.5",
      description="Go programming toolkit",
      author="Matthew Woodcraft",
      author_email="matthew@woodcraft.me.uk",
      packages=['gomill'],
      scripts=['ringmaster'],
      cmdclass=cmdclass,
      )
