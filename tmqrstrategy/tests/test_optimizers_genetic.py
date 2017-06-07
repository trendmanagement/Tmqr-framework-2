import unittest
from unittest.mock import MagicMock, patch
from tmqrstrategy.optimizers import OptimizerBase, OptimizerGenetic
from tmqrstrategy.strategy_base import StrategyBase
from tmqr.errors import *


class OptimizerGeneticTestCase(unittest.TestCase):
    def test_init(self):
        strategy = MagicMock()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4]),
        ]
        with patch('random.seed') as mock_random:
            opt = OptimizerGenetic(strategy, params)

            self.assertEqual(opt.strategy, strategy)
            self.assertEqual(opt.opt_params, params)

            # Test default kwargs
            self.assertEqual(opt.nbest_count, 30)
            self.assertEqual(opt.nbest_fitness_method, 'max')

            self.assertEqual(None, mock_random.call_args[0][0])
            self.assertEqual(200, opt.population_size)
            self.assertEqual(0.5, opt.cross_prob)
            self.assertEqual(0.1, opt.mut_prob)
            self.assertEqual(30, opt.number_generations)

    def test_init_kwargs(self):
        strategy = MagicMock()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4]),
        ]
        with patch('random.seed') as mock_random:
            opt = OptimizerGenetic(strategy, params,
                                   nbest_count=10,
                                   nbest_fitness_method='min',
                                   rand_seed=64,
                                   population_size=2000,
                                   cross_prob=0.55,
                                   mut_prob=0.11,
                                   number_generations=300,
                                   )

            self.assertEqual(opt.strategy, strategy)
            self.assertEqual(opt.opt_params, params)

            # Test default kwargs
            self.assertEqual(opt.nbest_count, 10)
            self.assertEqual(opt.nbest_fitness_method, 'min')

            self.assertEqual(64, mock_random.call_args[0][0])
            self.assertEqual(2000, opt.population_size)
            self.assertEqual(0.55, opt.cross_prob)
            self.assertEqual(0.11, opt.mut_prob)
            self.assertEqual(300, opt.number_generations)

    def test_mutate(self):
        with patch('random.choice') as mock_random_choice:
            with patch('random.randint') as mock_randint:
                ind = [0, 0]
                params_uni = [[1, 2], [3, 4], [5, 6]]

                mock_randint.return_value = 1
                mock_random_choice.return_value = [3, 4]

                result = OptimizerGenetic.mutate(ind, params_uni)

                self.assertEqual(tuple, type(result))
                self.assertEqual(1, len(result))
                self.assertEqual(result[0], ([0, 4]))

    def test_mate(self):
        with patch('deap.tools.cxOnePoint') as mock_cx_onepoint:
            ind1 = [0, 0]
            ind2 = [1, 2]

            OptimizerGenetic.mate(ind1, ind2)

            self.assertEqual(True, mock_cx_onepoint.called)
            self.assertEqual(ind1, mock_cx_onepoint.call_args[0][0])
            self.assertEqual(ind2, mock_cx_onepoint.call_args[0][1])

    def test_evaluate(self):
        individual = [1, 2]

        strategy = MagicMock(StrategyBase)()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4]),
        ]
        opt = OptimizerGenetic(strategy, params)

        strategy.calculate.return_value = [12, 12, 13]
        strategy.score.return_value = 100500

        result = opt.evaluate(individual)

        self.assertEqual(tuple(individual), strategy.calculate.call_args[0])
        self.assertEqual([12, 12, 13], strategy.score.call_args[0][0])
        self.assertEqual((100500,), result)

    def test_optimize(self):

        strategy = MagicMock(StrategyBase)()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4, 5, 10]),
            ('period_false', [10, 11, 12, 13])

        ]
        with patch('tmqrstrategy.optimizers.OptimizerGenetic.evaluate') as mock_eval:
            with patch('deap.algorithms.eaSimple') as mock_algo_easimple:
                mock_algo_easimple.return_value = (None, None)
                mock_eval.side_effect = lambda x: sum(x)

                opt = OptimizerGenetic(strategy, params)
                opt.optimize()
                self.assertEqual(30, opt.hof.maxsize)

                self.assertEqual(len(mock_algo_easimple.call_args[0][0]), opt.population_size)

                for k, v in {'cxpb': 0.5, 'mutpb': 0.1, 'ngen': 30, 'verbose': False}.items():
                    self.assertEqual(mock_algo_easimple.call_args[1][k], v)

    def test_optimize_fitness_direction_max(self):

        strategy = MagicMock(StrategyBase)()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4, 5, 10]),
            ('period_false', [10, 11, 12, 13])

        ]
        with patch('tmqrstrategy.optimizers.OptimizerGenetic.evaluate') as mock_eval:
            with patch('deap.algorithms.eaSimple') as mock_algo_easimple:
                mock_algo_easimple.return_value = (None, None)
                mock_eval.side_effect = lambda x: sum(x)
                opt = OptimizerGenetic(strategy, params, nbest_fitness_method='max')
                opt.optimize()

                toolbox = mock_algo_easimple.call_args[0][1]
                self.assertEqual(toolbox.individual.args[0]().fitness.weights, (1.0,))

    def test_optimize_fitness_direction_min(self):

        strategy = MagicMock(StrategyBase)()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4, 5, 10]),
            ('period_false', [10, 11, 12, 13])

        ]
        with patch('tmqrstrategy.optimizers.OptimizerGenetic.evaluate') as mock_eval:
            with patch('deap.algorithms.eaSimple') as mock_algo_easimple:
                mock_algo_easimple.return_value = (None, None)
                mock_eval.side_effect = lambda x: sum(x)
                opt = OptimizerGenetic(strategy, params, nbest_fitness_method='min')
                opt.optimize()

                toolbox = mock_algo_easimple.call_args[0][1]
                self.assertEqual(toolbox.individual.args[0]().fitness.weights, (-1.0,))

    def test_optimize_fitness_direction_unknown(self):

        strategy = MagicMock(StrategyBase)()
        params = [
            ('direction', [1, -1]),
            ('period_slow', [2, 4, 5, 10]),
            ('period_false', [10, 11, 12, 13])

        ]
        with patch('tmqrstrategy.optimizers.OptimizerGenetic.evaluate') as mock_eval:
            with patch('deap.algorithms.eaSimple') as mock_algo_easimple:
                mock_algo_easimple.return_value = (None, None)
                mock_eval.side_effect = lambda x: sum(x)
                opt = OptimizerGenetic(strategy, params, nbest_fitness_method='invalid')
                self.assertRaises(SettingsError, opt.optimize)
