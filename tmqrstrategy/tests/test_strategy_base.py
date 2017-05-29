import unittest
from unittest.mock import MagicMock, patch
from tmqrfeed import DataManager, Position
from tmqrstrategy.strategy_base import StrategyBase
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tmqr.errors import *


class StrategyBaseTestCase(unittest.TestCase):
    def test_init(self):
        dm = MagicMock(DataManager())

        strategy = StrategyBase(dm, position='position')
        self.assertEqual('position', strategy.position)

        strategy = StrategyBase(dm)
        self.assertEqual(Position, type(strategy.position))

    def test__make_wfo_matrix_rolling_month_1(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2011-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        wfo_matrix = strategy._make_wfo_matrix()

        for i, mtx_val in enumerate(wfo_matrix):
            self.assertEqual(wfo_matrix[i]['iis_end'], wfo_matrix[i]['oos_start'])

            if i == 0:
                continue
            self.assertEqual(wfo_matrix[i]['oos_start'], wfo_matrix[i - 1]['oos_end'])
            self.assertEqual(wfo_matrix[i]['iis_end'], wfo_matrix[i - 1]['oos_end'])

    def test__make_wfo_matrix_prev_weekend(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2017-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        wfo_matrix = strategy._make_wfo_matrix()
        self.assertEqual(2, len(wfo_matrix))

        self.assertEqual(wfo_matrix[0]['iis_start'], datetime(2016, 12, 25))
        self.assertEqual(wfo_matrix[0]['iis_end'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_start'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_end'], datetime(2017, 4, 29))

        self.assertEqual(wfo_matrix[1]['iis_start'], datetime(2017, 2, 28))
        self.assertEqual(wfo_matrix[1]['iis_end'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_start'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_end'], datetime(2017, 6, 24))

    def test__make_wfo_matrix_expanding_window(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'expanding',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2017-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        wfo_matrix = strategy._make_wfo_matrix()
        self.assertEqual(2, len(wfo_matrix))

        self.assertEqual(wfo_matrix[0]['iis_start'], datetime(2017, 1, 2))  # First business date
        self.assertEqual(wfo_matrix[0]['iis_end'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_start'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_end'], datetime(2017, 4, 29))

        self.assertEqual(wfo_matrix[1]['iis_start'], datetime(2017, 1, 2))  # First business date
        self.assertEqual(wfo_matrix[1]['iis_end'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_start'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_end'], datetime(2017, 6, 24))

    def test__make_wfo_matrix_weekly(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'W',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2011-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        wfo_matrix = strategy._make_wfo_matrix()

        for i, mtx_val in enumerate(wfo_matrix):
            self.assertEqual(wfo_matrix[i]['iis_end'], wfo_matrix[i]['oos_start'])

            if i == 0:
                continue
            self.assertEqual(wfo_matrix[i]['oos_start'], wfo_matrix[i - 1]['oos_end'])
            self.assertEqual(wfo_matrix[i]['iis_end'], wfo_matrix[i - 1]['oos_end'])

            self.assertEqual(5, wfo_matrix[i]['iis_end'].weekday())
            self.assertEqual(5, wfo_matrix[i]['oos_end'].weekday())
            self.assertEqual(14, relativedelta(wfo_matrix[i]['oos_end'], wfo_matrix[i]['iis_end']).days)

        self.assertGreater(wfo_matrix[-1]['oos_end'], datetime(2017, 6, 23))

    def test__make_wfo_matrix_bad_period_type(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'd',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2011-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        self.assertRaises(ArgumentError, strategy._make_wfo_matrix)

    def test__make_wfo_matrix_bad_oos_period(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 5,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window or minimal expanding window length
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2011-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params)

        self.assertRaises(ArgumentError, strategy._make_wfo_matrix)


if __name__ == '__main__':
    unittest.main()
