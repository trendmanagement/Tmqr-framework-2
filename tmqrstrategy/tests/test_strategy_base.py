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
        pos = Position(dm)

        self.assertRaises(StrategyError, StrategyBase, dm, position=pos)


        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position=Position(dm), wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

        # Wrong position type

        self.assertRaises(StrategyError, StrategyBase, dm, position='wrong_pos_type', wfo_params=wfo_params,
                          wfo_optimizer_class=MagicMock())

        self.assertEqual(pos, strategy.position)

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')
        self.assertEqual(Position, type(strategy.position))

    def test_strategy_name(self):
        dm = MagicMock(DataManager())
        pos = Position(dm)

        self.assertRaises(StrategyError, StrategyBase, dm, position=pos)

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position=Position(dm), wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')
        self.assertEqual('unittest_strat', strategy.strategy_name)

        strategy = StrategyBase(dm, position=Position(dm), wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='MyStrategy')
        self.assertEqual('MyStrategy', strategy.strategy_name)



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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, position=pos, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        self.opt_cnt = 0

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
                                                        wfo_optimizer_class=OptimizerBase, name='unittest_strat')
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

        self.assertRaises(StrategyError, StrategyBase, dm, position=Position(dm), name='unittest_strat')

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position=Position(dm), wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

        self.assertRaises(StrategyError, StrategyBase, dm, position=Position(dm), wfo_params=wfo_params,
                          name='unittest_strat')
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

        self.assertRaises(StrategyError, StrategyBase, dm, position=Position(dm), name='unittest_strat')

        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, position=Position(dm), wfo_params=wfo_params, wfo_optimizer_class=MagicMock(),
                                name='unittest_strat')

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

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            strategy.process_position(exp_df_list_valid, datetime(2011, 1, 5), datetime(2011, 1, 20))

            self.assertEqual(1, mock_calculate_position.call_count)

            self.assertEqual(datetime(2011, 1, 6), mock_calculate_position.call_args[0][0])
            self.assertEqual(pd.DataFrame, type(mock_calculate_position.call_args[0][1]))

            pos_df = mock_calculate_position.call_args[0][1]

            self.assertEqual(2, len(pos_df))
            self.assertEqual(3, pos_df['exposure'].sum())
            self.assertEqual(2, pos_df['some_value'].sum())

            self.assertEqual(1, len(strategy.exposure_series))
            self.assertEqual(3, strategy.exposure_series['exposure'][datetime(2011, 1, 6)])
            self.assertEqual(2, strategy.exposure_series['some_value'][datetime(2011, 1, 6)])

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

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            with patch('tmqrfeed.position.Position.keep_previous_position') as mock_keep_previous_position:
                strategy.position._position[datetime(2011, 1, 6)] = {}

                strategy.process_position(exp_df_list_valid, datetime(2011, 1, 5), datetime(2011, 1, 20))

                self.assertEqual(0, mock_calculate_position.call_count)
                self.assertEqual(0, mock_keep_previous_position.call_count)

    def test_process_position_valid_empty_alphas_list(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 8))

        dm.quotes.return_value = pd.Series(np.zeros(len(date_idx)), index=date_idx)

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            strategy.position._position[datetime(2011, 1, 6)] = {}

            strategy.process_position([], datetime(2011, 1, 5), datetime(2011, 1, 20))

            self.assertEqual(0, mock_calculate_position.call_count)

            self.assertEqual({}, strategy.position._position[datetime(2011, 1, 6)])
            self.assertEqual({}, strategy.position._position[datetime(2011, 1, 7)])
            self.assertEqual({}, strategy.position._position[datetime(2011, 1, 8)])

    def test_process_position_skip_if_dt_greater_oos_end(self):
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

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')

        with patch('tmqrstrategy.strategy_base.StrategyBase.calculate_position') as mock_calculate_position:
            with patch('tmqrfeed.position.Position.keep_previous_position') as mock_keep_previous_position:
                strategy.position._position[datetime(2011, 1, 6)] = {}

                strategy.process_position(exp_df_list_valid, datetime(2011, 1, 5), datetime(2011, 1, 20))

                self.assertEqual(0, mock_calculate_position.call_count)
                self.assertEqual(0, mock_keep_previous_position.call_count)

    def test_exposure(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))
        ohlc = pd.DataFrame({'c': np.random.random(len(date_idx))}, index=date_idx)

        dm.quotes.return_value = ohlc

        with patch('tmqrstrategy.strategy_base.exposure') as mock_exposure:
            strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')
            entry_rule = pd.Series(np.random.random(len(date_idx)), index=date_idx)
            exit_rule = pd.Series(np.random.random(len(date_idx)), index=date_idx)

            exposure_return = pd.Series(np.random.random(len(date_idx)), index=date_idx)
            mock_exposure.return_value = exposure_return

            exposure_ret = strategy.exposure(entry_rule, exit_rule, 1, -10, 2)

            self.assertTrue(np.all(ohlc.c.values == mock_exposure.call_args[0][0]))
            self.assertTrue(np.all(entry_rule.values == mock_exposure.call_args[0][1]))
            self.assertTrue(np.all(exit_rule.values == mock_exposure.call_args[0][2]))
            self.assertEqual(1, mock_exposure.call_args[0][3])

            # Default args
            self.assertEqual(2, mock_exposure.call_args[1]['nbar_stop'])
            self.assertEqual(-10, mock_exposure.call_args[1]['size_exposure'])

            self.assertEqual(pd.DataFrame, type(exposure_ret))
            self.assertEqual(True, 'exposure' in exposure_ret)
            self.assertEqual(True, np.all(ohlc.index == exposure_ret.index))

            # Default args checks
            exposure_ret = strategy.exposure(entry_rule, exit_rule, 1)
            self.assertEqual(0, mock_exposure.call_args[1]['nbar_stop'])
            self.assertEqual(None, mock_exposure.call_args[1]['size_exposure'])

    def test_exposure_error_checks(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))
        date_idx2 = pd.date_range(datetime(2011, 1, 2), datetime(2011, 1, 7))
        date_idx3 = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 5))

        ohlc = pd.DataFrame({'c': np.random.random(len(date_idx))}, index=date_idx)
        dm.quotes.return_value = ohlc

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')
        entry_rule = pd.Series(np.random.random_integers(0, 1, len(date_idx)), index=date_idx, dtype=np.uint8)
        exit_rule = pd.Series(np.random.random_integers(0, 1, len(date_idx)), index=date_idx, dtype=np.uint8)
        strategy.exposure(entry_rule, exit_rule, 1)

        # Check different entry_rule index
        with patch('tmqrstrategy.strategy_base.exposure') as mock_exposure:
            exposure_return = pd.Series(np.random.random(len(date_idx)), index=date_idx)
            mock_exposure.return_value = exposure_return

            # Bad entry index length
            wrong_series = pd.Series(np.zeros(len(date_idx3)), index=date_idx3)
            self.assertRaises(StrategyError, strategy.exposure, wrong_series, exit_rule, 1)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, wrong_series, 1)

            # Wrong series index
            wrong_series = pd.Series(np.zeros(len(date_idx3)), index=date_idx3)
            self.assertRaises(StrategyError, strategy.exposure, wrong_series, exit_rule, 1)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, wrong_series, 1)

            # Bad direction checks
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 0)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 2)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, -2)

            # Negative nbar stop
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 1, nbar_stop=-2)

            # fixed zero position size
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 1, position_size=0)

            # Non pandas series positions size
            wrong_series = pd.Series(np.zeros(len(date_idx2)), index=date_idx2)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 1, position_size=wrong_series)

            wrong_series = pd.Series(np.zeros(len(date_idx3)), index=date_idx3)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 1, position_size=wrong_series)
            self.assertRaises(StrategyError, strategy.exposure, entry_rule, exit_rule, 1,
                              position_size=np.zeros(len(date_idx)))

    def test_calculate(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')
        self.assertRaises(NotImplementedError, strategy.calculate)

    def test_calculate_position(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), name='unittest_strat')
        self.assertRaises(NotImplementedError, strategy.calculate_position, None, None)

    def test_score_netprofit(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))
        ohlc = pd.DataFrame({'c': np.random.random(len(date_idx))}, index=date_idx)
        dm.quotes.return_value = ohlc

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), wfo_costs_per_contract=3.0,
                                wfo_scoring_type='netprofit', name='unittest_strat')
        exposure_df = pd.DataFrame({'exposure': pd.Series(np.random.random(len(date_idx)), index=date_idx)})

        with patch('tmqrstrategy.strategy_base.score_netprofit') as mock_score_netprofit:
            strategy.score(exposure_df)
            self.assertEqual(True, mock_score_netprofit.called)
            self.assertTrue(np.all(ohlc['c'].values == mock_score_netprofit.call_args[0][0]))
            self.assertTrue(np.all(exposure_df['exposure'].values == mock_score_netprofit.call_args[0][1]))
            self.assertEqual(3, mock_score_netprofit.call_args[1]['costs'])

    def test_score_modsharpe(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))
        ohlc = pd.DataFrame({'c': np.random.random(len(date_idx))}, index=date_idx)
        dm.quotes.return_value = ohlc

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), wfo_costs_per_contract=3.0,
                                wfo_scoring_type='modsharpe', name='unittest_strat')
        exposure_df = pd.DataFrame({'exposure': pd.Series(np.random.random(len(date_idx)), index=date_idx)})

        with patch('tmqrstrategy.strategy_base.score_modsharpe') as mock_score_modsharpe:
            strategy.score(exposure_df)
            self.assertEqual(True, mock_score_modsharpe.called)
            self.assertTrue(np.all(ohlc['c'].values == mock_score_modsharpe.call_args[0][0]))
            self.assertTrue(np.all(exposure_df['exposure'].values == mock_score_modsharpe.call_args[0][1]))
            self.assertEqual(3, mock_score_modsharpe.call_args[1]['costs'])

    def test_score_unknown_error(self):
        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))
        ohlc = pd.DataFrame({'c': np.random.random(len(date_idx))}, index=date_idx)
        dm.quotes.return_value = ohlc

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), costs_per_contract=3.0,
                                wfo_scoring_type='unknown_scoring', name='unittest_strat')
        exposure_df = pd.DataFrame({'exposure': pd.Series(np.random.random(len(date_idx)), index=date_idx)})

        self.assertRaises(StrategyError, strategy.score, exposure_df)

    def test_pick(self):

        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), wfo_costs_per_contract=3.0,
                                wfo_members_count=5, name='unittest_strat')

        best_list_random = np.random.random(10)

        self.assertEqual(True, np.all(best_list_random[:5] == strategy.pick(best_list_random)))

    def test__exposure_update(self):

        dm = MagicMock(DataManager)()
        wfo_params = {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        }
        date_idx = pd.date_range(datetime(2011, 1, 1), datetime(2011, 1, 6))

        exposure1 = pd.DataFrame({
            'exposure': [1, 2, 3, 4, 5, 6],
            'exposure2': [11, 12, 13, 14, 15, 16],
        }, index=date_idx)

        exposure2 = pd.DataFrame({
            'exposure': [1, 1, 1, 1, 1, 1],
            'exposure2': [2, 2, 2, 2, 2, 2],
        }, index=date_idx)

        def ser_exposure(idx):
            exp_list_df = []
            for exp in [exposure1, exposure2]:
                exp_list_df.append(exp.loc[date_idx[idx]])

            return pd.DataFrame(exp_list_df)

        strategy = StrategyBase(dm, wfo_params=wfo_params, wfo_optimizer_class=MagicMock(), wfo_costs_per_contract=3.0,
                                wfo_members_count=5, name='unittest_strat')

        strategy._exposure_update(date_idx[0], ser_exposure(0))

        self.assertEqual(list(strategy.exposure_series.columns), ['exposure', 'exposure2'])
        self.assertEqual(1, len(strategy.exposure_series))
        self.assertEqual(strategy.exposure_series['exposure'][date_idx[0]], 2)
        self.assertEqual(strategy.exposure_series['exposure2'][date_idx[0]], 13)

        strategy._exposure_update(date_idx[0], ser_exposure(0))
        self.assertEqual(list(strategy.exposure_series.columns), ['exposure', 'exposure2'])
        self.assertEqual(1, len(strategy.exposure_series))
        self.assertEqual(strategy.exposure_series['exposure'][date_idx[0]], 2)
        self.assertEqual(strategy.exposure_series['exposure2'][date_idx[0]], 13)

        strategy._exposure_update(date_idx[1], ser_exposure(1))
        self.assertEqual(list(strategy.exposure_series.columns), ['exposure', 'exposure2'])
        self.assertEqual(2, len(strategy.exposure_series))
        self.assertEqual(strategy.exposure_series['exposure'][date_idx[0]], 2)
        self.assertEqual(strategy.exposure_series['exposure2'][date_idx[0]], 13)

        self.assertEqual(strategy.exposure_series['exposure'][date_idx[1]], 3)
        self.assertEqual(strategy.exposure_series['exposure2'][date_idx[1]], 14)

        strategy._exposure_update(date_idx[1], None)
        self.assertEqual(strategy.exposure_series['exposure'][date_idx[1]], 0.0)
        self.assertEqual(strategy.exposure_series['exposure2'][date_idx[1]], 0.0)
