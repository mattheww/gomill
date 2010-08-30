import cPickle as pickle

from gomill import competition_schedulers

def test_simple():
    sc = competition_schedulers.Simple_scheduler()

    def check():
        sc._check_consistent()

    def issue(n):
        result = [sc.issue() for _ in xrange(n)]
        check()
        return result

    assert issue(4) == [0, 1, 2, 3]
    sc.fix(2)
    sc.fix(1)
    assert sc.issue() == 4
    assert sc.fixed == 2
    assert sc.issued == 5
    sc.rollback()
    assert sc.issued == 2
    assert sc.fixed == 2

    assert issue(2) == [0, 3]

    sc.rollback()

    assert issue(4) == [0, 3, 4, 5]
    sc.fix(3)
    sc.fix(5)
    assert sc.issue() == 6

    sc = pickle.loads(pickle.dumps(sc))
    sc.rollback()

    assert issue(6) == [0, 4, 6, 7, 8, 9]
    assert sc.issued == 10
    assert sc.fixed == 4


def test_grouped():
    sc = competition_schedulers.Group_scheduler()
    def issue(n):
        return [sc.issue() for _ in xrange(n)]

    sc.set_groups([('m1', 4), ('m2', None)])

    assert sc.nothing_issued_yet()
    assert not sc.all_fixed()

    assert issue(3) == [
        ('m1', 0),
        ('m2', 0),
        ('m1', 1),
        ]

    assert not sc.nothing_issued_yet()

    sc.fix('m1', 1)
    sc.rollback()
    issued = issue(14)
    assert issued == [
        ('m2', 0),
        ('m1', 0),
        ('m2', 1),
        ('m1', 2),
        ('m2', 2),
        ('m1', 3),
        ('m2', 3),
        ('m2', 4),
        ('m2', 5),
        ('m2', 6),
        ('m2', 7),
        ('m2', 8),
        ('m2', 9),
        ('m2', 10),
        ]
    assert not sc.all_fixed()
    for token in issued:
        sc.fix(*token)
    assert sc.all_fixed()


if __name__ == "__main__":
    test_simple()
    test_grouped()

