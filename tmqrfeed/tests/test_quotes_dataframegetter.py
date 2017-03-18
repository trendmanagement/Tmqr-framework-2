import os
import unittest

import numpy as np
import pandas as pd

from tmqrfeed.quotes.dataframegetter import DataFrameGetter


class DataFrameGetterTestCase(unittest.TestCase):
    def test_init_with_getitem(self):
        print(os.getcwd())
        df = pd.read_csv(os.path.abspath(os.path.join(__file__, '../', 'fut_series.csv')), parse_dates=True,
                         index_col=0)
        dfg = DataFrameGetter(df)

        self.assertTrue(type(dfg.data) == np.ndarray)
        self.assertTrue(type(dfg.index) == pd.DatetimeIndex)
        self.assertTrue(type(dfg.cols) == dict)
        self.assertEqual(5, len(dfg.cols))
        self.assertTrue('o' in dfg.cols)
        self.assertTrue('h' in dfg.cols)
        self.assertTrue('l' in dfg.cols)
        self.assertTrue('c' in dfg.cols)
        self.assertTrue('v' in dfg.cols)

        self.assertEqual(123248.41, np.sum(dfg['o']))
        self.assertEqual(123284.35, np.sum(dfg['h']))
        self.assertEqual(123218.1, np.sum(dfg['l']))
        self.assertEqual(123251.24, np.sum(dfg['c']))
        self.assertEqual(184797, np.sum(dfg['v']))
