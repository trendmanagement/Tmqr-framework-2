import datetime
import os
import pickle
import unittest

from tmqrfeed.chains import OptionChain


class OptionChainTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))

        with open(fn, 'rb') as f:
            cls.chain_list = pickle.load(f)

    def setUp(self):
        self.opt_chain = OptionChain(self.chain_list[0])

    def test_init(self):
        self.assertEqual(self.opt_chain.expiration, datetime.datetime(2011, 1, 21, 0, 0))


