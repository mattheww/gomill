Installation
============

.. contents:: Page contents
   :local:
   :backlinks: none


Requirements
------------

Gomill requires Python 2.5, 2.6, or 2.7.

For Python 2.5 only, the :option:`--parallel <ringmaster --parallel>` feature
requires the external `multiprocessing`__ package.

.. __: http://pypi.python.org/pypi/multiprocessing

Gomill is intended to run on any modern Unix-like system.


Obtaining Gomill
----------------

Gomill is distributed as a pure-Python source archive,
:file:`gomill-{version}.tar.gz`. The most recent version can be obtained from
http://mjw.woodcraft.me.uk/gomill/.

This documentation is distributed separately as
:file:`gomill-doc-{version}.tar.gz`.

Once you have downloaded the source archive, extract it using a command like
:samp:`tar -xzf gomill-{version}.tar.gz`. This will create a directory named
:file:`gomill-{version}`, referred to below as the :dfn:`distribution
directory`.

Alternatively, you can access releases using Git::

  git clone http://mjw.woodcraft.me.uk/gomill/git/ gomill

which would create :file:`gomill` as the distribution directory.



Running the ringmaster
----------------------

The ringmaster executable in the distribution directory can be run directly
without any further installation; it will use the copy of the :mod:`!gomill`
package in the distribution directory.

A symbolic link to the ringmaster executable will also work, but if you move
the executable elsewhere it will not be able to find the :mod:`!gomill`
package unless the package is installed.


Installing
----------

Installing Gomill puts the :mod:`!gomill` package onto the Python module
search path, and the ringmaster executable onto the executable
:envvar:`!PATH`.

To install, first change to the distribution directory, then:

- to install for the system as a whole, run (as a sufficiently privileged
  user) ::

    python setup.py install


- to install for the current user only (Python 2.6 or 2.7), run ::

    python setup.py install --user

  (in this case the ringmaster executable will be placed in
  :file:`~/.local/bin`.)

Pass :option:`!--dry-run` to see what these will do. See
http://docs.python.org/2.7/install/ for more information.


Uninstalling
------------

To remove an installed version of Gomill, run ::

  python setup.py uninstall

(This uses the Python module search path and the executable :envvar:`!PATH` to
find the files to remove; pass :option:`!--dry-run` to see what it will do.)



Running the test suite
----------------------

To run the testsuite against the distributed :mod:`!gomill` package, change to
the distribution directory and run ::

  python -m gomill_tests.run_gomill_testsuite


To run the testsuite against an installed :mod:`!gomill` package, change to
the distribution directory and run ::

  python test_installed_gomill.py


With Python versions earlier than 2.7, the unittest2__ library is required
to run the testsuite.

.. __: http://pypi.python.org/pypi/unittest2/


.. _running the example scripts:

Running the example scripts
---------------------------

To run the example scripts, it is simplest to install the :mod:`!gomill`
package first.

If you do not wish to do so, you can run ::

  export PYTHONPATH=<path to the distribution directory>

so that the example scripts will be able to find the :mod:`!gomill` package.



Building the documentation
--------------------------

The sources for this HTML documentation are included in the Gomill source
archive. To rebuild the documentation, change to the distribution directory
and run ::

   python setup.py build_sphinx

The documentation will be generated in :file:`build/sphinx/html`.

Requirements:

- Sphinx__ version 1.0 or later
  (at least 1.0.4 recommended; tested with 1.0 and 1.1)
- LaTeX__
- dvipng__

.. __: http://sphinx.pocoo.org/
.. __: http://www.latex-project.org/
.. __: http://www.nongnu.org/dvipng/

