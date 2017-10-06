import unittest
from collections import OrderedDict
from datetime import datetime
from unittest.mock import patch, MagicMock

from tmqr.errors import *
from tmqrfeed.contracts import *
from tmqrfeed.manager import DataManager
from tmqrfeed.position import Position, PositionReadOnlyView
import pandas as pd
import numpy as np
import pickle
import lz4


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
        asset.price.return_value = (1.0, 2.0)

        self.assertRaises(ArgumentError, p.add_transaction, dt, asset, 0.0)

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
        asset.price.return_value = (1.0, 2.0)

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
        asset.price.return_value = (1.0, 2.0)

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

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        self.assertEqual(0, len(p._position))

        new_position = {asset: (5.0, 6.0, 1.0)}

        # zero-qty is skipped, but added position record for date
        # to maintain flat equity line
        p.add_net_position(dt, new_position, qty=0.0)
        self.assertEqual(1, len(p._position))
        self.assertEqual(0, len(p._position[dt]))

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
        asset.price.return_value = (1.0, 2.0)

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
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        new_position = {asset: (1.0, 2.0, 1.0)}
        self.assertRaises(ArgumentError, p.add_net_position, datetime(2010, 1, 1), new_position, qty=2)

    def test_add_transaction_insert_before_lastday_error(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        self.assertRaises(ArgumentError, p.add_transaction, datetime(2010, 1, 1), asset, 3.0)

    def test__prev_day_key(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        self.assertRaises(PositionNotFoundError, p._prev_day_key, None)
        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(dt, p._prev_day_key(date=None))
        self.assertRaises(PositionNotFoundError, p._prev_day_key, dt)

        p.add_transaction(datetime(2011, 1, 2), asset, 3.0)
        self.assertEqual(dt, p._prev_day_key(date=datetime(2011, 1, 2)))

    def test_last_date(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        self.assertRaises(PositionNotFoundError, p._prev_day_key, None)
        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(dt, p.last_date)

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

    def test_has_position(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        self.assertFalse(p.has_position(dt))
        p.add_transaction(dt, asset, 3.0)

        self.assertTrue(p.has_position(dt))

        with patch('tmqrfeed.position.Position._check_position_validity') as mock__check_position_validity:
            self.assertEqual(1, len(p._position))
            for i, v in enumerate((1.0, 2.0, 3.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            new_position = {asset: (1.0, 2.0, 0.0)}
            p.set_net_position(dt, new_position)
            self.assertFalse(p.has_position(dt))

            p.set_net_position(dt, {})
            self.assertTrue(p.has_position(dt, check_pos_qty=False))


    def test_set_net_position_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

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

    def test_set_net_position_qty_factor(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        with patch('tmqrfeed.position.Position._check_position_validity') as mock__check_position_validity:
            p.add_transaction(dt, asset, 3.0)

            self.assertEqual(1, len(p._position))
            for i, v in enumerate((1.0, 2.0, 3.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            new_position = {asset: (1.0, 2.0, 1.0)}

            p.set_net_position(dt, new_position, qty=-2)

            self.assertEqual(True, mock__check_position_validity.called)
            self.assertEqual(1, len(p._position))
            self.assertEqual(1, len(p._position[dt]))
            for i, v in enumerate((1.0, 2.0, -2.0)):
                self.assertEqual(v, p._position[dt][asset][i])

    def test_set_net_position_qty_is_zero(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        with patch('tmqrfeed.position.Position._check_position_validity') as mock__check_position_validity:
            new_position = {asset: (1.0, 2.0, 1.0)}

            p.set_net_position(dt, new_position, qty=0)

            self.assertEqual(True, mock__check_position_validity.called)
            self.assertEqual(1, len(p._position))
            self.assertEqual(0, len(p._position[dt]))

    def test_set_net_position_previous_date_raises_error(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        with patch('tmqrfeed.position.Position._check_position_validity') as mock__check_position_validity:
            p.add_transaction(dt, asset, 3.0)

            self.assertEqual(1, len(p._position))
            for i, v in enumerate((1.0, 2.0, 3.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            new_position = {asset: (1.0, 2.0, 1.0)}

            p.set_net_position(dt, new_position, qty=-2)

            self.assertEqual(True, mock__check_position_validity.called)
            self.assertEqual(1, len(p._position))
            self.assertEqual(1, len(p._position[dt]))
            for i, v in enumerate((1.0, 2.0, -2.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            p.set_net_position(dt, new_position, qty=-2)

            self.assertEqual(True, mock__check_position_validity.called)
            self.assertEqual(1, len(p._position))
            self.assertEqual(1, len(p._position[dt]))
            for i, v in enumerate((1.0, 2.0, -2.0)):
                self.assertEqual(v, p._position[dt][asset][i])

            self.assertRaises(ArgumentError, p.set_net_position, datetime(2010, 12, 31), new_position, qty=-2)



    def test_keep_previous_position_skip_zero_qty(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        new_position = {asset: (1.0, 2.0, 0.0)}
        p.set_net_position(dt, new_position)

        dm.price_get.return_value = (5.0, 6.0)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(0, len(p._position[dt2]))

    def test_keep_previous_position_skip_already_expired_asset_exception(self):
        dm = MagicMock(DataManager())

        def price_get_side(*args, **kwargs):
            raise AssetExpiredError()

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)

        new_position = {asset: (1.0, 2.0, 1.0)}
        p.set_net_position(dt, new_position)

        asset.price.side_effect = price_get_side

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(0, len(p._position[dt2]))

    def test_keep_previous_position_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        asset.price.return_value = (5.0, 6.0)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(1, len(p._position[dt2]))

        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        for i, v in enumerate((5.0, 6.0, 3.0)):
            self.assertEqual(v, p._position[dt2][asset][i])

    def test_keep_previous_position_existing_double_call_error(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        asset.price.return_value = (5.0, 6.0)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(True, dt in p._position)
        self.assertEqual(True, dt2 in p._position)

        for i, v in enumerate((5.0, 6.0, 3.0)):
            self.assertEqual(v, p._position[dt2][asset][i])

        #
        # But this is not allowed to call previous days once we have them processed
        #
        self.assertRaises(ArgumentError, p.keep_previous_position, dt)


    def test_keep_previous_position_existing_but_empty(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        asset.price.return_value = (5.0, 6.0)
        p.close(dt)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertEqual(0, len(p._position[dt2]))

    def test_keep_previous_position_overwrites_existing(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)
        p.keep_previous_position(dt)

        self.assertEqual(1, len(p._position))
        self.assertTrue(dt in p._position)
        self.assertEqual(0, len(p._position[dt]))

    def test_keep_previous_position_overwrites_existing_add_postion(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        dt2 = datetime(2011, 1, 2)
        p.keep_previous_position(dt2)
        # Add new
        p.add_transaction(dt2, asset, 10.0)

        # Expected to be overwritten
        p.keep_previous_position(dt2)

        self.assertEqual(2, len(p._position))
        self.assertTrue(dt in p._position)
        self.assertEqual(1, len(p._position[dt]))
        self.assertEqual(3.0, p._position[dt2][asset][2])

        self.assertTrue(dt2 in p._position)
        self.assertEqual(1, len(p._position[dt2]))
        self.assertEqual(3.0, p._position[dt2][asset][2])




    def test_keep_previous_position_not_exists_warn(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)


        with patch('tmqrfeed.position.Position.get_net_position') as mock_get_net_position:
            with patch('tmqr.logs.log.warn') as mock_log:
                p.keep_previous_position(dt)
                self.assertEqual(True, mock_log.called)

    def test_get_asset_price(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

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
        asset.ctype = 'F'
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 3.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        asset2 = MagicMock(ContractBase("US.S.AAPL_NOEXIST"), dm)

        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 2), asset)
        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 1), asset2)

        asset2.ctype = 'C'
        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 1), asset2)

        asset2.ctype = 'P'
        self.assertRaises(PositionQuoteNotFoundError, p.get_asset_price, datetime(2011, 1, 1), asset2)


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

    def test_merge_positions_with_decision_time_shift(self):

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

        p1 = Position(dm, position_dict=p_dict, decision_time_shift=5)
        p2 = Position(dm, position_dict=p_dict2, decision_time_shift=5)
        p3 = Position(dm, position_dict=p_dict3, decision_time_shift=5)

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

        self.assertEqual(merged_pos.kwargs['decision_time_shift'], 5)

    def test_merge_positions_with_decision_time_shift_error_mixed(self):

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

        p1 = Position(dm, position_dict=p_dict, decision_time_shift=3)
        p2 = Position(dm, position_dict=p_dict2, decision_time_shift=5)
        p3 = Position(dm, position_dict=p_dict3, decision_time_shift=5)

        self.assertRaises(ArgumentError, Position.merge, dm, [p1, p2, p3])

        p1 = Position(dm, position_dict=p_dict, decision_time_shift=5)
        p2 = Position(dm, position_dict=p_dict2, decision_time_shift=3)
        p3 = Position(dm, position_dict=p_dict3, decision_time_shift=5)

        self.assertRaises(ArgumentError, Position.merge, dm, [p1, p2, p3])

        p1 = Position(dm, position_dict=p_dict)
        p2 = Position(dm, position_dict=p_dict2, decision_time_shift=5)
        p3 = Position(dm, position_dict=p_dict3, decision_time_shift=5)

        self.assertRaises(ArgumentError, Position.merge, dm, [p1, p2, p3])

        p1 = Position(dm, position_dict=p_dict, decision_time_shift=5)
        p2 = Position(dm, position_dict=p_dict2)
        p3 = Position(dm, position_dict=p_dict3, decision_time_shift=5)

        self.assertRaises(ArgumentError, Position.merge, dm, [p1, p2, p3])


    def test_close(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)
        asset = MagicMock(ContractBase("US.S.AAPL"), dm)
        asset.price.return_value = (1.0, 2.0)

        p.add_transaction(dt, asset, 3.0)
        p.close(dt)

        self.assertEqual(1, len(p._position))
        for i, v in enumerate((1.0, 2.0, 0.0)):
            self.assertEqual(v, p._position[dt][asset][i])

        # Test non existing dates ignored
        p.close(datetime(2011, 1, 2))

    def test_serialize(self):
        p_dict = OrderedDict()
        dm = MagicMock(DataManager())
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        p = Position(dm, position_dict=p_dict, some_kwarg=1.0)
        self.assertEqual(p._position, p_dict)

        serialized = p.serialize()

        d = pickle.loads(lz4.block.decompress(serialized['data']))
        self.assertEqual(len(p_dict), len(d))
        for k, asset_pos in p_dict.items():
            self.assertTrue(k in d)
            for asset_key, asset_value in asset_pos.items():
                self.assertEqual(asset_value, d[k][asset_key.ticker])

    def test_deserialize_position(self):
        p_dict = OrderedDict()
        dm = MagicMock(DataManager())
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        p = Position(dm, position_dict=p_dict, some_kwarg=1.0)
        self.assertEqual(p._position, p_dict)
        serialized = p.serialize()

        res_pos = Position.deserialize(serialized, dm, as_readonly=False)
        self.assertEqual(type(res_pos), Position)
        self.assertEqual({'some_kwarg': 1.0}, res_pos.kwargs)

        for k, asset_pos in p_dict.items():
            self.assertTrue(k in res_pos._position)

            for asset_key, asset_value in asset_pos.items():
                self.assertEqual(asset_value, res_pos._position[k][asset_key])

    def test_deserialize_asread_only(self):
        p_dict = OrderedDict()
        dm = MagicMock(DataManager())
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        p = Position(dm, position_dict=p_dict, decision_time_shift=1)
        self.assertEqual(p._position, p_dict)
        serialized = p.serialize()

        res_pos = Position.deserialize(serialized, dm, as_readonly=True)
        self.assertEqual(type(res_pos), PositionReadOnlyView)
        self.assertEqual({'decision_time_shift': 1}, res_pos.kwargs)
        self.assertEqual(1, res_pos.decision_time_shift)

        for k, asset_pos in p_dict.items():
            self.assertTrue(k in res_pos._position)

            for asset_key, asset_value in asset_pos.items():
                self.assertEqual(asset_value, res_pos._position[k][asset_key])

    def test__calc_transactions(self):
        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.ticksize = 1.0
            mock_instrument_info.tickvalue = 1.0

            with patch('tmqrfeed.contracts.ContractBase.price') as mock_price:
                positions = OrderedDict()
                fut = ContractBase("US.S.AAPL")
                fut.ctype = 'F'

                opt1 = ContractBase("US.C.AAPL")
                opt1.ctype = 'C'

                opt2 = ContractBase("US.P.AAPL")
                opt2.ctype = 'P'
                positions = OrderedDict()

                positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
                positions[datetime(2011, 1, 2)] = {
                    fut: (101, 102, 1.0),
                    opt1: (201, 202, 3.0),
                    opt2: (301, 302, -4.0)
                }
                positions[datetime(2011, 1, 3)] = {
                    fut: (102, 103, 1.0),
                    opt1: (202, 203, 0.0)
                }

                mock_price.return_value = (501, 502)

                dm = MagicMock(DataManager())
                # dm.price_get.return_value = (501, 502)
                dm.costs_get.return_value = 0.0

                p = Position(dm)

                # First transaction
                trans = p._calc_transactions(datetime(2011, 1, 1), positions[datetime(2011, 1, 1)], None)
                self.assertEqual(1, len(trans))
                self.assertEqual({fut: (100, 101, 2, 0.0, 0.0, 0.0)}, trans)

                trans = p._calc_transactions(datetime(2011, 1, 1), positions[datetime(2011, 1, 2)],
                                             positions[datetime(2011, 1, 1)])
                self.assertEqual(3, len(trans))
                self.assertEqual({fut: (101, 102, -1, 2.0, 2.0, 0.0),
                                  opt1: (201, 202, 3, 0.0, 0.0, 0.0),
                                  opt2: (301, 302, -4, 0.0, 0.0, 0.0)
                                  }, trans)

                trans = p._calc_transactions(datetime(2011, 1, 2), positions[datetime(2011, 1, 3)],
                                             positions[datetime(2011, 1, 2)])
                self.assertEqual(3, len(trans))
                self.assertEqual({fut: (102, 103, 0.0, 1.0, 1.0, 0.0),
                                  opt1: (202, 203, -3.0, 3.0, 3.0, 0.0),
                                  opt2: (501, 502, 4.0, -200 * 4, -200 * 4, 0.0)
                                  }, trans)

    def test__calc_transactions_handle_closed_positions(self):
        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.ticksize = 1.0
            mock_instrument_info.tickvalue = 1.0

            with patch('tmqrfeed.contracts.ContractBase.price') as mock_price:
                positions = OrderedDict()
                fut = ContractBase("US.S.AAPL")
                fut.ctype = 'F'

                opt1 = ContractBase("US.C.AAPL")
                opt1.ctype = 'C'

                opt2 = ContractBase("US.P.AAPL")
                opt2.ctype = 'P'
                positions = OrderedDict()

                positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
                positions[datetime(2011, 1, 2)] = {
                    fut: (101, 102, 1.0),
                    opt1: (201, 202, 3.0),
                    opt2: (301, 302, -4.0)
                }
                positions[datetime(2011, 1, 3)] = {
                    fut: (102, 103, 1.0),
                    opt1: (202, 203, 0.0)
                }

                mock_price.return_value = (501, 502)

                dm = MagicMock(DataManager())
                # dm.price_get.return_value = (501, 502)
                dm.costs_get.return_value = 0.0

                p = Position(dm)

                trans = p._calc_transactions(datetime(2011, 1, 2), positions[datetime(2011, 1, 3)],
                                             positions[datetime(2011, 1, 2)])

                _pos = positions[datetime(2011, 1, 3)]
                self.assertEqual(3, len(_pos))
                self.assertEqual({
                                     fut: (102, 103, 1.0),
                                     opt1: (202, 203, 0.0),
                                     opt2: (501, 502, 0.0)
                                 }, _pos)



    def test__calc_transactions_asset_expired_error(self):
        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.ticksize = 1.0
            mock_instrument_info.tickvalue = 1.0

            with patch('tmqrfeed.contracts.ContractBase.price') as mock_price:
                positions = OrderedDict()
                fut = ContractBase("US.S.AAPL")
                fut.ctype = 'F'

                opt1 = ContractBase("US.C.AAPL")
                opt1.ctype = 'C'

                opt2 = ContractBase("US.P.AAPL")
                opt2.ctype = 'P'
                positions = OrderedDict()

                positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
                positions[datetime(2011, 1, 2)] = {}
                positions[datetime(2011, 1, 3)] = {fut: (102, 103, 1.0), opt1: (202, 203, 0.0)}

                def price_side_effect(date):
                    raise AssetExpiredError()

                mock_price.side_effect = price_side_effect

                dm = MagicMock(DataManager())
                # dm.price_get.return_value = (501, 502)
                dm.costs_get.return_value = 0.0

                p = Position(dm)

                # In case when position is about expired and we don't have the price data at this point
                # Use previous position price to close transaction (trade off)
                trans = p._calc_transactions(datetime(2011, 1, 2), positions[datetime(2011, 1, 2)],
                                             positions[datetime(2011, 1, 1)])
                #
                # 2017-07-11 New behavior added
                #   Already expired positions doesn't take place in processed equity
                #   They are skipped, to prevent code failure in other parts of the framework
                self.assertEqual(0, len(trans))


    def test__transactions_stats(self):
        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            positions = OrderedDict()
            fut = ContractBase("US.S.AAPL")
            fut.ctype = 'F'

            opt1 = ContractBase("US.C.AAPL")
            opt1.ctype = 'C'

            opt2 = ContractBase("US.P.AAPL")
            opt2.ctype = 'P'

            positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
            positions[datetime(2011, 1, 2)] = {
                fut: (101, 102, 1.0),
                opt1: (201, 202, 3.0),
                opt2: (301, 302, -4.0)
            }

            dm = MagicMock(DataManager())
            dm.price_get.return_value = (501, 502)

            def costs_side(asset, qty):
                return abs(qty) * -1.0

            dm.costs_get.side_effect = costs_side

            p = Position(dm)

            mock_instrument_info.ticksize = 1.0
            mock_instrument_info.tickvalue = 1.0

            trans = p._calc_transactions(datetime(2011, 1, 1), positions[datetime(2011, 1, 2)],
                                         positions[datetime(2011, 1, 1)])
            self.assertEqual(3, len(trans))
            self.assertEqual({fut: (101, 102, -1.0, 1.0, 1.0, -1.0),
                              opt1: (201, 202, 3.0, -3.0, -3.0, -3.0),
                              opt2: (301, 302, -4.0, -4.0, -4.0, -4.0)
                              }, trans)


            stats = p._transactions_stats(trans)

            self.assertEqual({
                'pnl_change_decision': -6.0,
                'pnl_change_execution': -6.0,
                'ncontracts_executed': 1.0,
                'noptions_executed': 7.0,
                'costs': -8.0
            }, stats)

    def test_get_pnl_series(self):
        positions = OrderedDict()
        fut = MagicMock(ContractBase("US.S.AAPL"))
        fut.ctype = 'F'
        fut.price.return_value = (501, 502)

        opt1 = MagicMock(ContractBase("US.C.AAPL"))
        opt1.ctype = 'C'
        opt1.price.return_value = (501, 502)

        opt2 = MagicMock(ContractBase("US.P.AAPL"))
        opt2.ctype = 'P'
        opt2.price.return_value = (501, 502)

        positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
        positions[datetime(2011, 1, 2)] = {
            fut: (101, 102, 1.0),
            opt1: (201, 202, 3.0),
            opt2: (301, 302, -4.0)
        }
        positions[datetime(2011, 1, 3)] = {fut: (102, 103, 1.0), opt1: (202, 203, 0.0)}

        dm = MagicMock(DataManager())
        dm.price_get.return_value = (501, 502)

        p = Position(dm, position_dict=positions)
        df = p.get_pnl_series()
        self.assertEqual(pd.DataFrame, type(df))
        self.assertEqual(3, len(df))

        for c in ['pnl_change_decision',
                  'pnl_change_execution',
                  'ncontracts_executed',
                  'noptions_executed',
                  'equity_decision',
                  'equity_execution',
                  'costs']:
            self.assertTrue(c in df, c)

        self.assertEqual('dt', df.index.name)
        self.assertTrue(np.all(df['equity_decision'] == df['pnl_change_decision'].cumsum()))
        self.assertTrue(np.all(df['equity_execution'] == df['pnl_change_execution'].cumsum()))

    def test_almost_expired_ratio(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        stk = ContractBase("US.S.AAPL", dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        opt2 = OptionContract('US.P.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        fut = FutureContract('US.F.CL.M83.110121', dm)

        self.assertEqual(0, p.almost_expired_ratio(datetime(2011, 1, 1), 0, 0))

        p.add_transaction(dt, opt, 1)
        p.add_transaction(dt, opt2, 1)
        p.add_transaction(dt, fut, 1)

        self.assertEqual(0, p.almost_expired_ratio(datetime(2011, 1, 1), 0, 0))

        dt2 = datetime(2011, 1, 20)
        p.keep_previous_position(dt2)
        self.assertEqual(0, p.almost_expired_ratio(dt2, 0, 0))

        dt2 = datetime(2011, 1, 21)
        p.keep_previous_position(dt2)
        self.assertEqual(1, p.almost_expired_ratio(dt2, 0, 0))

    def test_almost_expired_partial(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        stk = ContractBase("US.S.AAPL", dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        opt2 = OptionContract('US.P.F-ZB-H11-110322.110123@89.0', datamanager=dm)
        fut = FutureContract('US.F.CL.M83.110121', dm)

        p.add_transaction(dt, opt, 1)
        p.add_transaction(dt, opt2, 1)
        p.add_transaction(dt, fut, 1)

        self.assertEqual(0, p.almost_expired_ratio(datetime(2011, 1, 1), 0, 0))

        dt2 = datetime(2011, 1, 21)
        p.keep_previous_position(dt2)
        self.assertEqual(2.0 / 3.0, p.almost_expired_ratio(dt2, 0, 0))
        self.assertRaises(ArgumentError, p.almost_expired_ratio, dt2, -1, 0)
        self.assertRaises(ArgumentError, p.almost_expired_ratio, dt2, 0, -1)

    def test_almost_expired_after_closed(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        stk = ContractBase("US.S.AAPL", dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        fut = FutureContract('US.F.CL.M83.110121', dm)

        p.add_transaction(dt, opt, 1)
        p.add_transaction(dt, fut, 1)

        self.assertEqual(0, p.almost_expired_ratio(datetime(2011, 1, 1), 0, 0))

        dt2 = datetime(2011, 1, 21)
        p.keep_previous_position(dt2)
        self.assertEqual(1, p.almost_expired_ratio(dt2, 0, 0))
        p.close(dt2)
        self.assertEqual(0, p.almost_expired_ratio(dt2, 0, 0))

    def test_almost_expired_default_rollover_days_before(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.rollover_days_before_options = 0
            mock_instrument_info.rollover_days_before = 0

            stk = ContractBase("US.S.AAPL", dm)
            opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            fut = FutureContract('US.F.CL.M83.110121', dm)

            p.add_transaction(dt, opt, 1)
            p.add_transaction(dt, fut, 1)

            self.assertEqual(0, p.almost_expired_ratio(datetime(2011, 1, 1)))

            dt2 = datetime(2011, 1, 21)
            p.keep_previous_position(dt2)
            self.assertEqual(1, p.almost_expired_ratio(dt2))

    def test_repr(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.rollover_days_before_options = 0
            mock_instrument_info.rollover_days_before = 0

            stk = ContractBase("US.S.AAPL", dm)
            opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            fut = FutureContract('US.F.CL.M83.110121', dm)

            p.add_transaction(dt, opt, 1)
            p.add_transaction(dt, fut, 1)

            repr_text = p.__repr__()
            for txt in ['Asset', 'DecisionPx', 'ExecPx', 'Qty', 'US.C.F-ZB-H11-110322.110121@89.0',
                        'US.F.CL.M83.110121']:
                self.assertTrue(txt in repr_text)

    def test_repr_position_not_found_exception(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)

        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            self.assertEqual('<Empty position>', p.__repr__())

    def test_str(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        dt = datetime(2011, 1, 1)

        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.rollover_days_before_options = 0
            mock_instrument_info.rollover_days_before = 0

            stk = ContractBase("US.S.AAPL", dm)
            opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            fut = FutureContract('US.F.CL.M83.110121', dm)

            p.add_transaction(dt, opt, 1)
            p.add_transaction(dt, fut, 1)

            repr_text = p.__repr__()

            self.assertEqual(repr_text, str(p))



    def test_eq(self):
        dm = MagicMock(DataManager())
        dm.price_get.return_value = (1.0, 2.0)

        p = Position(dm)
        p2 = Position(dm)
        p3 = Position(dm)
        dt = datetime(2011, 1, 1)

        with patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            mock_instrument_info.rollover_days_before_options = 0
            mock_instrument_info.rollover_days_before = 0

            stk = ContractBase("US.S.AAPL", dm)
            opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            fut = FutureContract('US.F.CL.M83.110121', dm)

            p.add_transaction(dt, opt, 1)
            p.add_transaction(dt, fut, 1)

            p2.add_transaction(dt, opt, 1)
            p2.add_transaction(dt, fut, 1)

            p3.add_transaction(dt, opt, 1)

            self.assertEqual(p, p2)
            self.assertNotEqual(p, p3)
            self.assertNotEqual('test', p)

    def test_delta(self):
        dm = MagicMock(DataManager())
        positions = OrderedDict()
        fut = MagicMock(ContractBase("US.S.AAPL"))
        fut.ctype = 'F'
        fut.price.return_value = (501, 502)
        fut.delta.return_value = 1.0

        opt1 = MagicMock(ContractBase("US.C.AAPL"))
        opt1.ctype = 'C'
        opt1.price.return_value = (501, 502)
        opt1.delta.return_value = 1.0

        opt2 = MagicMock(ContractBase("US.P.AAPL"))
        opt2.ctype = 'P'
        opt2.price.return_value = (501, 502)
        opt2.delta.return_value = -1.0

        positions[datetime(2011, 1, 2)] = {
            fut: (101, 102, 1.0),
            opt1: (201, 202, 3.0),
            opt2: (301, 302, -4.0)
        }

        p = Position(dm, positions)

        self.assertEqual(p.delta(datetime(2011, 1, 2)),
                         1 * 1 + 1 * 3 + -1 * -4
                         )

    def test_last_transaction_date(self):
        import pytz
        tz = pytz.UTC
        dm = MagicMock(DataManager())
        positions = OrderedDict()
        fut = ContractBase("US.S.AAPL")
        fut.ctype = 'F'

        opt1 = ContractBase("US.C.AAPL")
        opt1.ctype = 'C'

        opt2 = ContractBase("US.P.AAPL")
        opt2.ctype = 'P'
        positions = OrderedDict()

        positions[datetime(2011, 1, 1)] = {fut: (100, 101, 2)}
        positions[datetime(2011, 1, 2)] = {
            fut: (101, 102, 1.0),
            opt1: (201, 202, 3.0),
            opt2: (301, 302, -4.0)
        }
        positions[datetime(2011, 1, 3)] = {
            fut: (102, 103, 1.0),
            opt1: (202, 203, 0.0)
        }
        positions[datetime(2011, 1, 4)] = {
            fut: (102, 103, 1.0),
        }
        positions[datetime(2011, 1, 5)] = {
        }

        empty_pos = Position(dm)
        self.assertEqual(QDATE_MIN, empty_pos.last_transaction_date(datetime(2011, 1, 4)))

        self.assertEqual(QDATE_MIN.replace(tzinfo=tz), empty_pos.last_transaction_date(datetime(2011, 1, 4, tzinfo=tz)))

        p = Position(dm, positions)
        self.assertEqual(p.last_transaction_date(datetime(2011, 1, 4)), datetime(2011, 1, 3))

        p = Position(dm, positions)
        self.assertEqual(p.last_transaction_date(datetime(2011, 1, 3)), datetime(2011, 1, 3))

        p = Position(dm, positions)
        self.assertEqual(p.last_transaction_date(datetime(2011, 1, 1)), datetime(2011, 1, 1))

        p = Position(dm, positions)
        self.assertEqual(p.last_transaction_date(datetime(2011, 1, 5)), datetime(2011, 1, 5))
