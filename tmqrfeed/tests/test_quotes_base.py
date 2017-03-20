import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tmqr.errors import *
from tmqrfeed.quotes.quote_base import QuoteBase


class QuoteBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.series1 = pd.DataFrame([
                                        {
                                            'dt': datetime(2012, 1, 1) + timedelta(days=x),
                                            'o': x * 1.0,
                                            'h': (x + 2) * 2.0,
                                            'l': (x + 4) * 4.0,
                                            'c': (x + 5) / 4.0,
                                            'v': (x + 10) / 2.0,
                                            'exec': (x * 10) / 2.0,
                                        } for x in range(10)
                                        ]).set_index('dt')

        self.series2 = pd.DataFrame([
                                        {
                                            'dt': datetime(2013, 1, 1) + timedelta(days=x),
                                            'o': x * 1.0,
                                            'h': (x + 2) * 2.0,
                                            'l': (x + 4) * 4.0,
                                            'c': (x + 5) / 4.0,
                                            'v': (x + 10) / 2.0,
                                            'exec': (x * 10) / 2.0,
                                        } for x in range(10)
                                        ]).set_index('dt')

    def test_merge_series(self):
        merged_df = QuoteBase.merge_series([self.series1, self.series2])
        target_df = pd.concat([self.series1, self.series2])
        self.assertEqual(len(merged_df), len(target_df))
        for i in range(len(merged_df)):
            self.assertTrue(np.all(merged_df.iloc[i] == target_df.iloc[i]))

    def test_merge_empty_series(self):
        self.assertRaises(QuoteEngineEmptyQuotes, QuoteBase.merge_series, [pd.DataFrame(), pd.DataFrame()])
        self.assertRaises(QuoteEngineEmptyQuotes, QuoteBase.merge_series, [None, None])

    def test_merge_positions(self):
        position1 = pd.DataFrame([
            {'date': datetime(2013, 1, 1),
             'px': 100,
             'qty': 1,
             'asset': "A1", },
            {'date': datetime(2013, 1, 2),
             'px': 100,
             'qty': 1,
             'asset': "A1", },
        ])

        position2 = pd.DataFrame([
            {'date': datetime(2013, 1, 2),
             'px': 200,
             'qty': 1,
             'asset': "A2", },
            {'date': datetime(2013, 1, 3),
             'px': 200,
             'qty': 1,
             'asset': "A2", },
        ])

        merged_pos = QuoteBase.merge_positions([position1, position2])
        self.assertEqual('date', merged_pos.index.name)

        self.assertEqual(4, len(merged_pos))

        df = merged_pos.ix[datetime(2013, 1, 1)]
        self.assertEqual(df['qty'], 1)
        self.assertEqual(df['px'], 100)
        self.assertEqual(df['asset'], 'A1')

        df = merged_pos.ix[datetime(2013, 1, 2)]

        self.assertEqual(df.iloc[0]['qty'], 0)
        self.assertEqual(df.iloc[0]['px'], 100)
        self.assertEqual(df.iloc[0]['asset'], 'A1')
        self.assertEqual(df.iloc[1]['qty'], 1)
        self.assertEqual(df.iloc[1]['px'], 200)
        self.assertEqual(df.iloc[1]['asset'], 'A2')

        df = merged_pos.ix[datetime(2013, 1, 3)]
        self.assertEqual(df['qty'], 1)
        self.assertEqual(df['px'], 200)
        self.assertEqual(df['asset'], 'A2')

    def test_merge_positions2(self):
        position1 = pd.DataFrame([
            {'date': datetime(2013, 1, 2),
             'px': 150,
             'qty': 1,
             'asset': "A1", },
            {'date': datetime(2013, 1, 2),
             'px': 100,
             'qty': 1,
             'asset': "A1", },
        ])

        position2 = pd.DataFrame([
            {'date': datetime(2013, 1, 2),
             'px': 200,
             'qty': 1,
             'asset': "A2", },
            {'date': datetime(2013, 1, 3),
             'px': 200,
             'qty': 1,
             'asset': "A2", },
        ])

        merged_pos = QuoteBase.merge_positions([position1, position2])
        self.assertEqual('date', merged_pos.index.name)

        self.assertEqual(4, len(merged_pos))

        df = merged_pos.ix[datetime(2013, 1, 2)]

        self.assertEqual(df.iloc[0]['qty'], 0)
        self.assertEqual(df.iloc[0]['px'], 150)
        self.assertEqual(df.iloc[0]['asset'], 'A1')
        self.assertEqual(df.iloc[1]['qty'], 0)
        self.assertEqual(df.iloc[1]['px'], 100)
        self.assertEqual(df.iloc[1]['asset'], 'A1')
        self.assertEqual(df.iloc[2]['qty'], 1)
        self.assertEqual(df.iloc[2]['px'], 200)
        self.assertEqual(df.iloc[2]['asset'], 'A2')

        df = merged_pos.ix[datetime(2013, 1, 3)]
        self.assertEqual(df['qty'], 1)
        self.assertEqual(df['px'], 200)
        self.assertEqual(df['asset'], 'A2')

    def test_merge_positions_none(self):
        merged_pos = QuoteBase.merge_positions([None, None])
        self.assertEqual(merged_pos, None)
