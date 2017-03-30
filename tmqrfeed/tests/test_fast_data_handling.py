import unittest
from  datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytz
import pyximport

from tmqr.errors import *

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily
import os

from tmqrfeed.assetsession import AssetSession
from tmqrfeed.quotes.dataframegetter import DataFrameGetter
from tmqrfeed.fast_data_handling import find_quotes


class FastDataHandlingTestCase(unittest.TestCase):
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

    def test_find_time_indexes_valid(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)
        # 'holdings' is a tuple of: date, asset, decision_px, exec_px, qty

        self.assertEqual(1, len(holdings))

        dt = pd.Timestamp('2011-12-20')
        start, decision, execution, next_sess_date = self.sess.get(dt)

        idx_list = find_quotes(df, [decision, execution])

        self.assertEqual(2, len(idx_list))
        self.assertEqual(holdings[0][0], idx_list[0][0])
        self.assertEqual(holdings[0][2], idx_list[0][1])

        self.assertEqual(holdings[0][3], idx_list[1][1])

    def test_find_time_indexes_out_of_session(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        df = df.between_time('11:00', '15:00')
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)
        self.assertEqual(0, len(holdings))

        dt = pd.Timestamp('2011-12-20')
        start, decision, execution, next_sess_date = self.sess.get(dt)

        self.assertRaises(IntradayQuotesNotFoundError, find_quotes, df, [decision, execution])

    def test_find_time_indexes_partial_session(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        df = df.between_time('00:00', '09:00')
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)
        # 'holdings' is a tuple of: date, asset, decision_px, exec_px, qty
        self.assertEqual(1, len(holdings))

        dt = pd.Timestamp('2011-12-20')
        start, decision, execution, next_sess_date = self.sess.get(dt)

        idx_list = find_quotes(df, [decision, execution])

        self.assertEqual(2, len(idx_list))
        self.assertEqual(pd.Timestamp('2011-12-20 09:00:00-0800'), idx_list[0][0])
        self.assertEqual(holdings[0][2], idx_list[0][1])

        self.assertEqual(pd.Timestamp('2011-12-20 09:00:00-0800'), idx_list[1][0])
        self.assertEqual(pd.Timestamp('2011-12-20 09:00:00-0800'), idx_list[1][0])
        self.assertEqual(holdings[0][3], idx_list[1][1])

    def test_find_time_missing_time_in_df(self):
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        df.index = df.index.tz_localize(pytz.utc).tz_convert(self.tz)
        df = df.drop([df.ix['2011-12-20 10:40'].name,
                      df.ix['2011-12-20 10:45'].name])
        asset_mock = MagicMock()
        asset_mock.__str__.return_value = "TestAsset"
        asset_mock.instrument_info.session = self.sess
        dfg = DataFrameGetter(df)

        comp_df, holdings = compress_daily(dfg, asset_mock)
        # 'holdings' is a tuple of: date, asset, decision_px, exec_px, qty
        self.assertEqual(1, len(holdings))

        dt = pd.Timestamp('2011-12-20')
        start, decision, execution, next_sess_date = self.sess.get(dt)

        idx_list = find_quotes(df, [decision, execution])

        self.assertEqual(2, len(idx_list))
        self.assertEqual(2, len(idx_list))
        self.assertEqual(pd.Timestamp('2011-12-20 10:39:00-0800'), idx_list[0][0])
        self.assertEqual(holdings[0][2], idx_list[0][1])

        self.assertEqual(holdings[0][3], idx_list[1][1])



if __name__ == '__main__':
    unittest.main()
