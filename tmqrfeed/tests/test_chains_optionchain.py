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
        self.expiration = datetime.datetime(2011, 1, 21, 0, 0)
        self.opt_chain = OptionChain(self.chain_list[self.expiration], self.expiration, self.underlying, self.dm)

    def test_init(self):
        self.assertEqual(self.opt_chain.expiration, self.expiration)

        self.assertRaises(ArgumentError, OptionChain, self.chain_list[self.expiration], self.expiration,
                          self.underlying, None)
        self.assertRaises(ChainNotFoundError, OptionChain, {}, self.expiration,
                          self.underlying, self.dm)

    def test_mixed_opt_codes(self):
        self.expiration = datetime.datetime(2011, 1, 21, 0, 0)
        opt_dict = self.chain_list[self.expiration].copy()
        opt_dict[12380.2] = (OptionContract('US.C.F-ZB-H11-110322.110121.OPTCODE@89.0'),
                             OptionContract('US.P.F-ZB-H11-110322.110121.OPTCODE@89.0'))

        self.assertRaises(ArgumentError, OptionChain, opt_dict, self.expiration, self.underlying, self.dm)

    def test_opt_code(self):
        self.expiration = datetime.datetime(2011, 1, 21, 0, 0)
        opt_dict = {}
        opt_dict[12380.2] = (OptionContract('US.C.F-ZB-H11-110322.110121.OPTCODE@89.0'),
                             OptionContract('US.P.F-ZB-H11-110322.110121.OPTCODE@89.0'))

        chain = OptionChain(opt_dict, self.expiration, self.underlying, self.dm)
        self.assertEqual('OPTCODE', chain.opt_code)

    def test_repr_and_str(self):
        self.assertEqual(str(self.opt_chain), f'Chain: {self.underlying} {self.expiration.date()}')
        self.assertEqual(str(self.opt_chain), self.opt_chain.__repr__())

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
        self.opt_chain.dm.riskfreerate_get.return_value = 0.05
        with patch('tmqrfeed.contracts.OptionContract.set_pricing_context') as mock_set_pricing_context:
            opt = self.opt_chain._find_by_offset(datetime.datetime(2011, 1, 19, 0, 0), 0, 'C', 10)
            self.assertEqual(True, mock_set_pricing_context.called)

            call_args = (datetime.datetime(2011, 1, 19, 0, 0), 500.0, 501.0, 0.25, 0.26, 0.05)
            self.assertEqual(call_args, mock_set_pricing_context.call_args[0])




    def test__find_by_offset_invalid_notfound_strike_nonatm(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.strike == 475:
                    raise QuoteNotFoundError()
                if asset.strike == 525:
                    raise QuoteNotFoundError()
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
                    raise QuoteNotFoundError()
                if asset.strike == 525:
                    raise QuoteNotFoundError()
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
                    raise QuoteNotFoundError()
                if asset.strike == 525:
                    raise QuoteNotFoundError()
                if asset.strike == 475:
                    raise QuoteNotFoundError()

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
                    raise QuoteNotFoundError()
                if asset.strike == 525:
                    raise QuoteNotFoundError()

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
                    raise QuoteNotFoundError()

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

    def test_find__how_delta(self):
        with patch('tmqrfeed.chains.OptionChain._find_by_delta') as mock__find_by_delta:
            self.opt_chain.find(datetime.datetime(2011, 1, 19, 0, 0), 0.5, 'c', how='delta')

            self.assertRaises(ArgumentError, self.opt_chain.find, datetime.datetime(2011, 1, 19, 0, 0), 0, 'c',
                              how='delta')

            self.assertTrue(mock__find_by_delta.called)
            self.assertEqual(mock__find_by_delta.call_args[0][0], datetime.datetime(2011, 1, 19, 0, 0))
            self.assertEqual(mock__find_by_delta.call_args[0][1], 0.5)
            self.assertEqual(mock__find_by_delta.call_args[0][2], 'C')
            self.assertEqual(mock__find_by_delta.call_args[0][3], 5)
            self.assertEqual(mock__find_by_delta.call_args[0][4], 30)

            mock__find_by_delta.reset_mock()
            self.opt_chain.find(datetime.datetime(2011, 1, 19, 0, 0), 0.5, 'c', how='delta', error_limit=2,
                                strike_limit=20)
            self.assertTrue(mock__find_by_delta.called)
            self.assertEqual(mock__find_by_delta.call_args[0][0], datetime.datetime(2011, 1, 19, 0, 0))
            self.assertEqual(mock__find_by_delta.call_args[0][1], 0.5)
            self.assertEqual(mock__find_by_delta.call_args[0][2], 'C')
            self.assertEqual(mock__find_by_delta.call_args[0][3], 2)
            self.assertEqual(mock__find_by_delta.call_args[0][4], 20)

    def test__find_by_delta_valid(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 1000, 1500
            if isinstance(asset, OptionContract):
                return 0.10, 0.15

        def blackscholes_greeks_sideeffect(iscall, ulprice, strike, toexpiry, riskfreerate, iv):
            assert ulprice == 1000
            assert iv == 0.10

            if iscall == 1:
                delta = 1 - strike / (500.0 + 1500.0)
                return (delta,)
            elif iscall == 0:
                delta = -strike / (500.0 + 1500.0)
                return (delta,)

        # Checking mock delta algorithm for validity
        self.assertEqual(0.5, blackscholes_greeks_sideeffect(1, 1000, 1000, 0, 0, 0.1)[0])
        self.assertEqual(-0.5, blackscholes_greeks_sideeffect(0, 1000, 1000, 0, 0, 0.1)[0])

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 900, 0, 0, 0.1)[0] > 0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 1100, 0, 0, 0.1)[0] < 0.5)

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 900, 0, 0, 0.1)[0] > -0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 1100, 0, 0, 0.1)[0] < -0.5)

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        with patch('tmqrfeed.contracts.blackscholes_greeks') as mock_blacksholes_greeks:
            mock_blacksholes_greeks.side_effect = blackscholes_greeks_sideeffect
            dt = datetime.datetime(2011, 1, 19, 0, 0)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 0, 'C', 10)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 1, 'C', 10)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, float('nan'), 'C', 10)

            opt = self.opt_chain._find_by_delta(dt, 0.5, 'C', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('C', opt.ctype)
            self.assertEqual(1000, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, -0.5, 'P', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('P', opt.ctype)
            self.assertEqual(1000, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, 0.65, 'P', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('P', opt.ctype)
            self.assertEqual(1300, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, 0.64925, 'P', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('P', opt.ctype)
            self.assertEqual(1300, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, 0.4, 'P', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('P', opt.ctype)
            self.assertEqual(800, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, 0.6, 'C', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('C', opt.ctype)
            self.assertEqual(800, opt.strike)

            opt = self.opt_chain._find_by_delta(dt, 0.35, 'C', 10, strike_limit=2000)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('C', opt.ctype)
            self.assertEqual(1300, opt.strike)

    def test__find_by_delta_error_limit(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 1000, 1500
            if isinstance(asset, OptionContract):
                return 0.10, 0.15

        def blackscholes_greeks_sideeffect(iscall, ulprice, strike, toexpiry, riskfreerate, iv):
            assert ulprice == 1000
            assert iv == 0.10

            if iscall == 1:
                delta = 1 - strike / (500.0 + 1500.0)
                return (delta,)
            elif iscall == 0:
                if strike <= 600 or strike >= 1400:
                    raise OptionsEODQuotesNotFoundError()
                delta = -strike / (500.0 + 1500.0)
                return (delta,)

        # Checking mock delta algorithm for validity
        self.assertEqual(0.5, blackscholes_greeks_sideeffect(1, 1000, 1000, 0, 0, 0.1)[0])
        self.assertEqual(-0.5, blackscholes_greeks_sideeffect(0, 1000, 1000, 0, 0, 0.1)[0])

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 900, 0, 0, 0.1)[0] > 0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 1100, 0, 0, 0.1)[0] < 0.5)

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 900, 0, 0, 0.1)[0] > -0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 1100, 0, 0, 0.1)[0] < -0.5)

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        with patch('tmqrfeed.contracts.blackscholes_greeks') as mock_blacksholes_greeks:
            mock_blacksholes_greeks.side_effect = blackscholes_greeks_sideeffect
            dt = datetime.datetime(2011, 1, 19, 0, 0)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 0, 'C', 10)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 1, 'C', 10)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, float('nan'), 'C', 10)

            self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_delta, dt, 0.8, 'P', error_limit=5,
                              strike_limit=2000)

    def test__find_by_delta_strike_limit(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 1000, 1500
            if isinstance(asset, OptionContract):
                return 0.10, 0.15

        def blackscholes_greeks_sideeffect(iscall, ulprice, strike, toexpiry, riskfreerate, iv):
            assert ulprice == 1000
            assert iv == 0.10

            if iscall == 1:
                delta = 1 - strike / (500.0 + 1500.0)
                return (delta,)
            elif iscall == 0:
                delta = -strike / (500.0 + 1500.0)
                return (delta,)

        # Checking mock delta algorithm for validity
        self.assertEqual(0.5, blackscholes_greeks_sideeffect(1, 1000, 1000, 0, 0, 0.1)[0])
        self.assertEqual(-0.5, blackscholes_greeks_sideeffect(0, 1000, 1000, 0, 0, 0.1)[0])

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 900, 0, 0, 0.1)[0] > 0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(1, 1000, 1100, 0, 0, 0.1)[0] < 0.5)

        # ITM Call delta > 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 900, 0, 0, 0.1)[0] > -0.5)
        # OTM Call delta < 0.5
        self.assertTrue(blackscholes_greeks_sideeffect(0, 1000, 1100, 0, 0, 0.1)[0] < -0.5)

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        with patch('tmqrfeed.contracts.blackscholes_greeks') as mock_blacksholes_greeks:
            mock_blacksholes_greeks.side_effect = blackscholes_greeks_sideeffect
            dt = datetime.datetime(2011, 1, 19, 0, 0)

            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 0.8, 'P', error_limit=5, strike_limit=0)
            self.assertRaises(ArgumentError, self.opt_chain._find_by_delta, dt, 0.8, 'P', error_limit=5,
                              strike_limit=-1)

            opt = self.opt_chain._find_by_delta(dt, 0.35, 'C', 10, strike_limit=1)
            self.assertTrue(isinstance(opt, OptionContract))
            self.assertEqual('C', opt.ctype)
            self.assertEqual(1005, opt.strike)

    def test__find_by_delta_strike_limit_and_not_found(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 1000, 1500
            if isinstance(asset, OptionContract):
                return 0.10, 0.15

        def blackscholes_greeks_sideeffect(iscall, ulprice, strike, toexpiry, riskfreerate, iv):
            assert ulprice == 1000
            assert iv == 0.10

            raise OptionsEODQuotesNotFoundError()

        self.opt_chain.dm = MagicMock(self.opt_chain.dm)
        self.opt_chain.dm.price_get.side_effect = dm_price_get_sideeffect

        with patch('tmqrfeed.contracts.blackscholes_greeks') as mock_blacksholes_greeks:
            mock_blacksholes_greeks.side_effect = blackscholes_greeks_sideeffect
            dt = datetime.datetime(2011, 1, 19, 0, 0)

            self.assertRaises(ChainNotFoundError, self.opt_chain._find_by_delta, dt, 0.8, 'P', error_limit=5,
                              strike_limit=1)
