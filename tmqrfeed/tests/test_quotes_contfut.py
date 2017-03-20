import numpy as np

try:
    from tmqr.settings_local import *
except:
    pass
import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})

from tmqrfeed.datafeed import DataFeed
import unittest
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from unittest.mock import MagicMock
import pandas as pd
import os
import pytz
from datetime import datetime
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.quotes.dataframegetter import DataFrameGetter

import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily


class QuoteContFutTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
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

        self.series1 = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_for_contfut1.csv.gz')),
                                   parse_dates=True,
                                   index_col=0, compression='gzip')
        self.series1.index = self.series1.index.tz_localize(pytz.utc).tz_convert(self.tz)

        self.series2 = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series_for_contfut2.csv.gz')),
                                   parse_dates=True,
                                   index_col=0, compression='gzip')
        self.series2.index = self.series2.index.tz_localize(pytz.utc).tz_convert(self.tz)

        self.fut1 = MagicMock()
        self.fut1.__str__.return_value = "TestAsset1"
        self.fut1.instrument_info.session = self.sess

        self.fut2 = MagicMock()
        self.fut2.__str__.return_value = "TestAsset2"
        self.fut2.instrument_info.session = self.sess

    def test_calculate_fut_offset_series(self):
        # Do quick sanity checks for input data
        self.assertEqual(2769134.1100000003, self.series1.c.sum())
        self.assertEqual(3145255.6600000001, self.series2.c.sum())

        prev_df, prev_holdings = compress_daily(DataFrameGetter(self.series1), self.fut1)
        new_df, new_holdings = compress_daily(DataFrameGetter(self.series2), self.fut2)
        # Check compressed output validity
        self.assertEqual(2105.0499999999997, prev_df.c.sum())
        self.assertEqual(2392.73, new_df.c.sum())

        self.assertTrue(prev_df.index[-1] in new_df.index)

        feed = DataFeed()
        qcont_fut = QuoteContFut('US.CL', datafeed=feed, timeframe='D')

        new_series_with_offset = qcont_fut.calculate_fut_offset_series(prev_df, new_df.copy())
        offset_df = new_df - new_series_with_offset
        self.assertEqual(0.15000000000000568, offset_df['o'].mean())
        self.assertEqual(0.15000000000000568, offset_df['l'].mean())
        self.assertEqual(0.15000000000000568, offset_df['c'].mean())
        self.assertEqual(0.15000000000000568, offset_df['h'].mean())
        self.assertEqual(0.15000000000000568, offset_df['exec'].mean())
        # Volume should be kept the same
        self.assertEqual(0, offset_df['v'].mean())

        self.assertTrue(prev_df.index[-1] not in new_series_with_offset)

    def test_calculate_fut_offset_series_zero_offset_if_not_found(self):
        prev_df, prev_holdings = compress_daily(DataFrameGetter(self.series1), self.fut1)
        new_df, new_holdings = compress_daily(DataFrameGetter(self.series2), self.fut2)
        # Check compressed output validity
        self.assertEqual(2105.0499999999997, prev_df.c.sum())
        self.assertEqual(2392.73, new_df.c.sum())

        feed = DataFeed()
        qcont_fut = QuoteContFut('US.CL', datafeed=feed, timeframe='D')

        new_exclude = new_df[new_df.index > prev_df.index[-1]].copy()
        new_series_with_offset = qcont_fut.calculate_fut_offset_series(prev_df, new_exclude)
        offset_df = new_df - new_series_with_offset
        self.assertEqual(0, offset_df['o'].mean())
        self.assertEqual(0, offset_df['l'].mean())
        self.assertEqual(0, offset_df['c'].mean())
        self.assertEqual(0, offset_df['h'].mean())
        self.assertEqual(0, offset_df['exec'].mean())
        # Volume should be kept the same
        self.assertEqual(0, offset_df['v'].mean())



    def test_build(self):
        feed = DataFeed()
        qcont_fut = QuoteContFut('US.CL', datafeed=feed, timeframe='D')
        qcont_fut.build()
