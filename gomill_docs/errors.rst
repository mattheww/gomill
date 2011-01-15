Error handling and exceptional situations
-----------------------------------------

This page contains some tedious details of the implementation; it might be of
interest if you're wondering whether the behaviour you see is intentional or a
bug.

.. contents:: Page contents
   :local:
   :backlinks: none


.. _game id:

Game identification
^^^^^^^^^^^^^^^^^^^

Each game played in a competition is identified using a short string (the
:dfn:`game_id`). This is used in the |sgf| :ref:`game record <game records>`
filename and game name (``GN``), the :ref:`log files <logging>`, the live
display, and so on.

For playoff tournaments, game ids are made up from the :pl-setting:`matchup id
<id>` and the number of the game within the matchup; for example, the first
game played might be ``0_0`` or ``0_000`` (depending on the value of
:pl-setting:`number_of_games`).

Similarly for all-play-all tournaments, game ids are like ``AvB_0``, using the
competitor letters shown in the results grid, with the length depending on the
:aa-setting:`rounds` setting.


Details of scoring
^^^^^^^^^^^^^^^^^^

If :setting:`scorer` is ``"players"`` but neither engine is able to score
(whether because :gtp:`!final_score` isn't implemented, or it fails, or
:setting:`is_reliable_scorer` is ``False``), the game result is reported as
unknown (|sgf| result ``?``).

If both engines are able to score but they disagree about the winner, the game
result is reported as unknown. The engines' responses to :gtp:`!final_score`
are recorded in |sgf| file comments.

If the engines agree about the winner but disagree about the winning margin,
the |sgf| result is simply ``B+`` or ``W+``, and the engines' responses are
recorded in |sgf| file comments.


.. _engine errors:

Engine errors
^^^^^^^^^^^^^

If an engine returns a |gtp| failure response to any of the commands which set
up the game (eg :gtp:`!boardsize` or :gtp:`!fixed_handicap`), the game is
treated as :ref:`void <void games>`.

If an engine fails to start, exits unexpectedly, or produces a |gtp| response
which is ill-formed at the protocol level, the game is treated as :ref:`void
<void games>`.

As an exception, if such an error happens after the game's result has been
established (in particular, if one player has already forfeited the game), the
game is not treated as void.


.. _engine exit behaviour:

Engine exit behaviour
^^^^^^^^^^^^^^^^^^^^^

Before reporting the game result, the ringmaster sends :gtp:`!quit` to both
engines, closes their input and output pipes, and waits for the subprocesses
to exit.

If an engine hangs (during the game or at exit), the ringmaster will just hang
too (or, if in parallel mode, one worker process will).

The exit status of engine subprocesses is ignored.


.. index:: void games

.. _void games:

Void games
^^^^^^^^^^

Void games are games which were not completed due to a software failure, and
which don't count as a forfeit by either engine.

Void games don't appear in the competition results. They're recorded in the
:ref:`event log <logging>`, and a warning is displayed on screen when they
occur.

If :setting:`record_games` is enabled, a game record will be written for each
void game that had at least one move played. These are placed in the
:file:`{code}.void/` subdirectory of the competition directory.

A void game will normally be replayed, with the same game id (the details
depend on the competition type; see below).

(Note that void games aren't the same thing as games whose |sgf| result is
``Void``; the ringmaster uses that result for games which exceed the
:setting:`move_limit`.)


Halting competitions due to errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A single error which causes a void game will not normally cause a competition
to be prematurely halted, but multiple errors may.

The details depend on the competition type:

For playoff and all-play-all tournaments, a run is halted early if the first
game in any matchup is void, or if two games in a row for the same matchup are
void.

For tuning events, a run is halted immediately if the first game to finish is
void.

Otherwise, in Monte Carlo tuning events a void game will be ignored: a new
game will be scheduled from the current state of the MCTS tree (and the
original game number will be skipped). If two game results in a row are void,
the run will be halted.

In cross-entropy tuning events a void game will be replayed; if it fails
again, the run will be halted.

In parallel mode, outstanding games will be allowed to complete.


Preventing simultaneous runs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If :c:func:`!flock()` is available, the ringmaster will detect attempts to run
a competition which is already running (but this probably won't work if the
control file is on a network filesystem).

It's fine to use :action:`show` and :action:`report`, or the results API,
while a competition is running.


Signals and controlling terminal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The check for :kbd:`Ctrl-X` uses the ringmaster's controlling terminal,
independently of stdin and stdout. If there's no controlling terminal, or
:mod:`termios` isn't available, this check is disabled.

The engine subprocesses are left attached to the ringmaster's controlling
terminal, so they will receive signals from :kbd:`Ctrl-C`; unless they detach
from their controlling terminal or ignore the signal, they should exit
cleanly in response.

Running the ringmaster in the background (including using :kbd:`Ctrl-Z`)
should work properly (you probably want :ref:`quiet mode <quiet mode>`).


.. _remote control file:

The remote control file
^^^^^^^^^^^^^^^^^^^^^^^

The :action:`stop` action is implemented by writing a :file:`{code}.cmd` file
to the competition directory.


Character encoding
^^^^^^^^^^^^^^^^^^

Gomill is designed for a UTF-8 environment; it is intended to work correctly
if non-ASCII characters provided as input are encoded in UTF-8, and to produce
terminal and report output in UTF-8.

Non-ASCII characters in the control file must be encoded in UTF-8.

|GTP| engines may return UTF-8 characters in in response to :gtp:`!name`,
:gtp:`!version`, :gtp:`gomill-describe_engine`, or
:gtp:`gomill-explain_last_move`.

In practice, non-ASCII characters from |GTP| engines will normally be passed
through untranslated, so if you have a non-UTF-8 environment things will
probably work reasonably (if your terminal uses the same encoding).

SGF files written by Gomill always explicitly specify UTF-8 encoding.

