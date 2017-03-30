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

    def test_merge_positions(self):
        position1 = [
            # Tuple of: date, asset, decision_px, exec_px, qty
            (datetime(2013, 1, 1), "A1", 100, 101, 1),
            (datetime(2013, 1, 2), "A1", 110, 102, 1),
        ]

        position2 = [
            # Tuple of: date, asset, decision_px, exec_px, qty
            (datetime(2013, 1, 2), "A2", 200, 201, 1),
            (datetime(2013, 1, 3), "A2", 210, 212, 1),
        ]

        merged_pos = QuoteBase.merge_positions([position1, position2])
        self.assertEqual(dict, type(merged_pos))
        self.assertEqual(3, len(merged_pos))

        d = merged_pos[datetime(2013, 1, 1)]
        self.assertEqual(dict, type(d))
        self.assertEqual(1, len(d))
        dtckr = d['A1']
        self.assertEqual(dtckr[0], 100)
        self.assertEqual(dtckr[1], 101)
        self.assertEqual(dtckr[2], 1)

        d = merged_pos[datetime(2013, 1, 2)]
        self.assertEqual(dict, type(d))
        self.assertEqual(2, len(d))
        dtckr = d['A1']
        self.assertEqual(dtckr[0], 110)
        self.assertEqual(dtckr[1], 102)
        self.assertEqual(dtckr[2], 0)

        dtckr = d['A2']
        self.assertEqual(dtckr[0], 200)
        self.assertEqual(dtckr[1], 201)
        self.assertEqual(dtckr[2], 1)

        d = merged_pos[datetime(2013, 1, 3)]
        self.assertEqual(dict, type(d))
        self.assertEqual(1, len(d))
        dtckr = d['A2']
        self.assertEqual(dtckr[0], 210)
        self.assertEqual(dtckr[1], 212)
        self.assertEqual(dtckr[2], 1)



    def test_merge_positions2(self):
        position1 = [
            # Tuple of: date, asset, decision_px, exec_px, qty
            (datetime(2013, 1, 2), "A1", 100, 101, 1),
            (datetime(2013, 1, 2), "A3", 110, 102, 1),
        ]

        position2 = [
            # Tuple of: date, asset, decision_px, exec_px, qty
            (datetime(2013, 1, 2), "A2", 200, 201, 1),
            (datetime(2013, 1, 3), "A2", 210, 212, 1),
        ]

        merged_pos = QuoteBase.merge_positions([position1, position2])
        self.assertEqual(dict, type(merged_pos))
        self.assertEqual(2, len(merged_pos))

        d = merged_pos[datetime(2013, 1, 2)]
        self.assertEqual(dict, type(d))
        self.assertEqual(3, len(d))
        dtckr = d['A1']
        self.assertEqual(dtckr[0], 100)
        self.assertEqual(dtckr[1], 101)
        self.assertEqual(dtckr[2], 0)

        dtckr = d['A3']
        self.assertEqual(dtckr[0], 110)
        self.assertEqual(dtckr[1], 102)
        self.assertEqual(dtckr[2], 0)

        dtckr = d['A2']
        self.assertEqual(dtckr[0], 200)
        self.assertEqual(dtckr[1], 201)
        self.assertEqual(dtckr[2], 1)

        d = merged_pos[datetime(2013, 1, 3)]
        self.assertEqual(dict, type(d))
        self.assertEqual(1, len(d))
        dtckr = d['A2']
        self.assertEqual(dtckr[0], 210)
        self.assertEqual(dtckr[1], 212)
        self.assertEqual(dtckr[2], 1)



    def test_merge_positions_none(self):
        merged_pos = QuoteBase.merge_positions([None, None])
        self.assertEqual(merged_pos, {})

    def test_build(self):
        qb = QuoteBase(datamanager='test')
        self.assertRaises(NotImplementedError, qb.build)
