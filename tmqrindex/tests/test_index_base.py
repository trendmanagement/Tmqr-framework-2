import unittest
from tmqrindex.index_base import IndexBase, INSTRUMENT_NA
from tmqrindex.index_contfut import IndexContFut
from tmqrfeed.manager import DataManager
from unittest.mock import MagicMock, patch
import pandas as pd
from tmqr.errors import *
from tmqrfeed.position import Position, PositionReadOnlyView
from datetime import datetime, timedelta
from tmqrfeed.contracts import *
from collections import OrderedDict
import pickle
import lz4
import numpy as np
from tmqrfeed.assetsession import AssetSession
import pytz


class IndexBaseTestCase(unittest.TestCase):
    def setUp(self):
        session_list = [
            # Default session
            {
                'decision': '10:40',  # Decision time (uses 'tz' param time zone!)
                'dt': datetime(1900, 12, 31),  # Actual date of default session start
                'execution': '10:45',  # Execution time (uses 'tz' param time zone!)
                'start': '03:32'  # Start of the session time (uses 'tz' param time zone!)
            },
        ]

        tz = pytz.timezone("UTC")
        self.sess = AssetSession(session_list, tz)

    def test_instrument_na(self):
        self.assertEqual(INSTRUMENT_NA, "N/A")

    def test_defaults(self):
        self.assertEqual(INSTRUMENT_NA, IndexBase._instrument)
        self.assertEqual("IndexBase", IndexBase._index_name)
        self.assertEqual("Short description of the index values or position", IndexBase._description_short)
        long_desc = "Long description of the index, could include description of the data fields meanings"

        self.assertEqual(long_desc, IndexBase._description_long)

    def test_init(self):
        dm = MagicMock()

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = MagicMock()
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition,
                        session=self.sess)

        self.assertEqual(kwinstrument, idx.instrument)
        self.assertEqual(kwcontext, idx.context)
        self.assertEqual(kwdata, idx.data)
        self.assertEqual(kwposition, idx.position)
        self.assertEqual(self.sess, idx.session)

        self.assertRaises(ArgumentError, IndexBase, dm, instrument=kwinstrument, context=kwcontext, data=kwdata,
                          position=kwposition,
                          session='wrong')

    def test_init_defaults(self):
        dm = MagicMock()

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = MagicMock()
        kwposition = MagicMock()

        idx = IndexBase(dm)

        self.assertEqual(INSTRUMENT_NA, idx.instrument)
        self.assertEqual({}, idx.context)
        self.assertEqual(pd.DataFrame, type(idx.data))
        self.assertEqual(None, idx.position)

        self.assertEqual('IndexBase', idx.index_name)

    def test_decision_time_shift(self):
        dm = MagicMock()

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = MagicMock()
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)
        self.assertEqual(5, idx.decision_time_shift)

        kwcontext = {'decision_time_shift': 3}
        kwdata = MagicMock()
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)
        self.assertEqual(3, idx.decision_time_shift)

        kwcontext = {'decision_time_shift': -3}
        kwdata = MagicMock()
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)
        self.assertRaises(SettingsError, idx.__getattribute__, 'decision_time_shift')

    def test_fields(self):
        dm = MagicMock()

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, position=kwposition)

        self.assertEqual([], idx.fields)

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        self.assertEqual(['a', 'b'], idx.fields)

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = None
        kwposition = MagicMock()

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)
        self.assertEqual([], idx.fields)

    def test_serialize(self):
        dm = MagicMock()
        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, some_kwarg=1.0)

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        serialized_idx = idx.serialize()

        self.assertEqual(9, len(serialized_idx))
        self.assertEqual(kwcontext, serialized_idx['context'])
        self.assertEqual('TEST', serialized_idx['instrument'])
        self.assertEqual(IndexBase._description_long, serialized_idx['description_long'])
        self.assertEqual(IndexBase._description_short, serialized_idx['description_short'])
        self.assertEqual(['a', 'b'], serialized_idx['fields'])
        self.assertEqual('TEST_IndexBase', serialized_idx['name'])
        self.assertEqual(pd.DataFrame, type(pickle.loads(lz4.block.decompress(serialized_idx['data']))))
        self.assertTrue('data' in serialized_idx['position'])
        self.assertTrue('kwargs' in serialized_idx['position'])
        self.assertTrue('session' in serialized_idx)

    def test_deserialize(self):
        dm = MagicMock(DataManager)()
        dm.session_get.return_value = self.sess
        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, some_kwarg=1.0)

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        serialized_idx = idx.serialize()

        self.assertRaises(ArgumentError, IndexContFut.deserialize, dm, serialized_idx)

        idx2 = IndexBase.deserialize(dm, serialized_idx, as_readonly=False)

        self.assertEqual(True, np.all(idx2.data == kwdata))
        self.assertEqual(kwcontext, idx2.context)
        self.assertEqual(kwinstrument, idx2.instrument)
        self.assertEqual(kwposition.get_net_position(datetime(2011, 1, 1)),
                         idx2.position.get_net_position(datetime(2011, 1, 1)))

    def test_deserialize_any_to_index_base(self):
        dm = MagicMock(DataManager)()
        dm.session_get.return_value = self.sess

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, some_kwarg=1.0)

        idx = IndexContFut(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        serialized_idx = idx.serialize()
        IndexContFut.deserialize(dm, serialized_idx)
        idx2 = IndexBase.deserialize(dm, serialized_idx)

        self.assertEqual('TEST_ContFutEOD', idx2.index_name)
        self.assertEqual(IndexContFut._description_short, idx2._description_short)
        self.assertEqual(IndexContFut._description_long, idx2._description_long)

    def test_deserialize_readonly_index(self):
        dm = MagicMock(DataManager)()
        dm.session_get.return_value = self.sess
        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ],
            index=[datetime(2011, 1, 1, 12, 40), datetime(2011, 1, 2, 12, 40)]
        )

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1, 12, 40)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, decision_time_shift=5)

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        serialized_idx = idx.serialize()

        idx2 = IndexBase.deserialize(dm, serialized_idx, as_readonly=True)

        self.assertEqual(PositionReadOnlyView, type(idx2.position))

        self.assertEqual(kwposition.get_net_position(datetime(2011, 1, 1, 12, 40)),
                         idx2.position.get_net_position(datetime(2011, 1, 1, 12, 45)))

        self.assertTrue(
            np.all(pd.Series([datetime(2011, 1, 1, 12, 45), datetime(2011, 1, 2, 12, 45)]) == idx2.data.index))

        # Check that position asset has DataManager instance initiated
        p = idx2.position.get_net_position(datetime(2011, 1, 1, 12, 45))
        for asset, pos_rec in p.items():
            self.assertEqual(dm, asset.dm)

    def test_deserialize_readonly_index_fail_to_call_methods(self):
        dm = MagicMock(DataManager)()
        dm.session_get.return_value = self.sess
        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ],
            index=[datetime(2011, 1, 1, 12, 40), datetime(2011, 1, 2, 12, 40)]
        )

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1, 12, 40)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, decision_time_shift=5)

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)

        serialized_idx = idx.serialize()

        idx2 = IndexBase.deserialize(dm, serialized_idx, as_readonly=True)

        self.assertEqual(True, idx2.as_readonly)

        self.assertRaises(IndexReadOnlyError, idx2.run)
        self.assertRaises(IndexReadOnlyError, idx2.save)


    def test_save_load_realdb(self):
        dm = DataManager()
        dm.session_set(session_instance=self.sess)

        kwinstrument = 'TEST'
        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, decision_time_shift=5)

        idx = IndexBase(dm, instrument=kwinstrument, context=kwcontext, data=kwdata, position=kwposition)
        idx.save()

        idx2 = IndexBase.load(dm, kwinstrument)

        self.assertEqual(True, np.all(idx2.data == kwdata))
        self.assertEqual(kwcontext, idx2.context)
        self.assertEqual(kwinstrument, idx2.instrument)
        self.assertEqual(kwposition.get_net_position(datetime(2011, 1, 1)),
                         idx2.position.get_net_position(datetime(2011, 1, 1)))

        self.assertRaises(DataEngineNotFoundError, IndexContFut.load, dm, kwinstrument)

    def test_save_load_realdb_no_instrument_index(self):
        dm = DataManager()
        dm.session_set(session_instance=self.sess)

        kwcontext = {'TEST': True}
        kwdata = pd.DataFrame([
            {'a': 1, 'b': 2},
            {'a': 4, 'b': 5}
        ])

        p_dict = OrderedDict()
        asset = ContractBase("US.S.AAPL", dm)
        p_dict[datetime(2011, 1, 1)] = {asset: (100, 101, 2)}

        kwposition = Position(dm, position_dict=p_dict, decision_time_shift=5)

        idx = IndexBase(dm, context=kwcontext, data=kwdata, position=kwposition)
        idx.save()

        idx2 = IndexBase.load(dm)

        self.assertEqual(True, np.all(idx2.data == kwdata))
        self.assertEqual(kwcontext, idx2.context)
        self.assertEqual(kwposition.get_net_position(datetime(2011, 1, 1)),
                         idx2.position.get_net_position(datetime(2011, 1, 1)))

    def test_not_implemented(self):
        dm = MagicMock()
        idx = IndexBase(dm)

        self.assertRaises(NotImplementedError, idx.setup)
        self.assertRaises(NotImplementedError, idx.set_data_and_position)

    def test_run(self):
        dm = MagicMock()
        idx = IndexBase(dm)

        with patch('tmqrindex.index_base.IndexBase.setup') as mock_setup:
            with patch('tmqrindex.index_base.IndexBase.set_data_and_position') as mock_set_data_and_position:
                idx.run()
                self.assertTrue(mock_setup.called)
                self.assertTrue(mock_set_data_and_position.called)
