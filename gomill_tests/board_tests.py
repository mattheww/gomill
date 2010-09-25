from gomill_tests.test_framework import SimpleTestCase

from gomill import boards

def make_tests(suite):
    suite.addTest(SimpleTestCase(test_basics))

def test_basics(tc):
    b = boards.Board(9)
    tc.assertTrue(b.is_empty())
    tc.assertEqual(b.area_score(), 0)
    b.play(2, 3, 'b')
    tc.assertFalse(b.is_empty())
    tc.assertEqual(b.area_score(), 81)
    b.play(3, 4, 'w')
    tc.assertEqual(b.area_score(), 0)

    tc.assertEqual(set(b.list_occupied_points()),
                   set([('b', (2, 3)), ('w', (3, 4))])
                   )

