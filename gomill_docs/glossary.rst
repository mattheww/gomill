Glossary
========

.. glossary::

  GTP
    The Go Text Protocol

    A communication protocol used to control Go-playing programs. Gomill
    uses only GTP version 2, which is specified at
    http://www.lysator.liu.se/~gunnar/gtp/gtp2-spec-draft2/gtp2-spec.html.

    (As of May 2012, the specification describes itself as a draft, but it
    has remained stable for several years and is widely implemented.)


  SGF
    The Smart Game Format

    A text-based file format used for storing Go game records.

    Gomill uses version FF[4], which is specified at
    http://www.red-bean.com/sgf/index.html.


  jigo
    A tied game (after komi is taken into account).


  komi
    Additional points awarded to White in final scoring.


  simple ko
    A Go rule prohibiting repetition of the immediately-preceding position.


  superko
    A Go rule prohibiting repetition of preceding positions.

    There are several possible variants of the superko rule. Gomill does not
    enforce any of them.


  pondering
    A feature implemented by some Go programs: thinking while it is their
    opponent's turn to move.


  controller
    A program implementing the 'referee' side of the |gtp| protocol.

    The |gtp| protocol can be seen as a client-server protocol, with the
    controller as the client.


  engine
    A program implementing the 'playing' side of the |gtp| protocol.

    The |gtp| protocol can be seen as a client-server protocol, with the
    engine as the server.


  player
    A |gtp| engine, together with a particular configuration.


  competition
    An 'event' consisting of multiple games managed by the Gomill ringmaster
    (either a tournament or a tuning event).

  tournament
    A competition in which the ringmaster plays games between predefined
    players, to compare their strengths.

  playoff
    A tournament comprising many games played between fixed pairings of
    players.

  all-play-all
    A tournament in which games are played between all pairings from a list of
    players.


  matchup
    A pairing of players in a tournament, together with its settings (board
    size, komi, handicap, and so on)


  tuning event
    A competition in which the ringmaster runs an algorithm which adjusts
    player parameters to try to find the values which give strongest play.


  Bandit problem
    A problem in which an agent has to repeatedly choose between actions whose
    value is initially unknown, trading off time spent on the action with the
    best estimated value against time spent evaluating other actions.

    See http://en.wikipedia.org/wiki/Multi-armed_bandit


  UCB
    Upper Confidence Bound algorithms

    A family of algorithms for addressing bandit problems.


  UCT
    Upper Confidence bounds applied to Trees.

    A variant of UCB for bandit problems in which the actions are arranged in
    the form of a tree.

    See http://senseis.xmp.net/?UCT.

