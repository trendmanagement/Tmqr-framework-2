import numpy as np

import pyximport
from tmqr.settings import *

pyximport.install(setup_args={"include_dirs": np.get_include()})

import unittest
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from unittest.mock import MagicMock
import pandas as pd
import os
import pytz
from datetime import datetime
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.quotes.dataframegetter import DataFrameGetter
from tmqr.errors import *


import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily
from tmqrfeed.manager import DataManager
from tmqrfeed.contracts import ContractBase
from tmqrfeed.position import Position


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

        self.fut1 = MagicMock(ContractBase("US.F.Fut1"))
        self.fut1.__str__.return_value = "TestAsset1"
        self.fut1.instrument_info.session = self.sess

        self.fut2 = MagicMock(ContractBase("US.F.Fut1"))
        self.fut2.__str__.return_value = "TestAsset2"
        self.fut2.instrument_info.session = self.sess

    def test_init_defaults(self):
        datafeed = MagicMock()
        datafeed.date_start = datetime(2012, 1, 1)
        datafeed.date_end = datetime(2013, 1, 1)
        dm = DataManager(datafeed=datafeed)

        qcf = QuoteContFut('US.CL', datamanager=dm, timeframe='D')
        self.assertEqual('US.CL', qcf.instrument)
        self.assertEqual(datafeed, qcf.dm.datafeed)
        self.assertEqual('D', qcf.timeframe)
        self.assertEqual(0, qcf.fut_offset)
        self.assertEqual(datafeed.date_start, qcf.date_start)
        self.assertEqual(datafeed.date_end, qcf.date_end)

        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL', datamanager=dm, timeframe=None)
        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL', datamanager=dm, timeframe="1M")
        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL', datamanager=dm, timeframe="D", decision_time_shift=-1)

    def test_init_errors(self):
        datafeed = MagicMock()
        datafeed.date_start = datetime(2012, 1, 1)

        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL')
        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL', datafeed=datafeed)
        self.assertRaises(ArgumentError, QuoteContFut, 'US.CL', datafeed=datafeed, timeframe='1M')

    def test_init_kwargs(self):
        datafeed = MagicMock()
        datafeed.date_start = datetime(2012, 1, 1)
        dm = DataManager(datafeed=datafeed)
        qcf = QuoteContFut('US.CL',
                           datamanager=dm,
                           timeframe='D',
                           fut_offset=1,
                           date_start=datetime(2013, 1, 1),
                           date_end=datetime(2014, 1, 1)
                           )
        self.assertEqual('US.CL', qcf.instrument)
        self.assertEqual(datafeed, qcf.dm.datafeed)
        self.assertEqual(dm, qcf.dm)
        self.assertEqual('D', qcf.timeframe)
        self.assertEqual(1, qcf.fut_offset)
        self.assertEqual(datetime(2013, 1, 1), qcf.date_start)
        self.assertEqual(datetime(2014, 1, 1), qcf.date_end)

    def test_calculate_fut_offset_series(self):
        # Do quick sanity checks for input data
        self.assertAlmostEqual(2769134.1100000003, self.series1.c.sum(), 4)
        self.assertAlmostEqual(3145255.6600000001, self.series2.c.sum(), 4)

        prev_df, prev_holdings = compress_daily(DataFrameGetter(self.series1), self.fut1, self.sess)
        new_df, new_holdings = compress_daily(DataFrameGetter(self.series2), self.fut2, self.sess)
        # Check compressed output validity
        self.assertAlmostEqual(2105.02, prev_df.c.sum(), 4)
        self.assertAlmostEqual(2392.78, new_df.c.sum(), 4)

        self.assertTrue(prev_df.index[-1] in new_df.index)

        dm = DataManager()
        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D')

        new_series_with_offset = qcont_fut._calculate_fut_offset_series(prev_df, new_df.copy())
        offset_df = new_df - new_series_with_offset
        self.assertEqual(0.1700000000000017, offset_df['o'].mean())
        self.assertEqual(0.1700000000000017, offset_df['l'].mean())
        self.assertEqual(0.1700000000000017, offset_df['c'].mean())
        self.assertEqual(0.1700000000000017, offset_df['h'].mean())
        self.assertEqual(0.1700000000000017, offset_df['exec'].mean())
        # Volume should be kept the same
        self.assertEqual(0, offset_df['v'].mean())

        self.assertTrue(prev_df.index[-1] not in new_series_with_offset)

    def test_calculate_fut_offset_series_zero_offset_if_not_found(self):
        prev_df, prev_holdings = compress_daily(DataFrameGetter(self.series1), self.fut1, self.sess)
        new_df, new_holdings = compress_daily(DataFrameGetter(self.series2), self.fut2, self.sess)
        # Check compressed output validity
        self.assertAlmostEqual(2105.02, prev_df.c.sum(), 4)
        self.assertAlmostEqual(2392.78, new_df.c.sum(), 4)

        feed = DataManager()
        qcont_fut = QuoteContFut('US.CL', datamanager=feed, timeframe='D')

        new_exclude = new_df[new_df.index > prev_df.index[-1]].copy()
        new_series_with_offset = qcont_fut._calculate_fut_offset_series(prev_df, new_exclude)
        offset_df = new_df - new_series_with_offset
        self.assertEqual(0, offset_df['o'].mean())
        self.assertEqual(0, offset_df['l'].mean())
        self.assertEqual(0, offset_df['c'].mean())
        self.assertEqual(0, offset_df['h'].mean())
        self.assertEqual(0, offset_df['exec'].mean())
        # Volume should be kept the same
        self.assertEqual(0, offset_df['v'].mean())

    def test_merge_series(self):
        # Do quick sanity checks for input data
        self.assertAlmostEqual(2769134.1100000003, self.series1.c.sum(), 4)
        self.assertAlmostEqual(3145255.6600000001, self.series2.c.sum(), 4)

        prev_df, prev_holdings = compress_daily(DataFrameGetter(self.series1), self.fut1, self.sess)
        new_df, new_holdings = compress_daily(DataFrameGetter(self.series2), self.fut2, self.sess)
        # Check compressed output validity
        self.assertAlmostEqual(2105.02, prev_df.c.sum(), 4)
        self.assertAlmostEqual(2392.78, new_df.c.sum(), 4)

        self.assertTrue(prev_df.index[-1] in new_df.index)

        dm = DataManager()
        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D')

        merged_df = qcont_fut.merge_series([prev_df, new_df])
        target_df = pd.concat([prev_df, new_df])
        self.assertEqual(len(merged_df), len(target_df))
        for i in range(len(merged_df)):
            self.assertTrue(np.all(merged_df.iloc[i] == target_df.iloc[i]))

    def test_str(self):
        dm = DataManager()
        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D')

        self.assertEqual('QuoteContFut-US.CL-D', str(qcont_fut))
        self.assertEqual('QuoteContFut-US.CL-D', f'{qcont_fut}')


    def test_apply_future_rollover_not_expired_future(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(datetime(2011, 1, 1), asset, 3.0)
        p.add_transaction(datetime(2011, 1, 2), asset, 3.0)

        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D')

        # Handle not expired future
        res_pos = qcont_fut._apply_future_rollover(p, datetime(2011, 1, 3).date())
        prec = res_pos.get_net_position(datetime(2011, 1, 2))
        self.assertEqual(prec, {asset: (1.0, 2.0, 3.0)})

    def test_apply_future_rollover_near_expired_future(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(datetime(2011, 1, 1), asset, 3.0)
        p.add_transaction(datetime(2011, 1, 2), asset, 3.0)

        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D')

        # Handle expired future
        res_pos = qcont_fut._apply_future_rollover(p, datetime(2011, 1, 1).date())
        prec = res_pos.get_net_position(datetime(2011, 1, 2))
        self.assertEqual(prec, {asset: (1.0, 2.0, 0.0)})

        prec = res_pos.get_net_position(datetime(2011, 1, 1))
        self.assertEqual(prec, {asset: (1.0, 2.0, 3.0)})





    def test_build(self):
        dm = DataManager()
        dm.session_set('US.CL')
        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D', date_start=datetime(2010, 1, 1))
        df, position = qcont_fut.build()

        for dt, pos_rec in position._position.items():
            if len(pos_rec) > 1:
                has_zero = False
                has_one = False

                for asset, pos_value in pos_rec.items():
                    if pos_value[2] == 1:
                        has_one = True
                    if pos_value[2] == 0:
                        has_zero = True
                self.assertEqual(True, has_zero)
                self.assertEqual(True, has_one)

        from tmqrfeed.costs import Costs
        dm.costs_set("US", Costs(3, 3))
        position.get_pnl_series()

    def test_build_date_end(self):
        dm = DataManager()
        dm.session_set('US.CL')
        qcont_fut = QuoteContFut('US.CL', datamanager=dm, timeframe='D', date_start=datetime(2010, 1, 1),
                                 date_end=datetime(2016, 1, 1))
        df, position = qcont_fut.build()

        self.assertEqual(datetime(2015, 12, 31).date(), df.index[-1].date())
