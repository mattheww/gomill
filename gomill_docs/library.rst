The Gomill library
==================

Gomill is intended to be useful as a Python library for developing |gtp|- and
|sgf|-based tools.


.. contents:: Page contents
   :local:
   :backlinks: none


Library status
--------------

As of Gomill |version|, the library API is not formally documented, and should
not be considered entirely stable.

Nonetheless, the source files contain fairly detailed documentation, and the
:doc:`example scripts <example_scripts>` illustrate how various parts of the
library can be used.


Library overview
----------------

Generic support code

- :mod:`!gomill_utils`
- :mod:`!compact_tracebacks`
- :mod:`!ascii_tables`
- :mod:`!job_manager`
- :mod:`!settings`


Go-related support code

- :mod:`!gomill_common`
- :mod:`!ascii_boards`
- :mod:`!boards`
- :mod:`!handicap_layout`


|sgf| support

- :mod:`!sgf_reader`
- :mod:`!sgf_writer`


|gtp| controller side

- :mod:`!gtp_controller`
- :mod:`!gtp_games`


|gtp| engine side

- :mod:`!gtp_engine`
- :mod:`!gtp_states`
- :mod:`!gtp_proxy`


Competitions

- :mod:`!competition_schedulers`
- :mod:`!competitions`
- :mod:`!cem_tuners`
- :mod:`!mcts_tuners`
- :mod:`!playoffs`


The Ringmaster

- :mod:`!game_jobs`
- :mod:`!terminal_input`
- :mod:`!ringmaster_presenters`
- :mod:`!ringmasters`
- :mod:`!ringmaster_command_line`

