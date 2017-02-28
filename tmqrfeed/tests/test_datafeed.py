import unittest
from datetime import datetime
from unittest import mock

from tmqrfeed.assetinfo import AssetInfo
from tmqrfeed.chains import FutureChain
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.dataengines import DataEngineMongo
from tmqrfeed.datafeed import DataFeed


class DataFeedTestCase(unittest.TestCase):
    def test_init_default(self):
        dfeed = DataFeed()
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.data_engine_settings, {})
        self.assertEqual(dfeed.date_start, datetime(1900, 1, 1))
        self.assertEqual(dfeed.ainfo_cache, {})

    def test_init_kwargs(self):
        dfeed = DataFeed(data_engine_settings={'test': 'ok'},
                         date_start=datetime(2011, 1, 1),
                         )
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.data_engine_settings, {'test': 'ok'})
        self.assertEqual(dfeed.date_start, datetime(2011, 1, 1))

    def test_get_asset_info(self):
        dfeed = DataFeed()
        self.assertRaises(ValueError, dfeed.get_asset_info, 'CL')
        self.assertRaises(ValueError, dfeed.get_asset_info, '')
        self.assertRaises(ValueError, dfeed.get_asset_info, 'CL.US.S')

        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.get_asset_info') as eng_ainfo:
            eng_ainfo.return_value = {
                'futures_months': [3, 6, 9, 12],
                'instrument': 'US.ES',
                'market': 'US',
                'rollover_days_before': 2,
                'ticksize': 0.25,
                'tickvalue': 12.5,
                'timezone': 'US/Pacific',
                'trading_session': [{
                    'decision': '10:40',
                    'dt': datetime(1900, 1, 1, 0, 0),
                    'execution': '10:45',
                    'start': '00:32'}]}
            ainfo = dfeed.get_asset_info("US.ES")
            self.assertEqual(AssetInfo, type(ainfo))
            self.assertEqual('US.ES', ainfo.instrument)
            self.assertEqual('US', ainfo.market)
            self.assertEqual(True, eng_ainfo.called)

            # Check that asset info requested only once (i.e. cached)
            eng_ainfo.reset_mock()
            ainfo = dfeed.get_asset_info("US.ES")
            self.assertEqual(False, eng_ainfo.called)

    def test_get_fut_chain_no_data(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.get_futures_chain') as mock_eng_chain:
            mock_eng_chain.return_value = []
            dfeed = DataFeed()
            self.assertRaises(ValueError, dfeed.get_fut_chain, 'US.NONEXISTING')

    def test_get_fut_chain_success(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.get_futures_chain') as mock_eng_chain:
            mock_eng_chain.return_value = [{'tckr': 'US.F.CL.G11.110120'},
                                           {'tckr': 'US.F.CL.H11.110222'},
                                           {'tckr': 'US.F.CL.J11.110322'},
                                           {'tckr': 'US.F.CL.K11.110419'}, ]
            dfeed = DataFeed()
            chain = dfeed.get_fut_chain('US.CL')
            self.assertEqual(FutureChain, type(chain))

    def test_get_contract_info(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.get_contract_info') as mock_contr_info:
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
