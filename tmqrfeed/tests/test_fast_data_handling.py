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
from tmqrfeed.fast_data_handling import find_time_indexes


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
        self.assertEqual(1, len(holdings))

        dt = pd.Timestamp('2011-12-20')
        start, decision, execution, next_sess_date = self.sess.get(dt)

        idx_list = find_time_indexes(df, [decision, execution])

        self.assertEqual(2, len(idx_list))
        self.assertEqual(holdings.iloc[0]['date'], df.index[idx_list[0]])
        self.assertEqual(holdings.iloc[0]['decision_px'], df['c'][idx_list[0]])

        self.assertEqual(holdings.iloc[0]['quote_dt'], df.index[idx_list[1]])
        self.assertEqual(holdings.iloc[0]['exec_dt'], df.index[idx_list[1]])
        self.assertEqual(holdings.iloc[0]['exec_px'], df['c'][idx_list[1]])


if __name__ == '__main__':
    unittest.main()
