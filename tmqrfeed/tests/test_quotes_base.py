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

    def test_init(self):
        self.assertRaises(ArgumentError, QuoteBase)

    def test_merge_series(self):
        merged_df = QuoteBase.merge_series([self.series1, self.series2])
        target_df = pd.concat([self.series1, self.series2])
        self.assertEqual(len(merged_df), len(target_df))
        for i in range(len(merged_df)):
            self.assertTrue(np.all(merged_df.iloc[i] == target_df.iloc[i]))

    def test_merge_empty_series(self):
        self.assertRaises(QuoteEngineEmptyQuotes, QuoteBase.merge_series, [pd.DataFrame(), pd.DataFrame()])
        self.assertRaises(QuoteEngineEmptyQuotes, QuoteBase.merge_series, [None, None])



    def test_build(self):
        qb = QuoteBase(datamanager='test')
        self.assertRaises(NotImplementedError, qb.build)

    def test_str(self):
        qb = QuoteBase(datamanager='test')
        self.assertRaises(NotImplementedError, qb.__str__)
