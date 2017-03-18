import unittest
from datetime import time
from unittest import mock

import pandas as pd
import pytz

from tmqr.errors import *
from tmqr.settings import *
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.chains import FutureChain
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.dataengines import DataEngineMongo
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.instrumentinfo import InstrumentInfo


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
            eng_ainfo.return_value = {
                'futures_months': [3, 6, 9, 12],
                'instrument': 'US.ES',
                'market': 'US',
                'rollover_days_before': 2,
                'ticksize': 0.25,
                'tickvalue': 12.5,
                'timezone': 'US/Pacific',
                'data_futures_src': SRC_INTRADAY,
                'data_options_src': SRC_OPTIONS,
                'trading_session': [{
                    'decision': '10:40',
                    'dt': datetime(1900, 1, 1, 0, 0),
                    'execution': '10:45',
                    'start': '00:32'}]}
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
            eng_ainfo.return_value = {
                'futures_months': [3, 6, 9, 12],
                'instrument': 'US.ES',
                'market': 'US',
                'rollover_days_before': 2,
                'ticksize': 0.25,
                'tickvalue': 12.5,
                'timezone': 'US/Pacific',
                'data_futures_src': SRC_INTRADAY,
                'data_options_src': SRC_OPTIONS,
                'trading_session': [{
                    'decision': '10:40',
                    'dt': datetime(1900, 1, 1, 0, 0),
                    'execution': '10:45',
                    'start': '00:32'}]}
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
            dfeed = DataFeed()
            chain = dfeed.get_fut_chain('US.CL')
            self.assertEqual(FutureChain, type(chain))

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
