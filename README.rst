======
Gomill
======

Gomill is a suite of tools, and a Python library, for use in developing and
testing Go-playing programs. It is based around the Go Text Protocol (GTP) and
the Smart Game Format (SGF).

Full documentation and contact information is available from the `home page`__.

.. __: https://mjw.woodcraft.me.uk/gomill/


Requirements
------------

Gomill requires Python 2.5, 2.6, or 2.7.

Gomill is intended to run on any modern Unix-like system.

A Python 3 version of the SGF code is available as a separate Sgfmill__
project.

.. __: https://mjw.woodcraft.me.uk/sgfmill/


Building the documentation
--------------------------

To build the HTML documentation yourself::

   sphinx-build -c gomill_docs -b html gomill_docs build/html_docs

The documentation will be generated in ``build/html_docs``.

Requirements:

- Sphinx__ version 1.0 or later
  (at least 1.0.4 recommended; tested with 1.4)
- LaTeX__
- dvipng__

.. __: https://www.sphinx-doc.org/
.. __: https://www.latex-project.org/
.. __: https://www.nongnu.org/dvipng/


Running the tests
-----------------

To run the tests::

    python -m gomill_tests.run_gomill_testsuite

