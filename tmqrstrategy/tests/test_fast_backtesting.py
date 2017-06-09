import unittest
from unittest.mock import MagicMock, patch
from tmqrstrategy.optimizers import OptimizerBase, OptimizerGenetic
from tmqrstrategy.strategy_base import StrategyBase
from tmqr.errors import *
import pyximport

pyximport.install()
from tmqrstrategy.fast_backtesting import *


class FastScoringTestCase(unittest.TestCase):
    def test_exposure(self):
        idx = np.array([0, 1, 2, 3, 4, 5])
        px = np.array([0, 0, 0, 0, 0, 0], dtype=np.float)
        size = np.array([1, 2, 3, 4, 5, 6], dtype=np.float)

        ent = np.array([0, 1, 1, 0, 0, 0], dtype=np.uint8)
        ext = np.array([0, 1, 1, 0, 0, 1], dtype=np.uint8)

        price_series = px
        # Error checks
        # self.assertRaises(ArgumentError, exposure, None, ent, ext, 1)
        self.assertRaises(ArgumentError, exposure, price_series, ent[:1], ext, 1)
        self.assertRaises(ArgumentError, exposure, price_series, ent, ext[:1], 1)
        self.assertRaises(ArgumentError, exposure, price_series, ent, ext, 1, size[:1])

        # Exposure calculation checks
        ent = np.array([0, 1, 1, 0, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 0, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, 1, 1, 1, 1, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, 1)
        self.assertTrue(np.all(exp == result))

        # Exposure calculation checks
        #
        # MOST DISCUSSING case:
        #   what to do when we have entry and exit rules on the same bar???
        ent = np.array([0, 1, 1, 0, 0, 0], dtype=np.uint8)
        ext = np.array([0, 1, 0, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, 1, 1, 1, 1, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, 1)
        self.assertTrue(np.all(exp == result))

        # Next day exit
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, 1, 0, 1, 1, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, 1)
        self.assertTrue(np.all(exp == result))

        # Short
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, -1, 0, -1, -1, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, -1)
        self.assertTrue(np.all(exp == result))

        # Size fixed int
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, -2, 0, -2, -2, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, -1, size_exposure=2)
        self.assertTrue(np.all(exp == result))

        # Size series
        size = np.array([1, 2, 3, 4, 5, 6], dtype=np.float)
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, -2, 0, -4, -4, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, -1, size_exposure=size)
        self.assertTrue(np.all(exp == result))

        result = exposure(price_series, ent, ext, -1, size_exposure=pd.Series(size, index=idx))
        self.assertTrue(np.all(exp == result))

        # NBar stop
        size = np.array([1, 2, 3, 4, 5, 6], dtype=np.float)
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, 1, 0, 1, 0, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, 1, nbar_stop=1)
        self.assertTrue(np.all(exp == result))

        # NBar stop
        size = np.array([1, 2, 3, 4, 5, 6], dtype=np.float)
        ent = np.array([0, 1, 1, 1, 0, 0], dtype=np.uint8)
        ext = np.array([0, 0, 1, 0, 0, 1], dtype=np.uint8)
        exp = np.array([0, 1, 0, 1, 1, 0], dtype=np.float)

        result = exposure(price_series, ent, ext, 1, nbar_stop=2)
        self.assertTrue(np.all(exp == result))

    def test_score_net_profit(self):
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 1, 2, 0, 0, 0], dtype=np.float)

        # Length checks
        self.assertRaises(ArgumentError, score_netprofit, pxs, exp[:1])

        net_profit = score_netprofit(pxs, exp)
        self.assertEqual(sum([0, 0, 1 * 2, 2 * 2, 0, 0]), net_profit)

        # Apply costs
        net_profit = score_netprofit(pxs, exp, costs=0.5)
        self.assertEqual(sum([0, -0.5 * 1, 1 * 2 - 0.5 * 1, 2 * 2 - 0.5 * 2, 0, 0]), net_profit)

        # Apply costs series
        cst = np.array([0, 1.0, 0.3, 1.2, 0, 0], dtype=np.float)
        net_profit = score_netprofit(pxs, exp, costs=cst)
        self.assertAlmostEqual(sum([0, -1.0 * 1, 1 * 2 - 0.3 * 1, 2 * 2 - 1.2 * 2, 0, 0]), net_profit, 2)

        self.assertRaises(ArgumentError, score_netprofit, pxs, exp, costs=cst[:1])

    def test_exposure_trades(self):
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 1, 2, 0, 0, 0], dtype=np.float)

        # Length checks
        self.assertRaises(ArgumentError, exposure_trades, pxs, exp[:1])

        net_profit = exposure_trades(pxs, exp)
        self.assertEqual(sum([0, 0, 1 * 2, 2 * 2, 0, 0]), sum(net_profit))

        # Apply costs
        net_profit = exposure_trades(pxs, exp, costs=0.5)
        self.assertEqual(sum([0, -0.5 * 1, 1 * 2 - 0.5 * 1, 2 * 2 - 0.5 * 2, 0, 0]), sum(net_profit))

        # Apply costs series
        cst = np.array([0, 1.0, 0.3, 1.2, 0, 0], dtype=np.float)
        net_profit = exposure_trades(pxs, exp, costs=cst)
        self.assertAlmostEqual(sum([0, -1.0 * 1, 1 * 2 - 0.3 * 1, 2 * 2 - 1.2 * 2, 0, 0]), sum(net_profit), 2)

        self.assertRaises(ArgumentError, exposure_trades, pxs, exp, costs=cst[:1])

        # Compare trades list
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 1, 2, 0, 0, 0], dtype=np.float)

        trades = exposure_trades(pxs, exp)
        expected = np.array([6.0], dtype=np.float)
        self.assertTrue(np.all(trades == expected))

        # Compare trades list
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 1, 2, 0, 1, 0], dtype=np.float)

        trades = exposure_trades(pxs, exp)
        expected = np.array([6.0, 1.0], dtype=np.float)
        self.assertTrue(np.all(trades == expected))

        #
        #  First bar-is ignored because we don't know the previous exposure
        #
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([1, 0, 2, 0, 1, 0], dtype=np.float)

        trades = exposure_trades(pxs, exp)
        expected = np.array([4.0, 1.0], dtype=np.float)
        self.assertTrue(np.all(trades == expected))

        #
        # Last bar trade is accounted
        #
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 0, 2, 0, 0, 1], dtype=np.float)

        trades = exposure_trades(pxs, exp)
        expected = np.array([4.0, 0.0], dtype=np.float)
        self.assertTrue(np.all(trades == expected))

        #
        # Last bar trade is accounted
        #
        pxs = np.array([1, 3, 5, 7, 8, 9], dtype=np.float)
        exp = np.array([0, 1, 0, 1, 0, 1], dtype=np.float)

        trades = exposure_trades(pxs, exp)
        expected = np.array([2.0, 1.0, 0.0], dtype=np.float)
        self.assertTrue(np.all(trades == expected))
