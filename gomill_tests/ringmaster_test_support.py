"""Test support code for testing Ringmasters."""

from cStringIO import StringIO

from gomill import ringmasters
from gomill import ringmaster_presenters

class Test_presenter(ringmaster_presenters.Presenter):
    """Presenter which stores warnings."""
    def __init__(self):
        ringmaster_presenters.Presenter.__init__(self)
        self.warnings = []

    # Make the ringmaster do the extra work
    shows_warnings_only = False

    def clear(self, channel):
        pass

    def say(self, channel, s):
        if channel == 'warnings':
            self.warnings.append(s)

    def refresh(self):
        pass

    def retrieve_warnings(self):
        """Retrieve a list of warning messages sent to the presenter.

        Returns a list of strings.

        """
        return self.warnings[:]


class Testing_ringmaster(ringmasters.Ringmaster):
    """Variant of ringmaster suitable for use in tests.

    FIXME: This is supposed to be nobbled so that it doesn't read from or write
    to the filesystem.

    You'll want to run set_display_mode('test') with this.

    """

    _presenter_classes = {
        'test' : Test_presenter,
        }

    def _open_files(self):
        self.logfile = StringIO()
        self.historyfile = StringIO()

    def _close_files(self):
        # Don't want to close the StringIOs
        pass

    def write_status(self):
        """FIXME: nobbled for now."""
        pass

