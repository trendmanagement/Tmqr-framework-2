import unittest
from tmqrfeed.manager import DataManager
from tmqrindex.index_contfut import IndexContFut


class IndexContFutTestCase(unittest.TestCase):
    def test_run(self):
        dm = DataManager()
        idx = IndexContFut(dm, instrument='US.CL')
        idx.run()
        pass
