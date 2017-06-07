import unittest
from unittest.mock import MagicMock, patch
from tmqrstrategy.optimizers import OptimizerBase
from tmqr.errors import *


class OptimizerBaseTestCase(unittest.TestCase):
    def test_init(self):
        strategy = MagicMock()
        params = [
            ('direction', [1, -1]),
            ('period_fast', list(range(1, 50))),
            ('period_slow', list(range(10, 200))),
        ]

        opt = OptimizerBase(strategy, params, nbest_count=10)

        self.assertEqual(opt.strategy, strategy)
        self.assertEqual(opt.opt_params, params)
        self.assertEqual(opt.nbest_count, 10)

    def test_check_params_integrity(self):
        strategy = MagicMock()
        params_valid = [
            ('direction', [1, -1]),
            ('period_fast', list(range(1, 50))),
            ('period_slow', list(range(10, 200))),
        ]
        # No exception
        OptimizerBase(strategy, params_valid)

        params_tuple = (
            ('direction', [1, -1]),
        )
        OptimizerBase(strategy, params_tuple)

        params_dict = {}
        self.assertRaises(SettingsError, OptimizerBase, strategy, params_dict)

        # None params
        self.assertRaises(SettingsError, OptimizerBase, strategy, None)

        # Zero length params
        self.assertRaises(SettingsError, OptimizerBase, strategy, [])

        params_invalid_member = [
            {'direction': [1, -1]},
            ('period_fast', list(range(1, 50))),
            ('period_slow', list(range(10, 200))),
        ]
        self.assertRaises(SettingsError, OptimizerBase, strategy, params_invalid_member)

        params_invalid_member_count = [
            ('direction',),
            ('period_fast', list(range(1, 50))),
            ('period_slow', list(range(10, 200))),
        ]
        self.assertRaises(SettingsError, OptimizerBase, strategy, params_invalid_member_count)

        # Parameter name must be a string
        params = [
            (['direction'], [1, -1]),
            ('period_fast', list(range(1, 50))),
            ('period_slow', list(range(10, 200))),
        ]
        self.assertRaises(SettingsError, OptimizerBase, strategy, params)

        # Parameter values must be list or tuple
        params = [
            ('direction', 'test'),
        ]
        self.assertRaises(SettingsError, OptimizerBase, strategy, params)

        params = [
            ('direction', None),
        ]
        self.assertRaises(SettingsError, OptimizerBase, strategy, params)

    def test__update_score_board_max_n1(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        new_score = 2.0
        new_param = [2.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 2.0)
        self.assertEqual(sb_params[0], [2.0])

        # Ignore
        new_score = 0.5
        new_param = [0.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 2.0)
        self.assertEqual(sb_params[0], [2.0])

    def test__update_score_board_max_n2(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        new_score = 2.0
        new_param = [2.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [1.0, 2.0])
        self.assertEqual(sb_params, [[1.0], [2.0]])

        # Ignore
        new_score = 0.5
        new_param = [0.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [1.0, 2.0])
        self.assertEqual(sb_params, [[1.0], [2.0]])

        # Ignore
        new_score = 1.5
        new_param = [1.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [1.5, 2.0])
        self.assertEqual(sb_params, [[1.4], [2.0]])

    def test__update_score_board_max_n_none(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        new_score = 2.0
        new_param = [2.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [1.0, 2.0])
        self.assertEqual(sb_params, [[1.0], [2.0]])

        new_score = 1.5
        new_param = [1.5]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)

        self.assertEqual(3, len(sb_scores))
        self.assertEqual(3, len(sb_params))
        self.assertEqual(sb_scores, [1.0, 1.5, 2.0])
        self.assertEqual(sb_params, [[1.0], [1.5], [2.0]])

    def test__update_score_board_errors_check(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        self.assertRaises(ArgumentError, OptimizerBase._update_score_board, sb_scores, sb_params, new_score, new_param,
                          -1, fitness_direction=1)

        self.assertRaises(ArgumentError, OptimizerBase._update_score_board, sb_scores, sb_params, new_score, new_param,
                          1, fitness_direction=2)

        # Skip bad new_scores
        new_score = None
        new_param = [1.5]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)
        self.assertEqual(0, len(sb_scores))

        new_score = float('nan')
        new_param = [1.5]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)
        self.assertEqual(0, len(sb_scores))

        new_score = float('inf')
        new_param = [1.5]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, None, fitness_direction=1)
        self.assertEqual(0, len(sb_scores))

    def test__update_score_board_min_n1(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=-1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        new_score = 2.0
        new_param = [2.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=-1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        # Ignore
        new_score = 0.5
        new_param = [0.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 1, fitness_direction=-1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 0.5)
        self.assertEqual(sb_params[0], [0.4])

    def test__update_score_board_min_n2(self):
        sb_scores = []
        sb_params = []

        new_score = 1.0
        new_param = [1.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=-1)

        self.assertEqual(1, len(sb_scores))
        self.assertEqual(1, len(sb_params))
        self.assertEqual(sb_scores[0], 1.0)
        self.assertEqual(sb_params[0], [1.0])

        new_score = 2.0
        new_param = [2.0]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=-1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [1.0, 2.0])
        self.assertEqual(sb_params, [[1.0], [2.0]])

        # Ignore
        new_score = 0.5
        new_param = [0.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=-1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [0.5, 1.0])
        self.assertEqual(sb_params, [[0.4], [1.0]])

        # Ignore
        new_score = 1.5
        new_param = [1.4]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=-1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [0.5, 1.0])
        self.assertEqual(sb_params, [[0.4], [1.0]])

        # Ignore
        new_score = 0.8
        new_param = [0.6]
        OptimizerBase._update_score_board(sb_scores, sb_params, new_score, new_param, 2, fitness_direction=-1)

        self.assertEqual(2, len(sb_scores))
        self.assertEqual(2, len(sb_params))
        self.assertEqual(sb_scores, [0.5, 0.8])
        self.assertEqual(sb_params, [[0.4], [0.6]])

    def test_optimize(self):
        params = [
            ('direction', [1, -1]),
            ('period', [3, 4])
        ]

        strategy = MagicMock()

        def calculate(*params):
            return params

        def score(params):
            return params[0] + params[1] / 10.0 * params[0]

        def pick(params):
            return params

        strategy.calculate.side_effect = calculate
        strategy.score.side_effect = score
        strategy.pick.side_effect = pick

        optimizer = OptimizerBase(strategy, params, nbest_count=None, nbest_fitness_method='max')
        picked_members = optimizer.optimize()
        self.assertEqual([(-1, 4), (-1, 3), (1, 3), (1, 4)], picked_members)
        pass

    def test_optimize_errors(self):
        params = [
            ('direction', [1, -1]),
            ('period', [3, 4])
        ]
        strategy = MagicMock()

        optimizer = OptimizerBase(strategy, params, nbest_count=None, nbest_fitness_method='unkn')
        self.assertRaises(SettingsError, optimizer.optimize)
