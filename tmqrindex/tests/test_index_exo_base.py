import unittest
from tmqrfeed.manager import DataManager
from tmqrindex.index_exo_base import IndexEXOBase
from unittest.mock import patch, MagicMock
from tmqr.errors import *
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from datetime import datetime
import pytz
from tmqrfeed import Costs
from tmqrfeed.assetsession import AssetSession
import pandas as pd
import numpy as np
from tmqrfeed.position import Position


class IndexEXOBaseTestCase(unittest.TestCase):
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

    def test_init(self):
        dm = MagicMock(DataManager)()
        idx = IndexEXOBase(dm, instrument='CL')

        self.assertEqual(idx.instrument, 'CL')
        self.assertEqual(idx.costs_futures, 0.0)
        self.assertEqual(idx.costs_options, 0.0)
        self.assertEqual(idx.dm, dm)

    def test_keywords_and_defaults(self):
        dm = MagicMock(DataManager)()
        context = {
            'costs_futures': 1,
            'costs_options': 3
        }
        idx = IndexEXOBase(dm, instrument='CL', context=context)

        self.assertEqual(idx.instrument, 'CL')
        self.assertEqual(idx.costs_futures, 1)
        self.assertEqual(idx.costs_options, 3)
        self.assertEqual(idx.dm, dm)

    def test_setup(self):
        dm = MagicMock(DataManager)()
        context = {
            'costs_futures': 1,
            'costs_options': 3
        }
        idx = IndexEXOBase(dm, instrument='US.CL', context=context)

        idx.setup()

        self.assertEqual(dm.session_set.call_args[0][0], 'US.CL')

        self.assertEqual(dm.series_primary_set.call_args[0][0], QuoteContFut)
        self.assertEqual(dm.series_primary_set.call_args[0][1], 'US.CL')
        self.assertEqual(dm.series_primary_set.call_args[1]['timeframe'], "D")
        self.assertEqual(dm.series_primary_set.call_args[1]['decision_time_shift'], idx.decision_time_shift)

        self.assertEqual(dm.costs_set.call_args[0][0], 'US')
        self.assertEqual(type(dm.costs_set.call_args[0][1]), Costs)
        self.assertEqual(dm.costs_set.call_args[0][1].per_contract, 1)
        self.assertEqual(dm.costs_set.call_args[0][1].per_option, 3)

    def test_setup_custom_session(self):
        dm = MagicMock(DataManager)()
        context = {
            'costs_futures': 1,
            'costs_options': 3
        }
        idx = IndexEXOBase(dm, instrument='US.CL', context=context, session=self.sess)
        idx.setup()

        self.assertEqual(dm.session_set.call_args[1]['session_instance'], self.sess)

    def test_empty_methods(self):
        dm = MagicMock(DataManager)()
        idx = IndexEXOBase(dm, instrument='US.CL')

        self.assertEqual(None, idx.calc_exo_logic())
        self.assertEqual(None, idx.manage_position(None, None, None))
        self.assertEqual(None, idx.construct_position(None, None, None))

    def test_index_name(self):
        dm = MagicMock(DataManager)()
        idx = IndexEXOBase(dm, instrument='US.CL')

        self.assertRaises(SettingsError, idx.__getattribute__, 'index_name')
        idx._index_name = 'TEST_EXO'
        self.assertEqual('US.CL_TEST_EXO', idx.index_name)

    def test_set_data_and_position(self):
        dm = MagicMock(DataManager)()

        quote_index = [datetime(2011, 1, 1), datetime(2011, 1, 2)]
        dm.quotes.return_value = pd.DataFrame({'exo': [1, 2]}, index=quote_index)

        with patch('tmqrindex.index_exo_base.Position') as mock_position_class:
            with patch('tmqrindex.index_exo_base.IndexEXOBase.calc_exo_logic') as mock_index_calc_exo_logic:
                with patch('tmqrindex.index_exo_base.IndexEXOBase.manage_position') as mock_index_manage_position:
                    with patch(
                            'tmqrindex.index_exo_base.IndexEXOBase.construct_position') as mock_index_construct_position:
                        mock_pos = MagicMock(Position)()
                        mock_pos.has_position.return_value = False
                        mock_position_class.return_value = mock_pos
                        logic_df = pd.DataFrame({'metric': [1]}, index=[datetime(2011, 1, 1)])
                        mock_index_calc_exo_logic.return_value = logic_df

                        idx = IndexEXOBase(dm, instrument='US.CL')
                        idx.set_data_and_position()

                        self.assertEqual(dm, mock_position_class.call_args[0][0])
                        self.assertEqual(5, mock_position_class.call_args[1]['decision_time_shift'])

                        self.assertEqual(1, mock_index_calc_exo_logic.call_count)

                        # Check internal loop
                        self.assertEqual(2, mock_pos.keep_previous_position.call_count)
                        for i, dt in enumerate(quote_index):

                            self.assertEqual(dt, mock_pos.keep_previous_position.call_args_list[i][0][0])

                        # manage positions
                        self.assertEqual(2, mock_index_construct_position.call_count)
                        self.assertEqual(2, mock_index_manage_position.call_count)
                        # Day 1
                        self.assertEqual(quote_index[0], mock_index_manage_position.call_args_list[0][0][0])
                        self.assertEqual(mock_pos, mock_index_manage_position.call_args_list[0][0][1])
                        self.assertEqual(True, np.all(
                            logic_df.loc[datetime(2011, 1, 1)] == mock_index_manage_position.call_args_list[0][0][2]))

                        self.assertEqual(quote_index[0], mock_index_construct_position.call_args_list[0][0][0])
                        self.assertEqual(mock_pos, mock_index_construct_position.call_args_list[0][0][1])
                        self.assertEqual(True, np.all(
                            logic_df.loc[datetime(2011, 1, 1)] == mock_index_construct_position.call_args_list[0][0][
                                2]))

                        # Day 2
                        self.assertEqual(quote_index[1], mock_index_manage_position.call_args_list[1][0][0])
                        self.assertEqual(mock_pos, mock_index_manage_position.call_args_list[1][0][1])
                        self.assertEqual(None, mock_index_manage_position.call_args_list[1][0][2])

                        self.assertEqual(quote_index[1], mock_index_construct_position.call_args_list[1][0][0])
                        self.assertEqual(mock_pos, mock_index_construct_position.call_args_list[1][0][1])
                        self.assertEqual(None, mock_index_construct_position.call_args_list[1][0][2])

                        #
                        # make sure that index data is set
                        #
                        self.assertEqual(idx.data, mock_pos.get_pnl_series())
                        self.assertEqual(idx.position, mock_pos)

    def test_set_data_and_position_error_chainnotfound(self):
        dm = MagicMock(DataManager)()

        quote_index = [datetime(2011, 1, 1), datetime(2011, 1, 2)]
        dm.quotes.return_value = pd.DataFrame({'exo': [1, 2]}, index=quote_index)

        with patch('tmqrindex.index_exo_base.Position') as mock_position_class:
            with patch('tmqrindex.index_exo_base.log') as mock_log:
                with patch('tmqrindex.index_exo_base.IndexEXOBase.manage_position') as mock_index_manage_position:
                    mock_pos = MagicMock(Position)()

                    def pos_keep_side_effect(dt):
                        raise ChainNotFoundError()

                    mock_pos.keep_previous_position.side_effect = pos_keep_side_effect
                    mock_position_class.return_value = mock_pos

                    idx = IndexEXOBase(dm, instrument='US.CL')
                    idx.set_data_and_position()
                    self.assertEqual(True, mock_log.error.called)
                    self.assertEqual(False, mock_index_manage_position.called)

    def test_set_data_and_position_error_quote_not_found(self):
        dm = MagicMock(DataManager)()

        quote_index = [datetime(2011, 1, 1), datetime(2011, 1, 2)]
        dm.quotes.return_value = pd.DataFrame({'exo': [1, 2]}, index=quote_index)

        with patch('tmqrindex.index_exo_base.Position') as mock_position_class:
            with patch('tmqrindex.index_exo_base.log') as mock_log:
                with patch('tmqrindex.index_exo_base.IndexEXOBase.manage_position') as mock_index_manage_position:
                    mock_pos = MagicMock(Position)()

                    def pos_keep_side_effect(dt):
                        raise QuoteNotFoundError()

                    mock_pos.keep_previous_position.side_effect = pos_keep_side_effect
                    mock_position_class.return_value = mock_pos

                    idx = IndexEXOBase(dm, instrument='US.CL')
                    idx.set_data_and_position()
                    self.assertEqual(True, mock_log.error.called)
                    self.assertEqual(False, mock_index_manage_position.called)

    def test_set_data_and_position_error_other_unhandled(self):
        dm = MagicMock(DataManager)()

        quote_index = [datetime(2011, 1, 1), datetime(2011, 1, 2)]
        dm.quotes.return_value = pd.DataFrame({'exo': [1, 2]}, index=quote_index)

        with patch('tmqrindex.index_exo_base.Position') as mock_position_class:
            with patch('tmqrindex.index_exo_base.log') as mock_log:
                with patch('tmqrindex.index_exo_base.IndexEXOBase.manage_position') as mock_index_manage_position:
                    mock_pos = MagicMock(Position)()

                    def pos_keep_side_effect(dt):
                        raise TMQRError()

                    mock_pos.keep_previous_position.side_effect = pos_keep_side_effect
                    mock_position_class.return_value = mock_pos

                    idx = IndexEXOBase(dm, instrument='US.CL')
                    self.assertRaises(TMQRError, idx.set_data_and_position)
