import os
import pickle
import unittest
from collections import OrderedDict
from datetime import time
from unittest import mock

import numpy as np
import pandas as pd
import pytz

from tmqr.errors import *
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.chains import FutureChain
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.contracts import *
from tmqrfeed.dataengines import DataEngineMongo
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.instrumentinfo import InstrumentInfo
from tmqrfeed.manager import DataManager
from tmqrfeed.tests.shared_asset_info import ASSET_INFO


class DataFeedTestCase(unittest.TestCase):
    def test_init_default(self):
        dfeed = DataFeed()
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.data_engine_settings, {})
        self.assertEqual(dfeed.date_start, datetime(1900, 1, 1))
        self.assertEqual(dfeed.instrument_info_cache, {})

    def test_init_kwargs(self):
        dfeed = DataFeed(data_engine_settings={'test': 'ok'},
                         date_start=datetime(2011, 1, 1),
                         )
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.data_engine_settings, {'test': 'ok'})
        self.assertEqual(dfeed.date_start, datetime(2011, 1, 1))

    def test_get_asset_info(self):
        dfeed = DataFeed()
        self.assertRaises(ValueError, dfeed.get_instrument_info, 'CL')
        self.assertRaises(ValueError, dfeed.get_instrument_info, '')
        self.assertRaises(ValueError, dfeed.get_instrument_info, 'CL.US.S')

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_instrument_info') as eng_ainfo:
            eng_ainfo.return_value = ASSET_INFO
            ainfo = dfeed.get_instrument_info("US.ES")
            self.assertEqual(InstrumentInfo, type(ainfo))
            self.assertEqual('US.ES', ainfo.instrument)
            self.assertEqual('US', ainfo.market)
            self.assertEqual(True, eng_ainfo.called)

            # Check that asset info requested only once (i.e. cached)
            eng_ainfo.reset_mock()
            ainfo = dfeed.get_instrument_info("US.ES")
            self.assertEqual(False, eng_ainfo.called)

    def test_get_instrument_info_caching(self):
        dfeed = DataFeed()

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_instrument_info') as eng_ainfo:
            eng_ainfo.return_value = ASSET_INFO
            ainfo = dfeed.get_instrument_info("US.ES")
            self.assertEqual(True, eng_ainfo.called)

            # Check that asset info requested only once (i.e. cached)
            eng_ainfo.reset_mock()
            ainfo = dfeed.get_instrument_info("US.ES")
            self.assertEqual(False, eng_ainfo.called)

    def test_get_fut_chain_no_data(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_futures_chain') as mock_eng_chain:
            mock_eng_chain.return_value = []
            dfeed = DataFeed()
            self.assertRaises(ArgumentError, dfeed.get_fut_chain, 'US.NONEXISTING')

    def test_get_fut_chain_success(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_futures_chain') as mock_eng_chain:
            mock_eng_chain.return_value = [{'tckr': 'US.F.CL.G11.110120'},
                                           {'tckr': 'US.F.CL.H11.110222'},
                                           {'tckr': 'US.F.CL.J11.110322'},
                                           {'tckr': 'US.F.CL.K11.110419'}, ]
            dm = DataManager()
            chain = dm.datafeed.get_fut_chain('US.CL', rollover_days_before=2, futures_months=list(range(1, 12)))
            self.assertEqual(FutureChain, type(chain))
            for c in chain.get_all():
                self.assertEqual(FutureContract, type(c))
                self.assertTrue(c.dm is not None)
                self.assertEqual(DataManager, type(c.dm))

    def test_get_contract_info(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_contract_info') as mock_contr_info:
            mock_contr_info.return_value = {

                "underlying": "US.CL",
                "type": "F",
                "contr": "CL.Q83",
                "tckr": "US.F.CL.Q83.830720",
                "instr": "US.CL",
                "exp": datetime(1983, 7, 20),
                "mkt": "US"
            }
            dfeed = DataFeed()
            ci = dfeed.get_contract_info("US.F.CL.Q83.830720")
            self.assertEqual(ContractInfo, type(ci))
            self.assertEqual(ci.ticker, "US.F.CL.Q83.830720")
            mock_contr_info.reset_mock()

            ci = dfeed.get_contract_info("US.F.CL.Q83.830720")
            self.assertEqual(False, mock_contr_info.called)

    def test_get_contract_info_caching(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_contract_info') as mock_contr_info:
            mock_contr_info.return_value = {

                "underlying": "US.CL",
                "type": "F",
                "contr": "CL.Q83",
                "tckr": "US.F.CL.Q83.830720",
                "instr": "US.CL",
                "exp": datetime(1983, 7, 20),
                "mkt": "US"
            }
            dfeed = DataFeed()
            ci = dfeed.get_contract_info("US.F.CL.Q83.830720")
            self.assertEqual(True, mock_contr_info.called)
            mock_contr_info.reset_mock()

            ci = dfeed.get_contract_info("US.F.CL.Q83.830720")
            self.assertEqual(False, mock_contr_info.called)

    def test_get_raw_series(self):
        info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:30'},

                {
                    'decision': '11:40',
                    'dt': datetime(2009, 12, 31),
                    'execution': '11:45',
                    'start': '01:30'},

                {
                    'decision': '12:40',
                    'dt': datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:30'},
            ]
        }
        tz = pytz.timezone(info_dic['timezone'])
        sess = AssetSession(info_dic['trading_session'], tz)

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_raw_series') as mock_db_get_raw_series:
            base_date = datetime(2008, 10, 10)
            data = [
                {'dt': datetime.combine(base_date, time(0, 29)), 'v': 0},
                {'dt': datetime.combine(base_date, time(0, 30)), 'v': 1},
                {'dt': datetime.combine(base_date, time(0, 31)), 'v': 1},
                {'dt': datetime.combine(base_date, time(10, 39)), 'v': 1},
                {'dt': datetime.combine(base_date, time(10, 40)), 'v': 1},
                {'dt': datetime.combine(base_date, time(10, 41)), 'v': 0},
            ]
            source_df = pd.DataFrame(data).set_index('dt').tz_localize('US/Pacific').tz_convert("UTC")
            mock_db_get_raw_series.return_value = source_df, QTYPE_INTRADAY
            dfeed = DataFeed()

            result = dfeed.get_raw_series('US.F.CL.Q83.830720', SRC_INTRADAY)
            for d in source_df.index:
                self.assertTrue(d in result.index)
            #
            # Test timezone
            #
            result = dfeed.get_raw_series('US.F.CL.Q83.830720', SRC_INTRADAY,
                                          timezone=pytz.timezone('US/Pacific'))
            self.assertEqual(pytz.timezone('US/Pacific'), result.index.tz)

            result = dfeed.get_raw_series('US.F.CL.Q83.830720', SRC_INTRADAY,
                                          timezone='US/Pacific')
            self.assertEqual(pytz.timezone('US/Pacific'), result.index.tz)

            # Test not implemented stuff
            mock_db_get_raw_series.return_value = source_df, 'UNKNOWN_QTYPE'
            self.assertRaises(NotImplementedError, dfeed.get_raw_series, 'US.F.CL.Q83.830720', SRC_INTRADAY)

    def test_get_raw_price_intraday(self):
        info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:30'},

                {
                    'decision': '11:40',
                    'dt': datetime(2009, 12, 31),
                    'execution': '11:45',
                    'start': '01:30'},

                {
                    'decision': '12:40',
                    'dt': datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:30'},
            ]
        }
        tz = pytz.timezone(info_dic['timezone'])
        sess = AssetSession(info_dic['trading_session'], tz)

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_raw_series') as mock_db_get_raw_series:
            base_date = datetime(2008, 10, 10)
            data = [
                {'dt': tz.localize(datetime.combine(base_date, time(0, 29))), 'c': 0},
                {'dt': tz.localize(datetime.combine(base_date, time(0, 30))), 'c': 1},
                {'dt': tz.localize(datetime.combine(base_date, time(0, 31))), 'c': 1},
                {'dt': tz.localize(datetime.combine(base_date, time(10, 39))), 'c': 100},
                {'dt': tz.localize(datetime.combine(base_date, time(10, 40))), 'c': 1},
                {'dt': tz.localize(datetime.combine(base_date, time(10, 41))), 'c': 0},
            ]
            source_df = pd.DataFrame(data).set_index('dt')
            mock_db_get_raw_series.return_value = source_df, QTYPE_INTRADAY
            dfeed = DataFeed()

            result = dfeed.get_raw_prices('US.F.CL.Q83.830720',
                                          SRC_INTRADAY,
                                          [tz.localize(datetime(2008, 10, 10, 10, 39))],
                                          timezone=tz)
            self.assertEqual(1, len(result))
            self.assertEqual(result[0], 100)

            #
            # Test timezone
            #
            result = dfeed.get_raw_prices('US.F.CL.Q83.830720', SRC_INTRADAY,
                                          [tz.localize(datetime(2008, 10, 10, 10, 39))],
                                          timezone='US/Pacific')
            self.assertEqual(result[0], 100)

            self.assertRaises(ArgumentError, dfeed.get_raw_prices, 'US.F.CL.Q83.830720', SRC_INTRADAY,
                              [tz.localize(datetime(2008, 10, 10, 10, 39))])

            # Test not implemented stuff
            mock_db_get_raw_series.return_value = source_df, 'UNKNOWN_QTYPE'
            self.assertRaises(NotImplementedError, dfeed.get_raw_prices, 'US.F.CL.Q83.830720', SRC_INTRADAY,
                              [tz.localize(datetime(2008, 10, 10, 10, 39))], timezone='US/Pacific')

    def test_get_raw_price_options_eod(self):
        tz = pytz.timezone("US/Pacific")
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_raw_series') as mock_db_get_raw_series:
            base_date = datetime(2008, 10, 10)
            data = [
                {'dt': datetime(2011, 1, 1, 23, 59, 59), 'iv': 1.0},
                {'dt': datetime(2011, 1, 2, 23, 59, 59), 'iv': 2.0},
                {'dt': datetime(2011, 1, 3, 23, 59, 59), 'iv': 3.0},
                {'dt': datetime(2011, 1, 4, 23, 59, 59), 'iv': 4.0},
            ]
            source_df = pd.DataFrame(data).set_index('dt')
            mock_db_get_raw_series.return_value = {'data': source_df}, QTYPE_OPTIONS_EOD
            dfeed = DataFeed()

            result = dfeed.get_raw_prices('US.F.CL.Q83.830720',
                                          SRC_OPTIONS_EOD,
                                          [tz.localize(datetime(2011, 1, 1, 10, 39)),
                                           tz.localize(datetime(2011, 1, 2, 10, 39))
                                           ],
                                          timezone=tz)
            self.assertEqual(2, len(result))
            self.assertEqual(result[0], 1)
            self.assertEqual(result[1], 2)
            #
            # Quote not found error
            #
            self.assertRaises(OptionsEODQuotesNotFoundError, dfeed.get_raw_prices, 'US.F.CL.Q83.830720',
                              SRC_OPTIONS_EOD,
                              [tz.localize(datetime(2011, 1, 10, 10, 39)),
                               tz.localize(datetime(2011, 1, 20, 10, 39))
                               ],
                              timezone=tz)
            #
            # data_options_use_prev_date kwarg True
            #
            result = dfeed.get_raw_prices('US.F.CL.Q83.830720',
                                          SRC_OPTIONS_EOD,
                                          [tz.localize(datetime(2011, 1, 1, 10, 39)),
                                           tz.localize(datetime(2011, 1, 2, 10, 39))
                                           ],
                                          timezone=tz,
                                          data_options_use_prev_date=True)
            self.assertEqual(2, len(result))
            self.assertTrue(np.isnan(result[0]))
            self.assertEqual(result[1], 1)
            #

    def test_get_options_chains(self):
        fn = os.path.abspath(os.path.join(__file__, '../', 'option_chain_list_es.pkl'))

        with open(fn, 'rb') as f:
            chain_list = pickle.load(f)

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_option_chains') as mock_db_get_option_chains:
            with mock.patch('tmqrfeed.datafeed.OptionChainList') as mock_cls_chain_list:
                mock_db_get_option_chains.return_value = chain_list
                dfeed = DataFeed()
                dfeed.dm = 'DM'

                dfeed.get_option_chains(FutureContract('US.F.ES.H11.110318'))

                self.assertEqual(True, mock_cls_chain_list.called)
                optchain_call_args = mock_cls_chain_list.call_args[0][0]
                self.assertEqual('DM', mock_cls_chain_list.call_args[1]['datamanager'])

                self.assertEqual(OrderedDict, type(optchain_call_args))
                self.assertEqual(3, len(optchain_call_args))

                strike_count = 0
                for k, v in optchain_call_args.items():
                    self.assertEqual(datetime, type(k))
                    self.assertEqual(OrderedDict, type(v))

                    prev_strike = 0.0
                    for strike, opts in v.items():
                        strike_count += 1
                        self.assertGreater(strike, prev_strike)
                        self.assertEqual(OptionContract, type(opts[0]))
                        self.assertEqual(OptionContract, type(opts[1]))
                        self.assertTrue(f'@{strike}' in opts[0].ticker)
                        self.assertTrue(f'@{strike}' in opts[1].ticker)
                        self.assertTrue('.C.' in opts[0].ticker)
                        self.assertTrue('.P.' in opts[1].ticker)
                        prev_strike = strike

                self.assertEqual(strike_count, 1110 / 2)

