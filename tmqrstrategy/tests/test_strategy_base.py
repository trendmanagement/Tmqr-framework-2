import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from tmqrfeed import DataManager, Position
from tmqrstrategy.strategy_base import *
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tmqr.errors import *
from tmqrstrategy.optimizers import OptimizerBase


class StrategyBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.opt_cnt = 0

    def test_init(self):
        dm = MagicMock(DataManager())

        self.assertRaises(StrategyError, StrategyBase, dm, position='position')

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position='position', wfo_params=wfo_params, optimizer_class=MagicMock())

        self.assertEqual('position', strategy.position)

        strategy = StrategyBase(dm, wfo_params=wfo_params, optimizer_class=MagicMock())
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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

        wfo_matrix = strategy._make_wfo_matrix()
        self.assertEqual(3, len(wfo_matrix))

        self.assertEqual(wfo_matrix[0]['iis_start'], datetime(2016, 12, 25))
        self.assertEqual(wfo_matrix[0]['iis_end'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_start'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_end'], datetime(2017, 4, 29))

        self.assertEqual(wfo_matrix[1]['iis_start'], datetime(2017, 2, 28))
        self.assertEqual(wfo_matrix[1]['iis_end'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_start'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_end'], datetime(2017, 6, 24))

        self.assertEqual(wfo_matrix[2]['iis_start'], datetime(2017, 4, 24))
        self.assertEqual(wfo_matrix[2]['iis_end'], datetime(2017, 6, 24))
        self.assertEqual(wfo_matrix[2]['oos_start'], datetime(2017, 6, 24))
        self.assertEqual(wfo_matrix[2]['oos_end'], datetime(2017, 8, 26))

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

        wfo_matrix = strategy._make_wfo_matrix()
        self.assertEqual(3, len(wfo_matrix))

        self.assertEqual(wfo_matrix[0]['iis_start'], datetime(2017, 1, 2))  # First business date
        self.assertEqual(wfo_matrix[0]['iis_end'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_start'], datetime(2017, 2, 25))
        self.assertEqual(wfo_matrix[0]['oos_end'], datetime(2017, 4, 29))

        self.assertEqual(wfo_matrix[1]['iis_start'], datetime(2017, 1, 2))  # First business date
        self.assertEqual(wfo_matrix[1]['iis_end'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_start'], datetime(2017, 4, 29))
        self.assertEqual(wfo_matrix[1]['oos_end'], datetime(2017, 6, 24))

        self.assertEqual(wfo_matrix[2]['iis_start'], datetime(2017, 1, 2))
        self.assertEqual(wfo_matrix[2]['iis_end'], datetime(2017, 6, 24))
        self.assertEqual(wfo_matrix[2]['oos_start'], datetime(2017, 6, 24))
        self.assertEqual(wfo_matrix[2]['oos_end'], datetime(2017, 8, 26))

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, optimizer_class=MagicMock())

        self.assertRaises(ArgumentError, strategy._make_wfo_matrix)



    def test__get_next_wfo_action_new_run(self):
        quotes_index = [datetime(2011, 3, 1), datetime(2011, 6, 1)]
        position = MagicMock(Position(None))

        type(position).last_date = PropertyMock()

        wfo_matrix = [
            {
                'iis_start': datetime(2011, 1, 1),
                'iis_end': datetime(2011, 2, 1),
                'oos_start': datetime(2011, 2, 1),
                'oos_end': datetime(2011, 3, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 3, 1),
                'oos_start': datetime(2011, 3, 1),
                'oos_end': datetime(2011, 4, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 4, 1),
                'oos_start': datetime(2011, 4, 1),
                'oos_end': datetime(2011, 5, 1),
            },
        ]

        self.assertRaises(WalkForwardOptimizationError, StrategyBase.get_next_wfo_action, None, wfo_matrix[0], [])

        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(None, wfo_matrix[0], quotes_index))
        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(None, wfo_matrix[1], quotes_index))
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(None, wfo_matrix[2], quotes_index))

    def test__get_next_wfo_action_continue_backtesting(self):
        quotes_index = [datetime(2010, 1, 1), datetime(2011, 5, 21)]
        position = MagicMock(Position(None))

        type(position).last_date = PropertyMock()

        wfo_matrix = [
            {
                'iis_start': datetime(2011, 1, 1),
                'iis_end': datetime(2011, 2, 1),
                'oos_start': datetime(2011, 2, 1),
                'oos_end': datetime(2011, 3, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 3, 1),
                'oos_start': datetime(2011, 3, 1),
                'oos_end': datetime(2011, 4, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 4, 1),
                'oos_start': datetime(2011, 4, 1),
                'oos_end': datetime(2011, 5, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 5, 1),
                'oos_start': datetime(2011, 5, 1),
                'oos_end': datetime(2011, 6, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 6, 1),
                'oos_start': datetime(2011, 6, 1),
                'oos_end': datetime(2011, 7, 1),
            },
        ]

        wfo_last = None
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[0], quotes_index))

        wfo_last = wfo_matrix[0]

        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[0], quotes_index))
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[2], quotes_index))

        wfo_last = wfo_matrix[2]
        self.assertEqual(WFO_ACTION_OPTIMIZE,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[3], quotes_index))

        self.assertEqual(WFO_ACTION_BREAK,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[4], quotes_index))

    def test__get_next_wfo_action_continue_wfo_calculation(self):
        quotes_index = [datetime(2010, 1, 1), datetime(2011, 5, 21)]
        position = MagicMock(Position(None))

        type(position).last_date = PropertyMock()

        wfo_matrix = [
            {
                'iis_start': datetime(2011, 1, 1),
                'iis_end': datetime(2011, 2, 1),
                'oos_start': datetime(2011, 2, 1),
                'oos_end': datetime(2011, 3, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 3, 1),
                'oos_start': datetime(2011, 3, 1),
                'oos_end': datetime(2011, 4, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 4, 1),
                'oos_start': datetime(2011, 4, 1),
                'oos_end': datetime(2011, 5, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 5, 1),
                'oos_start': datetime(2011, 5, 1),
                'oos_end': datetime(2011, 6, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 6, 1),
                'oos_start': datetime(2011, 6, 1),
                'oos_end': datetime(2011, 7, 1),
            },
        ]

        wfo_last = None
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[0], quotes_index))

        self.assertEqual(WFO_ACTION_RUN,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_OPTIMIZE,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[2], quotes_index))

    def test__get_next_wfo_action_online_only_run(self):
        quotes_index = [datetime(2010, 1, 1), datetime(2011, 3, 21)]
        position = MagicMock(Position(None))

        type(position).last_date = PropertyMock()

        wfo_matrix = [
            {
                'iis_start': datetime(2011, 1, 1),
                'iis_end': datetime(2011, 2, 1),
                'oos_start': datetime(2011, 2, 1),
                'oos_end': datetime(2011, 3, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 3, 1),
                'oos_start': datetime(2011, 3, 1),
                'oos_end': datetime(2011, 4, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 4, 1),
                'oos_start': datetime(2011, 4, 1),
                'oos_end': datetime(2011, 5, 1),
            },
        ]

        wfo_last = None
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[0], quotes_index))

        self.assertEqual(WFO_ACTION_RUN,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_BREAK,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[2], quotes_index))

    def test__get_next_wfo_action_online_optimize_if_date_now(self):
        quotes_index = [datetime(2010, 1, 1), datetime(2011, 3, 31)]
        position = MagicMock(Position(None))

        type(position).last_date = PropertyMock()

        wfo_matrix = [
            {
                'iis_start': datetime(2011, 1, 1),
                'iis_end': datetime(2011, 2, 1),
                'oos_start': datetime(2011, 2, 1),
                'oos_end': datetime(2011, 3, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 3, 1),
                'oos_start': datetime(2011, 3, 1),
                'oos_end': datetime(2011, 4, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 4, 1),
                'oos_start': datetime(2011, 4, 1),
                'oos_end': datetime(2011, 5, 1),
            },
            {
                'iis_start': datetime(2011, 2, 1),
                'iis_end': datetime(2011, 5, 1),
                'oos_start': datetime(2011, 5, 1),
                'oos_end': datetime(2011, 6, 1),
            },
            {
                'iis_start': datetime(2011, 3, 1),
                'iis_end': datetime(2011, 6, 1),
                'oos_start': datetime(2011, 6, 1),
                'oos_end': datetime(2011, 7, 1),
            },
        ]

        wfo_last = None
        self.assertEqual(WFO_ACTION_OPTIMIZE, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        self.assertEqual(WFO_ACTION_SKIP, StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[0], quotes_index))

        self.assertEqual(WFO_ACTION_RUN,
                         StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[1], quotes_index))

        wfo_last = wfo_matrix[1]
        with patch('tmqrstrategy.strategy_base.StrategyBase.date_now') as mock_date_now:
            mock_date_now.return_value = datetime(2011, 4, 1).date()
            self.assertEqual(WFO_ACTION_OPTIMIZE,
                             StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[2], quotes_index))

            wfo_last = wfo_matrix[2]
            self.assertEqual(WFO_ACTION_BREAK,
                             StrategyBase.get_next_wfo_action(wfo_last, wfo_matrix[3], quotes_index))

    def optimized_params_sideeffect(self):
        self.opt_cnt += 1
        return [[self.opt_cnt]]

    def test_run_wfo_opt(self):
        dm = MagicMock(DataManager())

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 1,  # Number of months is OOS period
            'iis_periods': 1,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        pos = MagicMock(Position(dm))

        idx = pd.bdate_range('2017-01-01', '2017-06-23')

        df = pd.DataFrame({'close': np.zeros(len(idx))}, index=idx)

        dm.quotes.return_value = df

        opt_cnt = 0

        def calculate_side_effect(*args):
            return len(args), args[0]

        with patch('tmqrstrategy.strategy_base.StrategyBase.setup') as mock_setup:
            with patch('tmqrstrategy.optimizers.OptimizerBase.optimize') as mock_optimizer:
                with patch('tmqrstrategy.strategy_base.StrategyBase.calculate') as mock_strategy_calculate:
                    with patch(
                            'tmqrstrategy.strategy_base.StrategyBase.process_position') as mock_strategy_process_position:
                        with patch('tmqrfeed.DataManager.quotes_range_set') as mock_dm_quotes_range_set:
                            with patch(
                                    'tmqrstrategy.optimizers.OptimizerBase._check_params_integrity') as mock_optimizer_integrity:
                                mock_optimizer.side_effect = self.optimized_params_sideeffect
                                mock_strategy_calculate.side_effect = calculate_side_effect

                                strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params,
                                                        optimizer_class=OptimizerBase)
                                strategy.run()

                                self.assertEqual([[5]], strategy.wfo_selected_alphas)
                                self.assertEqual(5, len(mock_strategy_process_position.call_args_list))

                                wfo_matrix = strategy._make_wfo_matrix()
                                for i in range(5):
                                    dm_quotes_range_base_i = i * 3

                                    # First call - set IIS quotes data range
                                    self.assertEqual(
                                        dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 0][0][0],
                                        wfo_matrix[i]['iis_start']
                                        )
                                    self.assertEqual(
                                        dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 0][0][1],
                                        wfo_matrix[i]['iis_end']
                                        )

                                    # Second call - set OOS quotes data range
                                    self.assertEqual(
                                        dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 1][0][0],
                                        wfo_matrix[i]['iis_start']
                                        )
                                    self.assertEqual(
                                        dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 1][0][1],
                                        wfo_matrix[i]['oos_end']
                                        )

                                    # Third call - reset quotes range
                                    self.assertEqual(dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 2][0],
                                                     ()
                                                     )
                                    self.assertEqual(dm.quotes_range_set.call_args_list[dm_quotes_range_base_i + 2][0],
                                                     ()
                                                     )

                                    # Process position called with calculate results and OOS period
                                    self.assertEqual([(1, i + 1)],
                                                     mock_strategy_process_position.call_args_list[i][0][0])
                                    self.assertEqual(wfo_matrix[i]['oos_start'],
                                                     mock_strategy_process_position.call_args_list[i][0][1])
                                    self.assertEqual(wfo_matrix[i]['oos_end'],
                                                     mock_strategy_process_position.call_args_list[i][0][2])

                                #
                                # Running the strategy once again
                                mock_strategy_process_position.reset_mock()
                                dm.quotes_range_set.reset_mock()
                                mock_optimizer.reset_mock()
                                mock_strategy_calculate.reset_mock()
                                self.opt_cnt = 0
                                strategy.run()

                                self.assertEqual(False, mock_optimizer.called)
                                self.assertEqual(True, mock_strategy_calculate.called)
                                self.assertEqual(2, len(dm.quotes_range_set.call_args_list))

                                # First call - set IIS quotes data range
                                self.assertEqual(dm.quotes_range_set.call_args_list[0][0][0],
                                                 wfo_matrix[4]['iis_start']
                                                 )
                                self.assertEqual(dm.quotes_range_set.call_args_list[0][0][1],
                                                 wfo_matrix[4]['oos_end']
                                                 )

                                # Second call - reset quotes range
                                self.assertEqual(dm.quotes_range_set.call_args_list[1][0],
                                                 ()
                                                 )
                                self.assertEqual(dm.quotes_range_set.call_args_list[1][0],
                                                 ()
                                                 )

                                # Process position called with calculate results and OOS period
                                self.assertEqual(1, mock_strategy_process_position.call_count)

                                self.assertEqual([(1, 5)], mock_strategy_process_position.call_args_list[0][0][0])
                                self.assertEqual(wfo_matrix[4]['oos_start'],
                                                 mock_strategy_process_position.call_args_list[0][0][1])
                                self.assertEqual(wfo_matrix[4]['oos_end'],
                                                 mock_strategy_process_position.call_args_list[0][0][2])

    def test_run_walkforward_error_no_quotes(self):
        dm = DataManager()

        self.assertRaises(StrategyError, StrategyBase, dm, position='position')

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position='position', wfo_params=wfo_params, optimizer_class=MagicMock())

        self.assertRaises(StrategyError, StrategyBase, dm, position='position', wfo_params=wfo_params)
        self.assertRaises(StrategyError, strategy.run)

    def test_process_position_exposure_df_integrity_checks(self):

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2012, 1, 10))

        exp_df = pd.DataFrame({'exposure': np.ones(len(date_idx)), 'some_value': np.ones(len(date_idx))},
                              index=date_idx)

        exp_df2 = pd.DataFrame({'exposure': np.ones(len(date_idx)) * 2, 'some_value': np.ones(len(date_idx))},
                               index=date_idx)

        exp_df3 = pd.DataFrame({'exposure': np.ones(len(date_idx)) * 3, 'some_value': np.ones(len(date_idx))},
                               index=date_idx)

        exp_df_list = [exp_df, exp_df2, exp_df3]

        dm = MagicMock(DataManager)()

        self.assertRaises(StrategyError, StrategyBase, dm, position='position')

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position='position', wfo_params=wfo_params, optimizer_class=MagicMock())

        #
        # Check list members must be pandas.DataFrames
        #
        self.assertRaises(ArgumentError, strategy.process_position, [None], date_idx[0], date_idx[-1])
        #
        # Check list members must have equal lengths
        #
        date_idx2 = pd.date_range(datetime(2011, 1, 1), datetime(2012, 1, 12))
        exp_df_diff_length = pd.DataFrame({
            'exposure': np.ones(len(date_idx2)),
            'some_value': np.ones(len(date_idx2))}, index=date_idx2)
        self.assertRaises(ArgumentError, strategy.process_position, [exp_df, exp_df_diff_length], date_idx[0],
                          date_idx[-1])

        #
        # Check list members must have equal index datapoints
        #
        date_idx2 = pd.date_range(datetime(2011, 1, 2), datetime(2012, 1, 11))
        exp_df_diff_idx = pd.DataFrame({
            'exposure': np.ones(len(date_idx2)),
            'some_value': np.ones(len(date_idx2))}, index=date_idx2)

        self.assertRaises(ArgumentError, strategy.process_position, [exp_df, exp_df_diff_idx], date_idx[0],
                          date_idx[-1])

        #
        # Check list members must have equal index datapoints
        #
        exp_df_col_names = pd.DataFrame({
            'exposure': np.ones(len(date_idx)),
            'some_value2': np.ones(len(date_idx))}, index=date_idx)

        self.assertRaises(ArgumentError, strategy.process_position, [exp_df, exp_df_col_names], date_idx[0],
                          date_idx[-1])

    def test_process_position_valid_new_position(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))

        exp_df = pd.DataFrame({'exposure': np.ones(len(date_idx)), 'some_value': np.ones(len(date_idx))},
                              index=date_idx)

        exp_df2 = pd.DataFrame({'exposure': np.ones(len(date_idx)) * 2, 'some_value': np.ones(len(date_idx))},
                               index=date_idx)

        exp_df_list_valid = [exp_df, exp_df2]

        strategy = StrategyBase(dm, wfo_params=wfo_params, optimizer_class=MagicMock())

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            with patch('tmqrfeed.position.Position.keep_previous_position') as mock_keep_previous_position:
                strategy.process_position(exp_df_list_valid, datetime(2011, 1, 5), datetime(2011, 1, 20))

                self.assertEqual(1, mock_calculate_position.call_count)
                # Undecided
                # self.assertEqual(1, mock_keep_previous_position.call_count)
                # self.assertEqual(datetime(2011, 1, 6), mock_keep_previous_position.call_args[0][0])

                self.assertEqual(datetime(2011, 1, 6), mock_calculate_position.call_args[0][0])
                self.assertEqual(pd.DataFrame, type(mock_calculate_position.call_args[0][1]))

                pos_df = mock_calculate_position.call_args[0][1]

                self.assertEqual(2, len(pos_df))
                self.assertEqual(3, pos_df['exposure'].sum())
                self.assertEqual(2, pos_df['some_value'].sum())

    def test_process_position_valid_existing_position(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))

        exp_df = pd.DataFrame({'exposure': np.ones(len(date_idx)), 'some_value': np.ones(len(date_idx))},
                              index=date_idx)

        exp_df2 = pd.DataFrame({'exposure': np.ones(len(date_idx)) * 2, 'some_value': np.ones(len(date_idx))},
                               index=date_idx)

        exp_df_list_valid = [exp_df, exp_df2]

        strategy = StrategyBase(dm, wfo_params=wfo_params, optimizer_class=MagicMock())

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            with patch('tmqrfeed.position.Position.keep_previous_position') as mock_keep_previous_position:
                strategy.position._position[datetime(2011, 1, 6)] = {}

                strategy.process_position(exp_df_list_valid, datetime(2011, 1, 5), datetime(2011, 1, 20))

                self.assertEqual(0, mock_calculate_position.call_count)
                self.assertEqual(0, mock_keep_previous_position.call_count)
