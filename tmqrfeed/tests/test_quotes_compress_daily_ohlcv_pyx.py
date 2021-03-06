import unittest
from  datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytz
import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily
import os

from tmqrfeed.assetsession import AssetSession
from tmqrfeed.quotes.dataframegetter import DataFrameGetter
from  tmqrfeed.contracts import ContractBase
from tmqrfeed.position import Position


class CompressDailyOHLCVCythonizedTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {
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
                'start': '00:32'},
            ]
        }
        self.tz = pytz.timezone(self.info_dic['timezone'])
        self.sess = AssetSession(self.info_dic['trading_session'], self.tz)

    def test_compress_valid_series(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock(ContractBase("US.S.GOOG"))
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock, self.sess)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == Position)

        row_1 = comp_df.iloc[0]
        self.assertEqual(row_1.name.date(), datetime(2011, 12, 20).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row_1.name.tzinfo, self.tz.localize(datetime(2011, 12, 20)).tzinfo)
        self.assertEqual(row_1.name, self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual(row_1['o'], 94.77)
        self.assertEqual(row_1['h'], 97.61)
        self.assertEqual(row_1['l'], 94.75)
        self.assertEqual(row_1['c'], 97.47)
        self.assertEqual(row_1['v'], 151103 + 141)
        self.assertEqual(row_1['exec'], 97.39)
        self.assertEqual(1, len(comp_df))

    def test_compress_valid_series_2days(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_2days.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock(ContractBase("US.S.GOOG"))
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock, self.sess)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == Position)

        self.assertEqual(2, len(comp_df))

        row = comp_df.iloc[0]
        self.assertEqual(row.name.date(), datetime(2011, 12, 20).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row.name.tzinfo, self.tz.localize(datetime(2011, 12, 20)).tzinfo)
        self.assertEqual(row.name, self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual(row['o'], 94.77)
        self.assertEqual(row['h'], 97.61)
        self.assertEqual(row['l'], 94.75)
        self.assertEqual(row['c'], 97.47)
        self.assertEqual(row['v'], 151103 + 141)
        self.assertEqual(row['exec'], 97.39)

        row = comp_df.iloc[1]
        self.assertEqual(row.name.date(), datetime(2011, 12, 21).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row.name.tzinfo, self.tz.localize(datetime(2011, 12, 21)).tzinfo)
        self.assertEqual(row.name, self.tz.localize(datetime(2011, 12, 21, 10, 40, 00)))
        self.assertEqual(row['o'], 94.77)
        self.assertEqual(row['h'], 97.61)
        self.assertEqual(row['l'], 94.75)
        self.assertEqual(row['c'], 97.47)
        self.assertEqual(row['v'], 151103 + 141)
        self.assertEqual(row['exec'], 97.39)

    def test_compress_2days_holdings(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_2days.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock(ContractBase("US.S.GOOG"))
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock, self.sess)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == Position)
        self.assertEqual(2, len(holdings._position))


        # Tuple of: date, asset, decision_px, exec_px, qty
        pos = holdings.get_net_position(self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual(pos, {asset_mock: (97.47, 97.39, 1)})

        pos = holdings.get_net_position(self.tz.localize(datetime(2011, 12, 21, 10, 40, 00)))
        self.assertEqual(pos, {asset_mock: (97.47, 97.39, 1)})


    def test_compress_invalid_series(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)

        df = df.between_time('11:00', '14:00')

        asset_mock = MagicMock(ContractBase("US.S.GOOG"))
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock, self.sess)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == Position)

        self.assertEqual(0, len(comp_df))
        self.assertEqual(0, len(holdings._position))

    def test_compress_desicion_time_shift(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock(ContractBase("US.S.GOOG"))
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock, self.sess, decision_time_shift=7)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == Position)

        self.assertEqual(7, holdings.kwargs['decision_time_shift'])

        self.assertEqual(1, len(comp_df))

        row = comp_df.iloc[0]
        self.assertEqual(row.name.date(), datetime(2011, 12, 20).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row.name.tzinfo, self.tz.localize(datetime(2011, 12, 20)).tzinfo)
        self.assertEqual(row.name, self.tz.localize(datetime(2011, 12, 20, 10, 33, 00)))
        self.assertEqual(row['o'], 94.77)
        self.assertEqual(row['h'], 97.61)
        self.assertEqual(row['l'], 94.75)
        self.assertEqual(row['c'], 97.44)
        self.assertEqual(row['v'], 150482)
        self.assertEqual(row['exec'], 97.39)
