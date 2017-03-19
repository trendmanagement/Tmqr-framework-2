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
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == pd.DataFrame)

        row_1 = comp_df.iloc[0]
        self.assertEqual(row_1.name.date(), datetime(2011, 12, 20).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row_1.name.tzinfo, self.tz.localize(datetime(2011, 12, 20)).tzinfo)
        self.assertEqual(row_1.name, self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual(row_1['o'], 94.77)
        self.assertEqual(row_1['h'], 97.61)
        self.assertEqual(row_1['l'], 94.75)
        self.assertEqual(row_1['c'], 97.48)
        self.assertEqual(row_1['v'], 151103)
        self.assertEqual(1, len(comp_df))

    def test_compress_valid_series_2days(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_2days.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == pd.DataFrame)

        self.assertEqual(2, len(comp_df))

        row = comp_df.iloc[0]
        self.assertEqual(row.name.date(), datetime(2011, 12, 20).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row.name.tzinfo, self.tz.localize(datetime(2011, 12, 20)).tzinfo)
        self.assertEqual(row.name, self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual(row['o'], 94.77)
        self.assertEqual(row['h'], 97.61)
        self.assertEqual(row['l'], 94.75)
        self.assertEqual(row['c'], 97.48)
        self.assertEqual(row['v'], 151103)
        self.assertEqual(row['exec'], 97.45)

        row = comp_df.iloc[1]
        self.assertEqual(row.name.date(), datetime(2011, 12, 21).date())

        # TZ trick: date's tzinfo is not equal to pytz.timezone (this is python wide bug), applying workaround
        self.assertEqual(row.name.tzinfo, self.tz.localize(datetime(2011, 12, 21)).tzinfo)
        self.assertEqual(row.name, self.tz.localize(datetime(2011, 12, 21, 10, 40, 00)))
        self.assertEqual(row['o'], 94.77)
        self.assertEqual(row['h'], 97.61)
        self.assertEqual(row['l'], 94.75)
        self.assertEqual(row['c'], 97.48)
        self.assertEqual(row['v'], 151103)
        self.assertEqual(row['exec'], 97.45)

    def test_compress_2days_holdings(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_2days.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)

        self.assertTrue(type(comp_df) == pd.DataFrame)
        self.assertTrue(type(holdings) == pd.DataFrame)

        self.assertEqual(2, len(holdings))

        row = holdings.iloc[0]
        dt = row.name[0]
        asset = row.name[1]
        self.assertEqual(dt, self.tz.localize(datetime(2011, 12, 20, 10, 40, 00)))
        self.assertEqual("TestAsset", str(asset))
        self.assertEqual(self.tz.localize(datetime(2011, 12, 20, 10, 45, 00)), row['exec_time'])
        self.assertEqual(self.tz.localize(datetime(2011, 12, 20, 10, 44, 00)), row['quote_time'])
        self.assertEqual(97.45, row['px'])
        self.assertEqual(1, row['qty'])

        row = holdings.iloc[1]
        dt = row.name[0]
        asset = row.name[1]
        self.assertEqual(dt, self.tz.localize(datetime(2011, 12, 21, 10, 40, 00)))
        self.assertEqual("TestAsset", str(asset))
        self.assertEqual(self.tz.localize(datetime(2011, 12, 21, 10, 45, 00)), row['exec_time'])
        self.assertEqual(self.tz.localize(datetime(2011, 12, 21, 10, 44, 00)), row['quote_time'])
        self.assertEqual(97.45, row['px'])
        self.assertEqual(1, row['qty'])
