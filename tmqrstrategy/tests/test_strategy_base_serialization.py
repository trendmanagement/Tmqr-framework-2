import unittest
from datetime import datetime
from unittest.mock import MagicMock

from tmqrstrategy.optimizers import OptimizerBase
from tmqrstrategy.strategy_base import *
from tmqrstrategy.tests.debug_alpha_prototype import AlphaGeneric


class AlphaAnother(StrategyBase):
    pass


class StrategyBaseTestCase(unittest.TestCase):
    def test_serialize(self):
        dm = MagicMock(DataManager)()
        ALPHA_CONTEXT = {
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
            'wfo_costs_per_contract': 1.0,
            'wfo_scoring_type': 'netprofit'
        }

        strategy = StrategyBase(dm, **ALPHA_CONTEXT)

        ser = strategy.serialize()

        self.assertEqual(ser['wfo_params'], ALPHA_CONTEXT['wfo_params'])
        self.assertEqual(ser['wfo_last_period'], None)
        self.assertEqual(ser['wfo_selected_alphas'], [])
        self.assertEqual(ser['wfo_opt_params'], ALPHA_CONTEXT['wfo_opt_params'])
        self.assertEqual(ser['wfo_scoring_type'], 'netprofit')
        self.assertEqual(ser['wfo_costs_per_contract'], ALPHA_CONTEXT['wfo_costs_per_contract'])
        self.assertEqual(ser['wfo_members_count'], ALPHA_CONTEXT['wfo_members_count'])
        self.assertEqual(ser['wfo_optimizer_class_kwargs'], ALPHA_CONTEXT['wfo_optimizer_class_kwargs'])
        self.assertEqual(ser['position'], Position(dm).serialize())
        self.assertEqual(ser['wfo_optimizer_class'], 'tmqrstrategy.optimizers.OptimizerBase')
        self.assertEqual(ser['strategy_class'], 'tmqrstrategy.strategy_base.StrategyBase')

    def test_serialize_deserialize(self):
        dm = DataManager(date_start=datetime(2011, 1, 1), date_end=datetime(2012, 1, 1))

        ALPHA_CONTEXT = {
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
                ('period_slow', [10, 30]),
                ('period_fast', [1, 3])
            ],
            'wfo_members_count': 1,
            'wfo_costs_per_contract': 0.0,
            'wfo_scoring_type': 'netprofit'
        }

        alpha = AlphaGeneric(dm, **ALPHA_CONTEXT)

        alpha.run()

        alpa_record = alpha.serialize()

        last_period = {
            'iis_start': datetime(2010, 12, 31, 0, 0),
            'iis_end': datetime(2011, 12, 31, 0, 0),
            'oos_start': datetime(2011, 12, 31, 0, 0),
            'oos_end': datetime(2012, 2, 25, 0, 0)}

        self.assertEqual(alpa_record['wfo_last_period'], last_period)
        self.assertEqual(alpa_record['wfo_selected_alphas'], [(30, 1)])

        deserialized_alpha = AlphaGeneric.deserialize(dm, alpa_record.copy())
        deserialized_alpha_base = StrategyBase.deserialize(dm, alpa_record.copy())

        self.assertEqual(type(deserialized_alpha), type(alpha))
        self.assertEqual(type(deserialized_alpha_base), type(alpha))
        self.assertRaises(ArgumentError, AlphaAnother.deserialize, dm, alpa_record.copy())

        for k, v in deserialized_alpha_base.__dict__.items():
            if k not in ['temp']:
                self.assertEqual(alpha.__dict__[k], v, f'attribute={k}')
                self.assertEqual(alpha.__dict__[k], deserialized_alpha_base.__dict__[k], f'attribute={k}')

    def test_save_load_real_db(self):
        dm = DataManager(date_start=datetime(2011, 1, 1), date_end=datetime(2012, 1, 1))
        name = 'test_save_load_real_db_alpha'
        ALPHA_CONTEXT = {
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
                ('period_slow', [10, 30]),
                ('period_fast', [1, 3])
            ],
            'wfo_members_count': 1,
            'wfo_costs_per_contract': 0.0,
            'wfo_scoring_type': 'netprofit'

        }

        alpha = AlphaGeneric(dm, **ALPHA_CONTEXT, name=name)
        alpha.run()
        alpha.save()

        deserialized_alpha = AlphaGeneric.load(dm, name)
        deserialized_alpha_base = StrategyBase.load(dm, name)

        self.assertEqual(type(deserialized_alpha), type(alpha))
        self.assertEqual(type(deserialized_alpha_base), type(alpha))

        for k, v in deserialized_alpha_base.__dict__.items():
            if k in ['wfo_selected_alphas', 'wfo_opt_params']:
                #
                # The mongo converts tuples to list
                # this is normal, but requires special handling
                self.assertEqual([list(x) for x in alpha.__dict__[k]], v, f'attribute={k}')
                self.assertEqual([list(x) for x in alpha.__dict__[k]], deserialized_alpha_base.__dict__[k],
                                 f'attribute={k}')
            elif k not in ['temp']:
                self.assertEqual(alpha.__dict__[k], v, f'attribute={k}')
                self.assertEqual(alpha.__dict__[k], deserialized_alpha_base.__dict__[k], f'attribute={k}')
