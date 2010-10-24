"""Generic (non-gomill-specific) test framework code."""

import sys

if sys.version_info >= (2, 7):
    import unittest as unittest2
else:
    try:
        import unittest2
    except ImportError, e:
        e.unittest2_missing = True
        raise

# This makes TestResult ignore lines from this module in tracebacks
__unittest = True

class SupporterError(StandardError):
    """Exception raised by support objects when something goes wrong.

    This is raised to indicate things like sequencing errors detected by mock
    objects.

    """

class FrameworkTestCase(unittest2.TestCase):
    """unittest2-style TestCase implementation with a few tweaks."""

    # This is default in unittest2 but not python 2.7 unittest, so force it on.
    longMessage = True

    def assertItemsEqual(self, expected_seq, actual_seq, msg=None):
        """Variant implementation of standard assertItemsEqual.

        This uses the unorderable_list_difference check even if the lists are
        sortable: I prefer its output.

        """
        expected = list(expected_seq)
        actual = list(actual_seq)
        missing, unexpected = unittest2.util.unorderable_list_difference(
            expected, actual, ignore_duplicate=False
        )
        errors = []
        if missing:
            errors.append('Expected, but missing:\n    %s' %
                           unittest2.util.safe_repr(missing))
        if unexpected:
            errors.append('Unexpected, but present:\n    %s' %
                           unittest2.util.safe_repr(unexpected))
        if errors:
            standardMsg = '\n'.join(errors)
            self.fail(self._formatMessage(msg, standardMsg))


class SimpleTestCase(FrameworkTestCase):
    """TestCase which runs a single function.

    Instantiate with the test function, which takes a TestCase parameter, eg:
        def test_xxx(tc):
            tc.assertEqual(2+2, 4)

    """

    def __init__(self, fn):
        FrameworkTestCase.__init__(self)
        self.fn = fn
        try:
            self.name = fn.__module__.split(".", 1)[-1] + "." + fn.__name__
        except AttributeError:
            self.name = str(fn)

    def runTest(self):
        self.fn(self)

    def id(self):
        return self.name

    def shortDescription(self):
        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<SimpleTestCase: %s>" % self.name


class ParameterisedTestCase(FrameworkTestCase):
    """Parameterised testcase.

    Subclasses should define:
      test_name       -- short string
      parameter_names -- list of identifiers
      runTest

    """
    def __init__(self, code, *parameters):
        FrameworkTestCase.__init__(self)
        self.code = code
        self.name = "%s.%s:%s" % (self.__class__.__module__.split(".", 1)[-1],
                                  self.test_name, code)
        for name, value in zip(self.parameter_names, parameters):
            setattr(self, name, value)

    def runTest(self):
        raise NotImplementedError

    def id(self):
        return self.name

    def shortDescription(self):
        return None

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)



def _function_sort_key(fn):
    try:
        return fn.__code__.co_firstlineno
    except AttributeError:
        return str(fn)

def make_simple_tests(source, prefix="test_", testcase_class=SimpleTestCase):
    """Make test cases from a module's test_xxx functions.

      source         -- dict (usually a module's globals()).
      prefix         -- string (default "test_")
      testcase_class -- SimpleTestCase subclass to use

    Returns a list of TestCase objects.

    This makes a TestCase for each function in the values of 'source' whose
    name begins with 'prefix'.

    The list is in the order of function definition (using the line number
    attribute).

    """
    functions = [value for name, value in source.iteritems()
                 if name.startswith(prefix) and callable(value)]
    functions.sort(key=_function_sort_key)
    return [testcase_class(fn) for fn in functions]


class Fixture(object):
    """A testing fixture.

    Instantiate fixture objects with a TestCase parameter.

    The fixture arranges for any necessary cleanup to be performed by calling
    TestCase.addCleanUp.

    """
