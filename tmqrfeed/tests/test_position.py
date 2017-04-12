import unittest
from collections import OrderedDict
from datetime import datetime
from unittest.mock import patch, MagicMock

from tmqr.errors import *
from tmqrfeed.contracts import ContractBase
from tmqrfeed.manager import DataManager
from tmqrfeed.position import Position


class PositionTestCase(unittest.TestCase):
    def test_init(self):
        p = Position('datamanager')
        self.assertEqual(OrderedDict, type(p._position))
        self.assertEqual('datamanager', p.dm)

    def test_init_with_position_dict(self):
        p_dict = OrderedDict()
        dm = MagicMock(DataManager())
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        p = Position(dm, position_dict=p_dict)
        self.assertEqual(p._position, p_dict)

    def test_add_transaction_new(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

    def test_add_transaction_existing_close(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)
        p.add_transaction(dt, asset, -3.0)

        self.assertEqual(1, len(p._position))
        self.assertEqual(1, len(p._position[dt]))
        for i, v in enumerate((1.0, 2.0, 0.0)):
            self.assertEqual(v, p._position[dt][asset][i])

    def test_get_net_position_exists(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        p.add_transaction(dt, asset, 3.0)

        pos = p.get_net_position(dt)

        self.assertEqual(1, len(pos))
        self.assertEqual(True, asset in pos)
        self.assertEqual(dict, type(pos))
        self.assertEqual((1.0, 2.0, 3.0), pos[asset])

    def test_get_net_position_not_exists(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        self.assertRaises(PositionNotFoundError, p.get_net_position, dt)

    def test_add_net_position_new(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        self.assertEqual(0, len(p._position))

        new_position = {asset: (1.0, 2.0, 1.0)}

        p.add_net_position(dt, new_position, qty=2)

        self.assertEqual(1, len(p._position))
        self.assertEqual(1, len(p._position[dt]))
        for i, v in enumerate((1.0, 2.0, 2.0)):
            self.assertEqual(v, p._position[dt][asset][i])

    def test_add_net_position_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        new_position = {asset: (1.0, 2.0, 1.0)}

        p.add_net_position(dt, new_position, qty=2)

        self.assertEqual(1, len(p._position))
        self.assertEqual(1, len(p._position[dt]))
        for i, v in enumerate((1.0, 2.0, 5.0)):
            self.assertEqual(v, p._position[dt][asset][i])

    def test_add_net_position_insert_before_lastday_error(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        new_position = {asset: (1.0, 2.0, 1.0)}
        self.assertRaises(ArgumentError, p.add_net_position, datetime(2010, 1, 1), new_position, qty=2)

    def test_add_transaction_insert_before_lastday_error(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertRaises(ArgumentError, p.add_transaction, datetime(2010, 1, 1), asset, 3.0)

    def test__prev_day_key(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        self.assertRaises(PositionNotFoundError, p._prev_day_key, None)
        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(dt, p._prev_day_key(date=None))
        self.assertRaises(PositionNotFoundError, p._prev_day_key, dt)

        p.add_transaction(datetime(2011, 1, 2), asset, 3.0)
        self.assertEqual(dt, p._prev_day_key(date=datetime(2011, 1, 2)))

    def test__check_position_validity(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        new_position = {asset: (1.0, 2.0, 1.0)}
        # Valid method
        self.assertEqual(None, p._check_position_validity(new_position))
        self.assertEqual(None, p._check_position_validity({}))

        self.assertRaises(ArgumentError, p._check_position_validity, [])
        self.assertRaises(ArgumentError, p._check_position_validity, {'asset': (1.0, 2.0, 1.0)})
        self.assertRaises(ArgumentError, p._check_position_validity, {asset: [1.0, 2.0, 1.0]})
        self.assertRaises(ArgumentError, p._check_position_validity, {asset: (2.0, 1.0)})

    def test_set_net_position_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        with patch('tmqrfeed.position.Position._check_position_validity') as mock__check_position_validity:
            p.add_transaction(dt, asset, 3.0)

            self.assertEqual(1, len(p._position))
            for i, v in enumerate((1.0, 2.0, 3.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            new_position = {asset: (1.0, 2.0, 1.0)}

            p.set_net_position(dt, new_position)

            self.assertEqual(True, mock__check_position_validity.called)
            self.assertEqual(1, len(p._position))
            self.assertEqual(1, len(p._position[dt]))
            for i, v in enumerate((1.0, 2.0, 1.0)):
                self.assertEqual(v, p._position[dt][asset][i])

    def test_keep_previous_position_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        dm.price_get.return_value = (5.0, 6.0)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(1, len(p._position[dt2]))

        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        for i, v in enumerate((5.0, 6.0, 3.0)):
            self.assertEqual(v, p._position[dt2][asset][i])

        self.assertRaises(ArgumentError, p.keep_previous_position, datetime(2010, 1, 2))

        def mock_get_net_position_side(*args, **kwargs):
            raise PositionNotFoundError('PositionNotFoundError raised')

        with patch('tmqrfeed.position.Position.get_net_position') as mock_get_net_position:
            mock_get_net_position.side_effect = mock_get_net_position_side
            with patch('tmqr.logs.log.warn') as mock_log:
                p.keep_previous_position(dt2)
                self.assertEqual(True, mock_log.called)

    def test_get_asset_price(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        self.assertEqual((1.0, 2.0), p.get_asset_price(dt, asset))

    def test_get_asset_price_quote_not_found(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 2), asset)
        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 1), 'not_existing_asset')

    def test_merge_positions(self):

        dm = MagicMock(DataManager())
        asset = MagicMock(ContractBase("US.S.AAPL", dm), name='Asset')
        asset2 = MagicMock(ContractBase("US.S.GOOG", dm), name='Asset2')

        p_dict = OrderedDict()
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2), asset2: (200, 201, 4)}
        p_dict[datetime(2011, 1, 2)] = {asset: (100, 101, 2)}

        p_dict2 = OrderedDict()
        p_dict2[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}
        p_dict2[datetime(2011, 1, 2)] = {asset: (100, 101, 2), asset2: (200, 201, 4)}
        p_dict2[datetime(2011, 1, 3)] = {asset2: (200, 201, 4)}

        p_dict3 = OrderedDict()
        p_dict3[datetime(2011, 1, 4)] = {asset: (100, 101, 2)}

        p1 = Position(dm, position_dict=p_dict)
        p2 = Position(dm, position_dict=p_dict2)
        p3 = Position(dm, position_dict=p_dict3)

        merged_pos = Position.merge(dm, [p1, p2, p3])
        self.assertEqual(Position, type(merged_pos))

        m_pdict = merged_pos._position

        self.assertEqual(4, len(m_pdict))

        expected_dict = OrderedDict()
        expected_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 4), asset2: (200, 201, 4)}
        expected_dict[datetime(2011, 1, 2)] = {asset: (100, 101, 4), asset2: (200, 201, 4)}
        expected_dict[datetime(2011, 1, 3)] = {asset2: (200, 201, 4)}
        expected_dict[datetime(2011, 1, 4)] = {asset: (100, 101, 2)}

        for dt, val in expected_dict.items():
            self.assertEqual(m_pdict[dt], val)
