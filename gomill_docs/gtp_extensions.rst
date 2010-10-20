GTP extensions
==============

Gomill supports a number of |gtp| extension commands. These are all named with
a ``gomill-`` prefix.


The extensions used by the ringmaster are as follows:

.. gtp:: gomill-explain_last_move

  Arguments: none

  Return a string containing the engine's comments about the last move it
  generated.

  This might include the engine's estimate of its winning chances, a principal
  variation, or any other diagnostic information.

  The intention is that |gtp| controllers which produce game records should
  use this command to write a comment associated with the move.

  Any non-ascii characters in the response should be encoded as UTF-8.

  If no information is available, return an empty string.

  The behaviour of this command is unspecified if a command changing the board
  state (eg :gtp:`play` or :gtp:`undo`) has occurred since the engine last
  generated a move.


.. gtp:: gomill-describe_engine

  Arguments: none

  Return a string with a description of the engine's configuration. This
  should repeat the information from the :gtp:`name` and :gtp:`version`
  commands. Controllers should expect the response to take multiple lines.

  The intention is that |gtp| controllers which produce game records should
  use the output of this command as part of a comment for the game as a whole.

  If possible, the response should include a description of all engine
  parameters which affect gameplay. If the engine plays reproducibly given the
  seed of a random number generator, the response should include that seed.

  Any non-ascii characters in the response should be encoded as UTF-8.


.. gtp:: gomill-cpu_time

  Arguments: none

  Return a float (represented in decimal) giving the amount of CPU time the
  engine has used to generate all moves made so far (in seconds).

  For engines which use multiple threads or processes, this should be the
  total time used on all CPUs.

  It may not be possible to meaningfully respond to this command (for example,
  if an engine runs on multiple processors which run at different speeds); in
  complex cases, the engine should document how the CPU time is calculated.


.. gtp:: gomill-genmove_ex

  Arguments: colour, list of keywords

  This is a variant of the standard :gtp:`genmove` command. Each keyword
  indicates a permitted (or desired) variation of behaviour. For example::

    gomill-genmove_ex b claim

  If :gtp:`!gomill-genmove_ex` is sent without any arguments (ie, no colour is
  specified), the engine should return a list of the keywords it supports (one
  per line, like :gtp:`list_commands`).

  Engines must ignore keywords they do not support. :gtp:`!gomill-genmove_ex`
  with no keywords is exactly equivalent to :gtp:`genmove`.

  The following keywords are currently defined:

  ``claim``
    In addition to the usual responses to :gtp:`genmove`, the engine may also
    return ``claim``, which indicates that the engine believes it is certain
    to win the game (the engine must not assume that the controller will act
    on this claim).


.. the other extensions, not used by the ringmaster, are:
.. - gomill-savesgf (kgs_proxy.py)
.. - gomill-passthrough (proxies in general, I suppose)

