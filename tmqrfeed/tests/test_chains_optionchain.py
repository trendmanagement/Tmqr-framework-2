import datetime
import os
import pickle
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from tmqr.errors import *
from tmqrfeed.chains import OptionChain
from tmqrfeed.contracts import FutureContract, OptionContract
from tmqrfeed.manager import DataManager


class OptionChainTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))
        cls.dm = DataManager()
        cls.underlying = FutureContract('US.F.ES.H11.110318')
        with open(fn, 'rb') as f:
            cls.chain_list = cls.dm.datafeed._process_raw_options_chains(pickle.load(f), cls.underlying)


    def setUp(self):

        self.expiraiton = datetime.datetime(2011, 1, 21, 0, 0)
        self.opt_chain = OptionChain(self.chain_list[self.expiraiton], self.expiraiton, self.underlying, self.dm)

    def test_init(self):
        self.assertEqual(self.opt_chain.expiration, self.expiraiton)

        self.assertRaises(ArgumentError, OptionChain, self.chain_list[self.expiraiton], self.expiraiton,
                          self.underlying, None)

    def test__get_atm_index(self):
        self.opt_chain._strike_array = np.array([90, 91, 92, 93, 94, 95])

        self.assertEqual(93, self.opt_chain._strike_array[self.opt_chain._get_atm_index(93)])
        self.assertEqual(92, self.opt_chain._strike_array[self.opt_chain._get_atm_index(92.5)])
        self.assertEqual(90, self.opt_chain._strike_array[self.opt_chain._get_atm_index(89)])
        self.assertEqual(95, self.opt_chain._strike_array[self.opt_chain._get_atm_index(100)])

    def test__find_by_offset_valid(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.ctype == 'C':
                    return 0.25, 0.26
                else:
                    return 0.15, 0.16

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 0, 'C', 10)

        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('C', opt.ctype)
        self.assertEqual(500, opt.strike)

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 0, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(500, opt.strike)

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), -1, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(475, opt.strike)

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 1, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(525, opt.strike)

    def test__find_by_offset__set_pricing_context_is_called(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.ctype == 'C':
                    return 0.25, 0.26

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect
        with patch('tmqrfeed.contracts.OptionContract.set_pricing_context') as mock_set_pricing_context:
            opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 0, 'C', 10)
            self.assertEqual(True, mock_set_pricing_context.called)

            call_args = (datetime.datetime(2011, 1, 19, 0, 0), 500.0, 501.0, 0.25, 0.26)
            self.assertEqual(call_args, mock_set_pricing_context.call_args[0])




    def test__find_by_offset_invalid_notfound_strike_nonatm(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.strike == 475:
                    raise NotFoundError()
                if asset.strike == 525:
                    raise NotFoundError()
                if asset.ctype == 'P':
                    return 0.15, 0.16

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), -1, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(450, opt.strike)

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 1, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(550, opt.strike)

    def test__find_by_offset_invalid_notfound_strike_atm(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.strike == 500:
                    raise NotFoundError()
                if asset.strike == 525:
                    raise NotFoundError()
                if asset.ctype == 'P':
                    return 0.15, 0.16

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 0, 'P', 10)
        self.assertTrue(isinstance(opt, OptionContract))
        self.assertEqual('P', opt.ctype)
        self.assertEqual(475, opt.strike)

    def test__find_by_offset_invalid_notfound_strike_atm_error(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.strike == 500:
                    raise NotFoundError()
                if asset.strike == 525:
                    raise NotFoundError()
                if asset.strike == 475:
                    raise NotFoundError()

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), 0,
                          'P', 10)

    def test__find_by_offset_invalid_notfound_error_limit(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.strike == 475:
                    raise NotFoundError()
                if asset.strike == 525:
                    raise NotFoundError()

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), -1,
                          'P', error_limit=1)

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), 1,
                          'P', error_limit=1)

    def test__find_by_offset_strike_array_out_of_bounds_error_lower(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 275, 275

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), -1,
                          'P', error_limit=1)

    def test__find_by_offset_strike_array_out_of_bounds_error_upper(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 1900, 1900

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), 1,
                          'P', error_limit=1)

    def test__find_by_offset_strike_array_out_of_bounds_error_lower_with_not_found(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 400, 400
            if isinstance(asset, OptionContract):
                if asset.strike == 375:
                    raise NotFoundError()

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_offset, datetime.datetime(2011, 1, 19, 0, 0), -1,
                          'P', error_limit=10)

    def test_find__errors_checks(self):
        with patch('tmqrfeed.chains.OptionChain._find_by_offset') as mock__find_by_offset:
            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 0, 'C',
                              how='UNKOWN')
            self.assertRaises(ArgumentError, self.opt_chain.find, None, 0, 'C')
            # Check other datetime types
            self.opt_chain.find(pd.Timestamp("2011-01-19"), 0, 'C')

            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 'w', 'C')
            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), None, 'C')
            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 0.32, 'C')
            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 1.0, 'C')

            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 0, 'F')
            self.opt_chain.find(pd.Timestamp("2011-01-19"), 0, 'C')
            self.opt_chain.find(pd.Timestamp("2011-01-19"), 0, 'C')
            self.opt_chain.find(pd.Timestamp("2011-01-19"), 0, 'c')
            self.opt_chain.find(pd.Timestamp("2011-01-19"), 0, 'p')

    def test_find__how_offset(self):
        with patch('tmqrfeed.chains.OptionChain._find_by_offset') as mock__find_by_offset:
            self.opt_chain.find(datetime.datetime(2011, 1, 19, 0, 0), 0, 'c', how='offset')

            self.assertTrue(mock__find_by_offset.called)
            self.assertEqual(mock__find_by_offset.call_args[0][0], datetime.datetime(2011, 1, 19, 0, 0))
            self.assertEqual(mock__find_by_offset.call_args[0][1], 0)
            self.assertEqual(mock__find_by_offset.call_args[0][2], 'C')
            self.assertEqual(mock__find_by_offset.call_args[0][3], 5)

            mock__find_by_offset.reset_mock()
            self.opt_chain.find(datetime.datetime(2011, 1, 19, 0, 0), 0, 'c', how='offset', error_limit=2)
            self.assertTrue(mock__find_by_offset.called)
            self.assertEqual(mock__find_by_offset.call_args[0][0], datetime.datetime(2011, 1, 19, 0, 0))
            self.assertEqual(mock__find_by_offset.call_args[0][1], 0)
            self.assertEqual(mock__find_by_offset.call_args[0][2], 'C')
            self.assertEqual(mock__find_by_offset.call_args[0][3], 2)
