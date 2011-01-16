"""Test support code for testing Ringmasters."""

from collections import defaultdict
from cStringIO import StringIO

from gomill import ringmasters
from gomill import ringmaster_presenters

class Test_presenter(ringmaster_presenters.Presenter):
    """Presenter which stores the messages."""
    def __init__(self):
        ringmaster_presenters.Presenter.__init__(self)
        self.channels = defaultdict(list)

    shows_warnings_only = False

    def clear(self, channel):
        self.channels[channel] = []

    def say(self, channel, s):
        self.channels[channel].append(s)

    def refresh(self):
        pass

    def recent_messages(self, channel):
        """Retrieve messages sent since the channel was last cleared.

        Returns a list of strings.

        """
        return self.channels[channel][:]


class Testing_ringmaster(ringmasters.Ringmaster):
    """Variant of ringmaster suitable for use in tests.

    This doesn't read from or write to the filesystem.

    (If you're testing run(), make sure record_games is False, and
    discard_stderr is True for each player.)

    (Currently, write_status is made to do nothing, so it's not usefully
    testable.)

    Instantiate with the control file contents as an 8-bit string.

    It will act as if the control file had been loaded from
    /nonexistent/ctl/test.ctl.

    You'll want to run set_display_mode('test') with this.

    """
    def __init__(self, control_file_contents):
        self._control_file_contents = control_file_contents
        self._test_status = None
        self._written_status = None
        ringmasters.Ringmaster.__init__(self, '/nonexistent/ctl/test.ctl')

    _presenter_classes = {
        'test' : Test_presenter,
        }

    def _open_files(self):
        self.logfile = StringIO()
        self.historyfile = StringIO()

    def _close_files(self):
        # Don't want to close the StringIOs
        pass

    def _read_control_file(self):
        return self._control_file_contents

    def set_test_status(self, test_status):
        """Specify the value that will be loaded from the state file.

        test_status -- fake state file contents

        test_status should be a pair (status_format_version, status dict)

        """
        self._test_status = test_status

    def _load_status(self):
        return self._test_status

    def status_file_exists(self):
        return (self._test_status is not None)

    def _write_status(self, value):
        self._written_status = value

