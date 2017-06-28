import unittest
from tmqrfeed.costs import Costs
from tmqrfeed.quotes.quote_index import QuoteIndex
from tmqrfeed.manager import DataManager
from tmqrstrategy.strategy_alpha import StrategyAlpha
from tmqrstrategy.optimizers import OptimizerBase
from tmqrfeed.position import Position
from unittest.mock import patch, MagicMock
import pandas as pd
from tmqr.errors import *
import numpy as np
from datetime import datetime


class StrategyAlphaTestCase(unittest.TestCase):
    def setUp(self):
        self.ALPHA_CONTEXT = {
            'name': 'alpha_TEST_debug',
            'context': {  # Strategy specific settings
                # These settings only applycable for alphas derived from StrategyAlpha strategy
                # StrategyAlpha - is a classic EXO/SmartEXO based alpha
                'index_name': 'US.ES_ContFutEOD',  # Name of EXO index to trade
                'costs_per_option': 3.0,
                'costs_per_contract': 1.0,
            },
            'wfo_params': {
                'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
                'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
                'oos_periods': 2,  # Number of months is OOS period
                'iis_periods': 12,
                # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
            },
            'wfo_optimizer_class': OptimizerBase,
            'wfo_optimizer_class_kwargs': {
                'nbest_count': 3,
                'nbest_fitness_method': 'max'
            },
            'wfo_opt_params': [
                ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
                ('period_fast', [1, 3, 10, 15, 20, 30])
            ],
            'wfo_members_count': 1,
            'wfo_costs_per_contract': 0.0,
            'wfo_scoring_type': 'netprofit'
        }

    def test_setup(self):
        dm = MagicMock(DataManager)()

        alpha = StrategyAlpha(dm, **self.ALPHA_CONTEXT)
        alpha.setup()

        self.assertEqual(dm.session_set.called, False)

        self.assertEqual(dm.series_primary_set.call_args[0][0], QuoteIndex)
        self.assertEqual(dm.series_primary_set.call_args[0][1], 'US.ES_ContFutEOD')
        self.assertEqual(dm.series_primary_set.call_args[1]['set_session'], True)
        self.assertEqual(dm.series_primary_set.call_args[1]['check_session'], True)

        self.assertEqual(dm.costs_set.call_args[0][0], 'US')
        self.assertEqual(type(dm.costs_set.call_args[0][1]), Costs)
        self.assertEqual(dm.costs_set.call_args[0][1].per_contract, 1)
        self.assertEqual(dm.costs_set.call_args[0][1].per_option, 3)

    def test_setup_errors_no_index(self):
        dm = MagicMock(DataManager)()

        context = self.ALPHA_CONTEXT.copy()
        del context['context']['index_name']
        alpha = StrategyAlpha(dm, **context)
        self.assertRaises(StrategyError, alpha.setup)

    def test_setup_errors_no_costs_options(self):
        dm = MagicMock(DataManager)()

        context = self.ALPHA_CONTEXT.copy()
        del context['context']['costs_per_option']
        alpha = StrategyAlpha(dm, **context)
        self.assertRaises(StrategyError, alpha.setup)

    def test_setup_errors_no_costs_contracts(self):
        dm = MagicMock(DataManager)()

        context = self.ALPHA_CONTEXT.copy()
        del context['context']['costs_per_contract']
        alpha = StrategyAlpha(dm, **context)
        self.assertRaises(StrategyError, alpha.setup)

    def test_calculate_position(self):
        dm = MagicMock(DataManager)()
        alpha = StrategyAlpha(dm, **self.ALPHA_CONTEXT)

        mock_alpha_position = MagicMock(Position)()
        alpha.position = mock_alpha_position

        mock_index_position = MagicMock(Position)()
        dm.position.return_value = mock_index_position

        mock_replicated_pos = MagicMock(Position)()
        mock_index_position.get_net_position.return_value = mock_replicated_pos

        dt = datetime(2011, 1, 1)
        exposure_rec = pd.DataFrame({"exposure": [1, 2]}, index=[dt, dt])

        self.assertEqual(None, alpha.calculate_position(dt, exposure_rec))

        self.assertEqual(1, mock_index_position.get_net_position.call_count)
        self.assertEqual(dt, mock_index_position.get_net_position.call_args[0][0])
        self.assertEqual(1, mock_alpha_position.add_net_position.call_count)
        self.assertEqual(dt, mock_alpha_position.add_net_position.call_args[0][0])
        self.assertEqual(mock_replicated_pos, mock_alpha_position.add_net_position.call_args[0][1])
        self.assertEqual(exposure_rec['exposure'].sum(), mock_alpha_position.add_net_position.call_args[1]['qty'])

    def test_calculate_position_error_no_exposure_col(self):
        dm = MagicMock(DataManager)()
        alpha = StrategyAlpha(dm, **self.ALPHA_CONTEXT)

        mock_alpha_position = MagicMock(Position)()
        alpha.position = mock_alpha_position

        mock_index_position = MagicMock(Position)()
        dm.position.return_value = mock_index_position

        mock_replicated_pos = MagicMock(Position)()
        mock_index_position.get_net_position.return_value = mock_replicated_pos

        dt = datetime(2011, 1, 1)
        exposure_rec = pd.DataFrame({"exposure2": [1, 2]}, index=[dt, dt])

        self.assertRaises(StrategyError, alpha.calculate_position, dt, exposure_rec)
