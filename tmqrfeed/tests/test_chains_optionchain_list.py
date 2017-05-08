import datetime
import os
import pickle
import unittest
from collections import OrderedDict

from tmqr.errors import *
from tmqrfeed.chains import OptionChainList, OptionChain
from tmqrfeed.contracts import FutureContract
from tmqrfeed.manager import DataManager


class ChainListTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))
        cls.dm = DataManager()
        cls.underlying = FutureContract('US.F.ES.H11.110318')
        with open(fn, 'rb') as f:
            cls.chain_list = cls.dm.datafeed._process_raw_options_chains(pickle.load(f), cls.underlying)

    def setUp(self):
        self.dm = DataManager()
        self.opt_chain = OptionChainList(self.chain_list, self.underlying, self.dm)

    def test_init(self):
        chainlst = OptionChainList(self.chain_list, self.underlying, self.dm)
        self.assertEqual(type(chainlst.chain_list), OrderedDict)
        self.assertEqual(len(chainlst.chain_list), 3)

        self.assertRaises(ArgumentError, OptionChainList, self.chain_list, self.underlying, None)
        self.assertRaises(ArgumentError, OptionChainList, self.chain_list, None, self.dm)
        self.assertRaises(ArgumentError, OptionChainList, None, self.underlying, self.dm)
        self.assertRaises(ArgumentError, OptionChainList, OrderedDict(), self.underlying, self.dm)

    def test_has_len(self):
        self.assertEqual(3, len(self.opt_chain))

    def test_has_expiraitons(self):
        exp_list = [datetime.datetime(2011, 1, 21, 0, 0),
                    datetime.datetime(2011, 2, 18, 0, 0),
                    datetime.datetime(2011, 3, 18, 0, 0)]
        self.assertEqual(exp_list, self.opt_chain.expirations)

    def test_has_iterable(self):
        for chain in self.opt_chain:
            self.assertEqual(type(chain), OptionChain)

    def test_has_iterable_items(self):
        for expiration, chain in self.opt_chain.items():
            self.assertEqual(type(expiration), datetime.datetime)
            self.assertEqual(type(chain), OptionChain)


    def test_chain_get_item_by_date(self):
        expiry = datetime.datetime(2011, 2, 18, 0, 0)

        self.assertEqual(self.opt_chain.find(datetime.datetime(2011, 2, 11, 0, 0), expiry.date()).expiration, expiry)

    def test_chain_get_item_by_date_time(self):
        expiry = datetime.datetime(2011, 2, 18, 0, 0)
        self.assertEqual(self.opt_chain.find(datetime.datetime(2011, 2, 11, 0, 0), expiry).expiration, expiry)

    def test_chain_has_get_item_error_unexpected_item_type(self):
        self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 2, 11, 0, 0), 'wrong type')

    def test_chain_get_item_by_offset(self):
        expiry = datetime.datetime(2011, 2, 18, 0, 0)

        self.assertEqual(self.opt_chain.find(datetime.datetime(2011, 2, 11, 0, 0), 0).expiration, expiry)

    def test_chain_get_item_by_requested_expired(self):
        self.assertRaises(ChainNotFoundError, self.opt_chain.find, datetime.datetime(2011, 4, 11, 0, 0), 0)

    def test_chain_get_item_by_requested_chain_not_found_skipped_offset(self):
        self.assertRaises(ChainNotFoundError, self.opt_chain.find, datetime.datetime(2011, 2, 11, 0, 0), 3)
        try:
            self.opt_chain.find(datetime.datetime(2011, 2, 11, 0, 0), 3)
        except ChainNotFoundError as exc:
            self.assertEqual(exc.option_offset_skipped, 2)

    def test_chain_find_with_optcode(self):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es_optcode.pkl'))
        dm = DataManager()
        underlying = FutureContract('US.F.ES.Z16.161216')
        with open(fn, 'rb') as f:
            chain_list = dm.datafeed._process_raw_options_chains(pickle.load(f), underlying)

        chain = OptionChainList(chain_list, underlying, dm)

        self.assertRaises(ArgumentError, chain.find, datetime.datetime(2016, 11, 11), -1, opt_codes=['EW'])

        opt_chain = chain.find(datetime.datetime(2016, 11, 11), 0, opt_codes=['EW'])
        self.assertEqual(datetime.datetime(2016, 11, 30), opt_chain.expiration)

        opt_chain = chain.find(datetime.datetime(2016, 11, 11), 1, opt_codes=['EW', ''])
        self.assertEqual(datetime.datetime(2016, 12, 16), opt_chain.expiration)

        self.assertRaises(ChainNotFoundError, self.opt_chain.find, datetime.datetime(2016, 11, 11, 0, 0), 3)

        try:
            chain.find(datetime.datetime(2016, 11, 11, 0, 0), 3, opt_codes=['EW', ''])
        except ChainNotFoundError as exc:
            self.assertEqual(exc.option_offset_skipped, 2)







    def test_chain_repr(self):
        self.assertTrue('US.F.ES.H11.110318 expirations' in self.opt_chain.__repr__())
        self.assertTrue('0: 2011-01-21' in self.opt_chain.__repr__())

        chain = self.opt_chain.chain_list[datetime.datetime(2011, 1, 21)]
        chain.opt_code = 'OPTCODE'
        self.assertTrue('0: 2011-01-21 (OptCode: OPTCODE)' in self.opt_chain.__repr__())
