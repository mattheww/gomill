try:
    from collections import defaultdict
except:
    import UserDict
    class defaultdict(UserDict.UserDict) :
        def __init__(self, default_factory):
            UserDict.UserDict.__init__(self)
            self._default_factory = default_factory

        def __getitem__(self, key) :
            if key in self.data:
                result = self.data[key]
            else:
                result = self._default_factory()
                self[key] = result
            return result

