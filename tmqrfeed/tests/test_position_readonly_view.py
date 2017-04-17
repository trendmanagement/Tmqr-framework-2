import unittest
from tmqrfeed.position import Position, PositionReadOnlyView
from unittest.mock import MagicMock
from datetime import datetime
from tmqrfeed.contracts import ContractBase
from tmqrfeed.manager import DataManager
from tmqr.errors import ArgumentError, PositionReadOnlyError, PositionQuoteNotFoundError


class PositionReadOnlyViewTestCase(unittest.TestCase):
    def setUp(self):
        self.dm = MagicMock(DataManager())
        self.dm.price_get.return_value = (1.0, 2.0)

        self.p = Position(self.dm)
        self.dt = datetime(2011, 1, 1, 10, 35)
        self.asset = MagicMock(ContractBase("US.S.AAPL"), self.dm)
        self.p.add_transaction(self.dt, self.asset, 3.0)

        self.pos_view = PositionReadOnlyView(self.dm, self.p._position, decision_time_shift=0)
        self.pos_view_shifted = PositionReadOnlyView(self.dm, self.p._position, decision_time_shift=5)

    def test_init(self):
        self.assertRaises(ArgumentError, PositionReadOnlyView, self.dm, self.p._position, decision_time_shift=-5)

    def test_get_net_position(self):
        pos = self.pos_view.get_net_position(self.dt)
        self.assertEqual(1, len(pos))
        self.assertEqual(True, self.asset in pos)
        self.assertEqual(dict, type(pos))
        self.assertEqual((1.0, 2.0, 3.0), pos[self.asset])

    def test_get_net_position_shifted(self):
        pos = self.pos_view_shifted.get_net_position(datetime(2011, 1, 1, 10, 40))

        self.assertEqual(1, len(pos))
        self.assertEqual(True, self.asset in pos)
        self.assertEqual(dict, type(pos))
        self.assertEqual((1.0, 2.0, 3.0), pos[self.asset])

    def test_read_only_errors(self):
        self.assertRaises(PositionQuoteNotFoundError, self.pos_view.get_asset_price, None, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view.get_pnl_series)
        self.assertRaises(PositionReadOnlyError, self.pos_view.serialize)
        self.assertRaises(PositionReadOnlyError, self.pos_view.set_net_position, None, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view.add_transaction, None, None, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view.add_net_position, None, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view.close, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view.keep_previous_position, None)
        self.assertRaises(PositionReadOnlyError, self.pos_view._prev_day_key, None)
