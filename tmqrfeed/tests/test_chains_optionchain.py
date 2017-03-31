import datetime
import os
import pickle
import unittest

from tmqrfeed.chains import OptionChain
from tmqrfeed.manager import DataManager


class OptionChainTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))
        cls.dm = DataManager()
        with open(fn, 'rb') as f:
            cls.chain_list = cls.dm.datafeed._process_raw_options_chains(pickle.load(f))

    def setUp(self):
        self.expiraiton = datetime.datetime(2011, 1, 21, 0, 0)
        self.opt_chain = OptionChain(self.chain_list[self.expiraiton], self.expiraiton, self.dm)

    def test_init(self):
        self.assertEqual(self.opt_chain.expiration, datetime.datetime(2011, 1, 21, 0, 0))


