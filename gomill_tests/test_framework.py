import unittest2

class SimpleTestCase(unittest2.TestCase):
    """TestCase which runs a single function.

    Instantiate with the test function, which takes a TestCase parameter, eg:
        def test_xxx(tc):
            tc.assertEqual(2+2, 4)

    """

    longMessage = True

    def __init__(self, fn):
        unittest2.TestCase.__init__(self)
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


def _function_sort_key(fn):
    try:
        return fn.__code__.co_firstlineno
    except AttributeError:
        return str(fn)

def make_simple_tests(source, prefix="test_"):
    """Make test cases from a module's test_xxx functions.

      source -- dict (usually a module's globals()).
      prefix -- string (default "test_")

    Returns a list of TestCase objects.

    This makes a TestCase for each function in the values of 'source' whose
    name begins with 'prefix'.

    The list is in the order of function definition (using the line number
    attribute).

    """
    functions = [value for name, value in source.iteritems()
                 if name.startswith(prefix) and callable(value)]
    functions.sort(key=_function_sort_key)
    return [SimpleTestCase(fn) for fn in functions]
