import datetime
import os
import pickle
import unittest
from collections import OrderedDict

from tmqr.errors import *
from tmqrfeed.chains import OptionChainList, OptionChain
from tmqrfeed.manager import DataManager


class ChainListTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))
        cls.dm = DataManager()

        with open(fn, 'rb') as f:
            cls.chain_list = cls.dm.datafeed._process_raw_options_chains(pickle.load(f))

    def setUp(self):
        self.opt_chain = OptionChainList(self.chain_list)

    def test_init(self):
        chainlst = OptionChainList(self.chain_list)
        self.assertEqual(type(chainlst.chain_list), OrderedDict)
        self.assertEqual(len(chainlst.chain_list), 3)

        self.assertRaises(ArgumentError, OptionChainList, None)
        self.assertRaises(ArgumentError, OptionChainList, [])

    def test_has_len(self):
        chainlst = OptionChainList(self.chain_list)
        self.assertEqual(3, len(chainlst))

    def test_has_expiraitons(self):
        chainlst = OptionChainList(self.chain_list)
        exp_list = [datetime.datetime(2011, 1, 21, 0, 0),
                    datetime.datetime(2011, 2, 18, 0, 0),
                    datetime.datetime(2011, 3, 18, 0, 0)]
        self.assertEqual(exp_list, chainlst.expirations)

    def test_has_iterable(self):
        for chain in self.opt_chain:
            self.assertEqual(type(chain), OptionChain)

    def test_has_iterable_items(self):
        for expiration, chain in self.opt_chain.items():
            self.assertEqual(type(expiration), datetime.datetime)
            self.assertEqual(type(chain), OptionChain)


    def test_chain_get_item_by_date(self):
        expiry = datetime.datetime(2011, 2, 18, 0, 0)
        self.assertEqual(self.opt_chain.find(expiry.date()).expiration, expiry)

    def test_chain_get_item_by_date_time(self):
        expiry = datetime.datetime(2011, 2, 18, 0, 0)
        self.assertEqual(self.opt_chain.find(expiry).expiration, expiry)

    def test_chain_has_get_item_error_unexpected_item_type(self):
        self.assertRaises(ValueError, self.opt_chain.find, 'wrong type')

    def test_chain_get_item_by_offset(self):
        expiry = datetime.datetime(2011, 1, 21, 0, 0)
        self.assertEqual(self.opt_chain.find(0).expiration, expiry)

    def test_chain_repr(self):
        exp_str = ""

        for i, exp in enumerate(self.opt_chain.expirations):
            exp_str += '{0}: {1}\n'.format(i, exp.date())

        self.assertEqual(self.opt_chain.__repr__(), exp_str)
