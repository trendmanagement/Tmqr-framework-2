import unittest
from unittest.mock import MagicMock, patch

from tmqr.errors import *
from tmqrfeed.contracts import *
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.manager import DataManager
from tmqrfeed.chains import *
from tmqrfeed.position import Position
from tmqrfeed.costs import Costs
import pytz
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.instrumentinfo import InstrumentInfo


class DataManagerTestCase(unittest.TestCase):
    def test_init(self):
        self.assertRaises(TypeError, DataManager, datafeed_cls=None)
        dm = DataManager()
        self.assertTrue(DataFeed, type(dm.datafeed))

        eng_settings = {'test': 'test'}
        dm = DataManager(data_engine_settings=eng_settings)
        self.assertEqual(dm.datafeed.data_engine_settings, eng_settings)

        self.assertEqual(None, dm._primary_quotes)
        self.assertEqual({}, dm._secondary_quotes)
        self.assertEqual(None, dm._primary_positions)
        self.assertEqual({}, dm._secondary_positions)

    def test_series_primary_set(self):
        dm = DataManager()
        with patch('tmqrfeed.quotes.quote_base.QuoteBase') as quote_mock:
            with patch.object(dm, 'series_check') as mock_dm_series_check:
                quote_mock.build.return_value = 'quotes', 'pos'
                # Creating mock for Quote class, constructor will return quote_mock
                quote_cls_mock = MagicMock()
                quote_cls_mock.return_value = quote_mock
                dm.series_primary_set(quote_cls_mock, 'test', kwtest=True)
                self.assertEqual('quotes', dm._primary_quotes)
                self.assertEqual('pos', dm._primary_positions)

                self.assertRaises(DataManagerError, dm.series_primary_set, quote_cls_mock, 'test', kwtest=True)
                self.assertTrue(quote_cls_mock.called)
                self.assertEqual(('test',), quote_cls_mock.call_args[0])
                self.assertEqual({'kwtest': True, 'datamanager': dm}, quote_cls_mock.call_args[1])
                self.assertTrue(quote_mock.build.called)

    def test_series_extra_set(self):
        dm = DataManager()
        with patch('tmqrfeed.quotes.quote_base.QuoteBase') as quote_mock:
            with patch.object(dm, 'series_check') as mock_dm_series_check:
                with patch.object(dm, 'series_align') as mock_dm_series_align:
                    quote_mock.build.return_value = 'quotes', 'pos'
                    mock_dm_series_align.return_value = 'quotes'

                    # Creating mock for Quote class, constructor will return quote_mock
                    quote_cls_mock = MagicMock()
                    quote_cls_mock.return_value = quote_mock
                    self.assertRaises(DataManagerError, dm.series_extra_set, 'name1', quote_cls_mock, 'test',
                                      kwtest=True)

                    dm.series_primary_set(quote_cls_mock, 'test', kwtest=True)

                    quote_cls_mock.reset_mock()
                    quote_mock.reset_mock()
                    dm.series_extra_set('name1', quote_cls_mock, 'test', kwtest=True)
                    self.assertTrue(mock_dm_series_check.called)
                    self.assertTrue(mock_dm_series_align.called)
                    self.assertTrue(quote_cls_mock.called)
                    self.assertEqual(('test',), quote_cls_mock.call_args[0])
                    self.assertEqual({'kwtest': True, 'datamanager': dm}, quote_cls_mock.call_args[1])
                    self.assertTrue(quote_mock.build.called)

                    self.assertEqual('quotes', dm._secondary_quotes['name1'])
                    self.assertEqual('pos', dm._secondary_positions['name1'])

                    self.assertRaises(DataManagerError, dm.series_extra_set, 'name1', quote_cls_mock, 'test',
                                      kwtest=True)

    def test_get_series(self):
        with patch('tmqrfeed.datafeed.DataFeed.get_raw_series') as mock_get_raw_series:
            dm = DataManager()
            dm.session_set('US.ES')
            mock_get_raw_series.return_value = True

            contract = FutureContract('US.F.ES.M83.830520', datamanager=dm)
            self.assertEqual(True, dm.series_get(contract))
            self.assertEqual(True, mock_get_raw_series.called)
            self.assertEqual('US.F.ES.M83.830520', mock_get_raw_series.call_args[0][0])
            kwargs = mock_get_raw_series.call_args[1]
            self.assertEqual(kwargs['source_type'], SRC_INTRADAY)
            self.assertEqual(kwargs['date_start'], QDATE_MIN)
            self.assertEqual(kwargs['date_end'], QDATE_MAX)
            self.assertEqual('US/Pacific', str(kwargs['timezone']))

    def test_get_series_with_kwargs(self):
        import pytz

        with patch('tmqrfeed.datafeed.DataFeed.get_raw_series') as mock_get_raw_series:
            dm = DataManager()
            dm.session_set('US.ES')

            mock_get_raw_series.return_value = True

            contract = FutureContract('US.F.ES.M83.830520', datamanager=dm)
            self.assertEqual(True, dm.series_get(contract,
                                                 date_start=QDATE_MAX,
                                                 date_end=QDATE_MIN,
                                                 session='sess',
                                                 timezone='another',
                                                 source_type='another_source'
                                                 ))
            self.assertEqual(True, mock_get_raw_series.called)

            self.assertEqual('US.F.ES.M83.830520', mock_get_raw_series.call_args[0][0])
            kwargs = mock_get_raw_series.call_args[1]
            self.assertEqual(kwargs['source_type'], 'another_source')
            self.assertEqual(kwargs['timezone'], pytz.timezone('US/Pacific'))
            self.assertEqual(kwargs['date_start'], QDATE_MAX)
            self.assertEqual(kwargs['date_end'], QDATE_MIN)

    def test_series_align_previous(self):
        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 30), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 30), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 30), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 30), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 30), 'px': 5},
        ]).set_index('dt')

        result = DataManager.series_align(primary, extra)
        target = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        self.assertTrue(np.all(result.index == target.index))
        self.assertTrue(np.all(result.px == target.px))

    def test_series_align_greater(self):
        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 50), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 50), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 50), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 50), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 50), 'px': 5},
        ]).set_index('dt')

        result = DataManager.series_align(primary, extra)
        target = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': pd.np.nan},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 4},
        ]).set_index('dt')

        self.assertTrue(np.all(result.index == target.index))
        self.assertTrue(np.allclose(result.px.values, target.px.values, equal_nan=True))

    def test_series_align_missing_beginning(self):
        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            # {'dt': datetime.datetime(2011, 1, 1, 10, 30), 'px': 1},
            # {'dt': datetime.datetime(2011, 1, 2, 10, 30), 'px': 2},
            # {'dt': datetime.datetime(2011, 1, 3, 10, 30), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        result = DataManager.series_align(primary, extra)
        target = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': pd.np.nan},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': pd.np.nan},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': pd.np.nan},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        self.assertTrue(np.all(result.index == target.index))
        self.assertTrue(np.allclose(result.px.values, target.px.values, equal_nan=True))

    def test_series_align_missing_end(self):
        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 30), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 30), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 30), 'px': 3},
            # {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            # {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        result = DataManager.series_align(primary, extra)
        target = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 3},
        ]).set_index('dt')

        self.assertTrue(np.all(result.index == target.index))
        self.assertTrue(np.allclose(result.px.values, target.px.values, equal_nan=True))

    def test_series_align_intraday(self):
        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 30), 'px': 10},
            {'dt': datetime.datetime(2011, 1, 1, 10, 31), 'px': 11},
            {'dt': datetime.datetime(2011, 1, 1, 10, 33), 'px': 12},

            {'dt': datetime.datetime(2011, 1, 2, 10, 32), 'px': 20},
            {'dt': datetime.datetime(2011, 1, 2, 10, 33), 'px': 21},
            {'dt': datetime.datetime(2011, 1, 2, 10, 34), 'px': 22},

            {'dt': datetime.datetime(2011, 1, 3, 10, 39), 'px': 30},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 31},
            {'dt': datetime.datetime(2011, 1, 3, 10, 41), 'px': 32},

            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        result = DataManager.series_align(primary, extra)
        target = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 12},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 22},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 31},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        self.assertTrue(np.all(result.index == target.index))
        self.assertTrue(np.allclose(result.px.values, target.px.values, equal_nan=True))

    def test_series_check(self):
        dm = DataManager()

        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 2, 1, 10, 30), 'px': 1},
            {'dt': datetime.datetime(2011, 2, 2, 10, 30), 'px': 2},
            {'dt': datetime.datetime(2011, 2, 3, 10, 30), 'px': 3},
            {'dt': datetime.datetime(2011, 2, 4, 10, 30), 'px': 4},
            {'dt': datetime.datetime(2011, 2, 5, 10, 30), 'px': 5},
        ]).set_index('dt')

        extra2 = pd.DataFrame([
            {'dt': datetime.datetime(2010, 2, 1, 10, 30), 'px': 1},
            {'dt': datetime.datetime(2010, 2, 2, 10, 30), 'px': 2},
            {'dt': datetime.datetime(2010, 2, 3, 10, 30), 'px': 3},
            {'dt': datetime.datetime(2010, 2, 4, 10, 30), 'px': 4},
            {'dt': datetime.datetime(2010, 2, 5, 10, 30), 'px': 5},
        ]).set_index('dt')

        self.assertEqual(False, dm.series_check('test', primary, None))
        self.assertEqual(False, dm.series_check('test', primary, pd.DataFrame()))
        self.assertEqual(False, dm.series_check('test', primary, []))
        self.assertEqual(False, dm.series_check('test', primary, extra))
        self.assertEqual(False, dm.series_check('test', primary, extra2))

    def test_series_check_delayed(self):
        dm = DataManager()

        primary = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 40), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 40), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 40), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 40), 'px': 4},
            {'dt': datetime.datetime(2011, 1, 5, 10, 40), 'px': 5},
        ]).set_index('dt')

        extra = pd.DataFrame([
            {'dt': datetime.datetime(2011, 1, 1, 10, 30), 'px': 1},
            {'dt': datetime.datetime(2011, 1, 2, 10, 30), 'px': 2},
            {'dt': datetime.datetime(2011, 1, 3, 10, 30), 'px': 3},
            {'dt': datetime.datetime(2011, 1, 4, 10, 30), 'px': 4},
            # {'dt': datetime.datetime(2011, 1, 5, 0, 30), 'px': 5},
        ]).set_index('dt')

        self.assertEqual(True, dm.series_check('test', primary, extra))


    def test_chains_get(self):
        def mock_opt_chain_find_sideeffect(date, opt_offset, **kwargs):
            return (opt_offset, kwargs.get('min_days', -1))

        with patch('tmqrfeed.datafeed.DataFeed.get_fut_chain') as mock_get_fut_chain:
            with patch('tmqrfeed.datafeed.DataFeed.get_option_chains') as mock_get_option_chains:
                dm = DataManager()

                # fut_chain = self.datafeed.get_fut_chain(instrument)
                mock_fut_chain = MagicMock(spec=FutureChain)
                mock_get_fut_chain.return_value = mock_fut_chain

                # err_count = 0
                # while True:
                #    try:
                #        fut = fut_chain.get_contract(date, fut_offset)
                mock_fut_contract = MagicMock()
                mock_fut_chain.get_contract.return_value = mock_fut_contract
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                mock_opt_chain_list = MagicMock(spec=OptionChainList)
                mock_get_option_chains.return_value = mock_opt_chain_list
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                mock_opt_chain_list.find.side_effect = mock_opt_chain_find_sideeffect

                #        return fut, option_chain
                #    except ChainNotFoundError as exc:
                #        err_count += 1
                #        fut_offset += 1
                #        opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                #        if err_count == error_limit:
                #            # Too many errors occurred, probably no data or very strict 'opt_offset' value
                #            raise ChainNotFoundError(f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}")

                result = dm.chains_options_get("TEST", datetime.datetime(2011, 1, 1))
                # fut_chain = self.datafeed.get_fut_chain(instrument)
                self.assertEqual(True, mock_get_fut_chain.called)
                self.assertEqual("TEST", mock_get_fut_chain.call_args[0][0])
                #        fut = fut_chain.get_contract(date, fut_offset)
                self.assertEqual(True, mock_fut_chain.get_contract.called)
                self.assertEqual((datetime.datetime(2011, 1, 1), 0), mock_fut_chain.get_contract.call_args[0])
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                self.assertEqual(True, mock_get_option_chains.called)
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                #        return fut, option_chain
                self.assertEqual(0, result[1][0])  # opt_offset
                self.assertEqual(2, result[1][1])  # min_days=opt_min_days
                self.assertEqual(mock_fut_contract, result[0])

    def test_chains_get_error_limit(self):
        def mock_opt_chain_find_sideeffect(date, opt_offset, **kwargs):
            if opt_offset == 0:
                raise ChainNotFoundError()

        with patch('tmqrfeed.datafeed.DataFeed.get_fut_chain') as mock_get_fut_chain:
            with patch('tmqrfeed.datafeed.DataFeed.get_option_chains') as mock_get_option_chains:
                dm = DataManager()

                # fut_chain = self.datafeed.get_fut_chain(instrument)
                mock_fut_chain = MagicMock(spec=FutureChain)
                mock_get_fut_chain.return_value = mock_fut_chain

                # err_count = 0
                # while True:
                #    try:
                #        fut = fut_chain.get_contract(date, fut_offset)
                mock_fut_contract = MagicMock()
                mock_fut_chain.get_contract.return_value = mock_fut_contract
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                mock_opt_chain_list = MagicMock(spec=OptionChainList)
                mock_get_option_chains.return_value = mock_opt_chain_list
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                mock_opt_chain_list.find.side_effect = mock_opt_chain_find_sideeffect

                #        return fut, option_chain
                #    except ChainNotFoundError as exc:
                #        err_count += 1
                #        fut_offset += 1
                #        opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                #        if err_count == error_limit:
                #            # Too many errors occurred, probably no data or very strict 'opt_offset' value
                #            raise ChainNotFoundError(f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}")

                self.assertRaises(ChainNotFoundError, dm.chains_options_get, "TEST", datetime.datetime(2011, 1, 1))

    def test_chains_get_next_future(self):
        def mock_opt_chain_find_sideeffect(date, opt_offset, **kwargs):
            return (opt_offset, kwargs.get('min_days', -1))

        def mock_fut_chain__get_contract_sideeffect(date, fut_offset):
            if fut_offset == 0:
                raise ChainNotFoundError()
            return f'FUT{fut_offset}'

        with patch('tmqrfeed.datafeed.DataFeed.get_fut_chain') as mock_get_fut_chain:
            with patch('tmqrfeed.datafeed.DataFeed.get_option_chains') as mock_get_option_chains:
                dm = DataManager()

                # fut_chain = self.datafeed.get_fut_chain(instrument)
                mock_fut_chain = MagicMock(spec=FutureChain)
                mock_get_fut_chain.return_value = mock_fut_chain

                # err_count = 0
                # while True:
                #    try:
                #        fut = fut_chain.get_contract(date, fut_offset)
                mock_fut_contract = MagicMock()
                mock_fut_chain.get_contract.side_effect = mock_fut_chain__get_contract_sideeffect
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                mock_opt_chain_list = MagicMock(spec=OptionChainList)
                mock_get_option_chains.return_value = mock_opt_chain_list
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                mock_opt_chain_list.find.side_effect = mock_opt_chain_find_sideeffect

                #        return fut, option_chain
                #    except ChainNotFoundError as exc:
                #        err_count += 1
                #        fut_offset += 1
                #        opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                #        if err_count == error_limit:
                #            # Too many errors occurred, probably no data or very strict 'opt_offset' value
                #            raise ChainNotFoundError(f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}")

                result = dm.chains_options_get("TEST", datetime.datetime(2011, 1, 1))
                # fut_chain = self.datafeed.get_fut_chain(instrument)
                self.assertEqual(True, mock_get_fut_chain.called)
                self.assertEqual("TEST", mock_get_fut_chain.call_args[0][0])
                #        fut = fut_chain.get_contract(date, fut_offset)
                self.assertEqual(True, mock_fut_chain.get_contract.called)
                self.assertEqual((datetime.datetime(2011, 1, 1), 1), mock_fut_chain.get_contract.call_args[0])
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                self.assertEqual(True, mock_get_option_chains.called)
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                #        return fut, option_chain
                self.assertEqual(0, result[1][0])  # opt_offset
                self.assertEqual(2, result[1][1])  # min_days=opt_min_days
                self.assertEqual('FUT1', result[0])

    def test_chains_get_kwargs(self):
        def mock_opt_chain_find_sideeffect(date, opt_offset, **kwargs):
            return (opt_offset, kwargs.get('min_days', -1))

        with patch('tmqrfeed.datafeed.DataFeed.get_fut_chain') as mock_get_fut_chain:
            with patch('tmqrfeed.datafeed.DataFeed.get_option_chains') as mock_get_option_chains:
                dm = DataManager()

                # fut_chain = self.datafeed.get_fut_chain(instrument)
                mock_fut_chain = MagicMock(spec=FutureChain)
                mock_get_fut_chain.return_value = mock_fut_chain

                # err_count = 0
                # while True:
                #    try:
                #        fut = fut_chain.get_contract(date, fut_offset)
                mock_fut_contract = MagicMock()
                mock_fut_chain.get_contract.return_value = mock_fut_contract
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                mock_opt_chain_list = MagicMock(spec=OptionChainList)
                mock_get_option_chains.return_value = mock_opt_chain_list
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                mock_opt_chain_list.find.side_effect = mock_opt_chain_find_sideeffect

                #        return fut, option_chain
                #    except ChainNotFoundError as exc:
                #        err_count += 1
                #        fut_offset += 1
                #        opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                #        if err_count == error_limit:
                #            # Too many errors occurred, probably no data or very strict 'opt_offset' value
                #            raise ChainNotFoundError(f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}")

                """
                :param kwargs: 
                - 'opt_offset' - option expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
                - 'opt_min_days' - minimal days count until option expiration (default: 2)
                - 'error_limit' - ChainNotFoundError error limit, useful to increase when you are trying to get far 'opt_offset' (default: 3)
                """
                result = dm.chains_options_get("TEST", datetime.datetime(2011, 1, 1), opt_offset=3,
                                               opt_min_days=4)
                # fut_chain = self.datafeed.get_fut_chain(instrument)
                self.assertEqual(True, mock_get_fut_chain.called)
                self.assertEqual("TEST", mock_get_fut_chain.call_args[0][0])
                #        fut = fut_chain.get_contract(date, fut_offset)
                self.assertEqual(True, mock_fut_chain.get_contract.called)
                self.assertEqual((datetime.datetime(2011, 1, 1), 0), mock_fut_chain.get_contract.call_args[0])
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                self.assertEqual(True, mock_get_option_chains.called)
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                #        return fut, option_chain
                self.assertEqual(3, result[1][0])  # opt_offset
                self.assertEqual(4, result[1][1])  # min_days=opt_min_days
                self.assertEqual(mock_fut_contract, result[0])

    def test_chains_get_kwargs_errors_checks(self):

        dm = DataManager()

        """
        :param kwargs: 
        - 'fut_offset' - future expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
        - 'opt_offset' - option expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
        - 'opt_min_days' - minimal days count until option expiration (default: 2)
        - 'error_limit' - ChainNotFoundError error limit, useful to increase when you are trying to get far 'opt_offset' (default: 3)
        """

        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1),
                          opt_offset=None)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1), opt_offset=0.2)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1), opt_offset=-1)

        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1),
                          opt_min_days=None)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1),
                          opt_min_days=0.2)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1),
                          opt_min_days=-1)

        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1),
                          error_limit=None)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1), error_limit=0)
        self.assertRaises(ArgumentError, dm.chains_options_get, "T.TEST", datetime.datetime(2011, 1, 1), error_limit=-1)

    def test_chains_get_option_offset_skipped(self):
        def mock_opt_chain_find_sideeffect(date, opt_offset, **kwargs):
            return (opt_offset, kwargs.get('min_days', -1))

        def mock_fut_chain__get_contract_sideeffect(date, fut_offset):
            if fut_offset == 0:
                raise ChainNotFoundError(option_offset_skipped=2)
            return f'FUT{fut_offset}'

        with patch('tmqrfeed.datafeed.DataFeed.get_fut_chain') as mock_get_fut_chain:
            with patch('tmqrfeed.datafeed.DataFeed.get_option_chains') as mock_get_option_chains:
                dm = DataManager()

                # fut_chain = self.datafeed.get_fut_chain(instrument)
                mock_fut_chain = MagicMock(spec=FutureChain)
                mock_get_fut_chain.return_value = mock_fut_chain

                # err_count = 0
                # while True:
                #    try:
                #        fut = fut_chain.get_contract(date, fut_offset)
                mock_fut_contract = MagicMock()
                mock_fut_chain.get_contract.side_effect = mock_fut_chain__get_contract_sideeffect
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                mock_opt_chain_list = MagicMock(spec=OptionChainList)
                mock_get_option_chains.return_value = mock_opt_chain_list
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                mock_opt_chain_list.find.side_effect = mock_opt_chain_find_sideeffect

                #        return fut, option_chain
                #    except ChainNotFoundError as exc:
                #        err_count += 1
                #        fut_offset += 1
                #        opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                #        if err_count == error_limit:
                #            # Too many errors occurred, probably no data or very strict 'opt_offset' value
                #            raise ChainNotFoundError(f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}")

                result = dm.chains_options_get("TEST", datetime.datetime(2011, 1, 1), opt_offset=6)
                # fut_chain = self.datafeed.get_fut_chain(instrument)
                self.assertEqual(True, mock_get_fut_chain.called)
                self.assertEqual("TEST", mock_get_fut_chain.call_args[0][0])
                #        fut = fut_chain.get_contract(date, fut_offset)
                self.assertEqual(True, mock_fut_chain.get_contract.called)
                self.assertEqual((datetime.datetime(2011, 1, 1), 1), mock_fut_chain.get_contract.call_args[0])
                #        opt_chain_list = self.datafeed.get_option_chains(fut)
                self.assertEqual(True, mock_get_option_chains.called)
                #        option_chain = opt_chain_list.find(opt_offset, min_days=opt_min_days)
                #        return fut, option_chain
                self.assertEqual(4, result[1][0])  # opt_offset
                self.assertEqual(2, result[1][1])  # min_days=opt_min_days
                self.assertEqual('FUT1', result[0])

    def test__price_get_set_cached(self):
        dm = DataManager()
        fut = FutureContract('US.F.CL.G12.120120', datamanager=dm)
        stk = ContractBase('US.S.AAPL', datamanager=dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        self.assertEqual(0, len(dm._cache_single_price))

        dt = datetime.datetime(2012, 1, 1)
        px_data = (1, 2)

        dm._price_set_cached(opt, dt, px_data)
        self.assertTrue(opt not in dm._cache_single_price)

        dm._price_set_cached(fut, dt, px_data)
        self.assertTrue(fut in dm._cache_single_price)
        self.assertEqual(px_data, dm._cache_single_price[fut][dt])

        dm._price_set_cached(stk, dt, px_data)
        self.assertTrue(stk in dm._cache_single_price)
        self.assertEqual(px_data, dm._cache_single_price[stk][dt])

        self.assertEqual((None, None), dm._price_get_cached(opt, dt))
        self.assertEqual(px_data, dm._price_get_cached(fut, dt))
        self.assertEqual(px_data, dm._price_get_cached(stk, dt))

    def test__price_get_positions_cached(self):
        dm = DataManager()
        dm._primary_positions = None
        stk = ContractBase('US.S.AAPL', datamanager=dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        fut = FutureContract('US.F.CL.G12.120120', datamanager=dm)
        dt = datetime.datetime(2012, 1, 1)

        # No cached positions
        self.assertEqual((None, None), dm._price_get_positions_cached(stk, dt))

        stk = ContractBase('US.S.AAPL', datamanager=dm)
        opt = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)

        dm._primary_positions = Position(dm, {
            datetime.datetime(2012, 1, 1): {
                stk: (0.1, 0.2, 1),
                opt: (1, 2, 4)
            }
        })

        dt = datetime.datetime(2012, 1, 1)
        # No date time
        self.assertEqual((None, None), dm._price_get_positions_cached(stk, datetime.datetime(2012, 1, 2)))

        # No asset
        self.assertEqual((None, None), dm._price_get_positions_cached(fut, datetime.datetime(2012, 1, 1)))

        # Existing assets
        self.assertEqual((0.1, 0.2), dm._price_get_positions_cached(stk, datetime.datetime(2012, 1, 1)))

        # Options in position are priced once again, and not applicable for caching
        self.assertEqual((None, None), dm._price_get_positions_cached(opt, datetime.datetime(2012, 1, 1)))

    def test__price_get(self):
        with patch('tmqrfeed.manager.DataManager._price_get_positions_cached') as mock__price_get_positions_cached:
            with patch('tmqrfeed.manager.DataManager._price_get_cached') as mock__price_get_cached:
                with patch('tmqrfeed.manager.DataManager._price_get_from_datafeed') as mock__price_get_from_datafeed:
                    with patch(
                            'tmqrfeed.manager.DataManager._price_set_cached') as mock__price_set_cached:
                        dm = DataManager()
                        stk = ContractBase('US.S.AAPL', datamanager=dm)
                        dt = datetime.datetime(2011, 1, 1)

                        mock__price_get_positions_cached.return_value = (1, 1)
                        # Fetch from _price_get_positions_cached

                        self.assertEqual((1, 1), dm.price_get(stk, dt))

                        mock__price_get_positions_cached.return_value = None, None
                        mock__price_get_cached.return_value = (2, 2)
                        self.assertEqual((2, 2), dm.price_get(stk, dt))

                        mock__price_get_positions_cached.return_value = None, None
                        mock__price_get_cached.return_value = None, None
                        mock__price_get_from_datafeed.return_value = (3, 3)
                        self.assertEqual((3, 3), dm.price_get(stk, dt))

                        self.assertTrue(mock__price_set_cached.called)
                        self.assertEqual((stk, dt, (3, 3)), mock__price_set_cached.call_args[0])

                        #
                        # handling bad NaN values from datafeed
                        #
                        mock__price_set_cached.reset_mock()
                        mock__price_get_positions_cached.return_value = None, None
                        mock__price_get_cached.return_value = None, None
                        mock__price_get_from_datafeed.return_value = (float('nan'), 3)
                        self.assertRaises(QuoteNotFoundError, dm.price_get, stk, dt)

                        mock__price_get_from_datafeed.return_value = (3, float('nan'))
                        self.assertRaises(QuoteNotFoundError, dm.price_get, stk, dt)

                        self.assertFalse(mock__price_set_cached.called)

                        #
                        # Asset expired error
                        #
                        fut = FutureContract('US.F.CL.G12.100120')
                        self.assertRaises(AssetExpiredError, dm.price_get, fut, dt)


    def test_costs_set_get(self):
        dm = DataManager()
        stk = ContractBase('US.S.AAPL', datamanager=dm)
        stk2 = ContractBase('RU.S.LKOH', datamanager=dm)

        cst = Costs(10, 20)
        dm.costs_set('US', cst)

        self.assertEqual(1, len(dm._cache_costs))
        self.assertEqual(dm._cache_costs['US'], cst)
        self.assertRaises(ArgumentError, dm.costs_set, 'US', 0.0)

        self.assertEqual(cst.calc_costs(stk, 10), dm.costs_get(stk, 10))

        self.assertRaises(CostsNotFoundError, dm.costs_get, stk2, 10)

    def test_quotes(self):
        dm = DataManager()

        self.assertRaises(QuoteNotFoundError, dm.quotes, None)

        prim_quotes = pd.DataFrame()
        sec_quotes = pd.DataFrame()

        dm._primary_quotes = prim_quotes

        self.assertEqual(id(prim_quotes), id(dm.quotes()))

        self.assertRaises(QuoteNotFoundError, dm.quotes, 'secondary')

        dm._secondary_quotes['secondary'] = sec_quotes
        self.assertEqual(id(sec_quotes), id(dm.quotes('secondary')))

    def test_position(self):
        dm = DataManager()

        self.assertRaises(PositionNotFoundError, dm.position, None)

        position1 = 'position1'
        position_sec = 'position2'

        dm._primary_positions = position1

        self.assertEqual(id(position1), id(dm.position()))

        self.assertRaises(PositionNotFoundError, dm.position, 'secondary')

        dm._secondary_positions['secondary'] = position_sec
        self.assertEqual(id(position_sec), id(dm.position('secondary')))

    def test_riskfreerate_get(self):
        dm = DataManager()
        stk = ContractBase('US.S.AAPL', datamanager=dm)

        with patch('tmqrfeed.datafeed.DataFeed.get_riskfreerate_series') as mock_rfr:
            mock_rfr.return_value = pd.Series([1, 2],
                                              index=[datetime.datetime(2011, 1, 1), datetime.datetime(2011, 1, 3)]
                                              )

            self.assertEqual(1, dm.riskfreerate_get(stk, datetime.datetime(2011, 1, 1)))
            self.assertEqual('US', mock_rfr.call_args[0][0])

            self.assertEqual(1, dm.riskfreerate_get(stk, datetime.datetime(2011, 1, 2)))

            self.assertRaises(QuoteNotFoundError, dm.riskfreerate_get, stk, datetime.datetime(2010, 1, 2))

    def test_set_quotes_range_init(self):
        dm = DataManager()

        self.assertEqual(None, dm._quotes_range_start)
        self.assertEqual(None, dm._quotes_range_end)

    def test_set_quotes_range_set_both(self):
        dm = DataManager()

        date_start = datetime.datetime(2011, 1, 1)
        date_end = datetime.datetime(2012, 1, 1)

        dm.quotes_range_set(date_start, date_end)

        self.assertEqual(date_start, dm._quotes_range_start)
        self.assertEqual(date_end, dm._quotes_range_end)

    def test_set_quotes_range_type_check(self):
        dm = DataManager()

        date_start = datetime.datetime(2011, 1, 1)
        date_end = datetime.datetime(2012, 1, 1)

        # valid calls
        dm.quotes_range_set(date_start, date_end)
        dm.quotes_range_set(None, None)
        dm.quotes_range_set()

        self.assertRaises(ArgumentError, dm.quotes_range_set, '2011-01-01', None)
        self.assertRaises(ArgumentError, dm.quotes_range_set, None, '2011-01-01')

    def test_set_quotes_range_type_start_less_end(self):
        dm = DataManager()

        self.assertRaises(ArgumentError, dm.quotes_range_set, datetime.datetime(2012, 1, 1),
                          datetime.datetime(2011, 1, 1))
        self.assertRaises(ArgumentError, dm.quotes_range_set, datetime.datetime(2011, 1, 1),
                          datetime.datetime(2011, 1, 1))

    def test_set_quotes_range__get_quotes(self):
        dm = DataManager()

        data = pd.Series(np.zeros(100), index=pd.date_range(start=datetime.datetime(2011, 1, 1), periods=100))
        dm._primary_quotes = data

        dm.quotes_range_set(datetime.datetime(2010, 1, 1), datetime.datetime(2011, 2, 1))

        qdata = dm.quotes()
        self.assertEqual(qdata.index[0], datetime.datetime(2011, 1, 1))
        self.assertEqual(qdata.index[-1], datetime.datetime(2011, 2, 1))

        # Reset quotes range
        dm.quotes_range_set(range_start=datetime.datetime(2011, 2, 1))
        qdata = dm.quotes()
        self.assertEqual(qdata.index[0], datetime.datetime(2011, 2, 1))
        self.assertEqual(qdata.index[-1], datetime.datetime(2011, 4, 10))

    def test_session_set_instrument(self):
        with patch('tmqrfeed.datafeed.DataFeed.get_instrument_info') as mock_get_instrument_info:
            dm = DataManager()

            mock_asset_info = MagicMock()
            mock_session = MagicMock()
            mock_asset_info.session = mock_session
            mock_get_instrument_info.return_value = mock_asset_info

            dm.session_set('US.ES')
            self.assertEqual('US.ES', mock_get_instrument_info.call_args[0][0])
            self.assertEqual(mock_session, dm._session)

    def test_session_get(self):
        with patch('tmqrfeed.datafeed.DataFeed.get_instrument_info') as mock_get_instrument_info:
            dm = DataManager()

            mock_asset_info = MagicMock()
            mock_session = MagicMock()
            mock_asset_info.session = mock_session
            mock_get_instrument_info.return_value = mock_asset_info

            self.assertRaises(SettingsError, dm.session_get)
            dm.session_set('US.ES')
            self.assertEqual('US.ES', mock_get_instrument_info.call_args[0][0])
            self.assertEqual(mock_session, dm._session)

            self.assertEqual(mock_session, dm.session_get())

    def test_session_set_custom(self):
        dm = DataManager()
        session_list = [
            # Default session
            {
                'decision': '10:40',  # Decision time (uses 'tz' param time zone!)
                'dt': datetime.datetime(1900, 12, 31),  # Actual date of default session start
                'execution': '10:45',  # Execution time (uses 'tz' param time zone!)
                'start': '03:32'  # Start of the session time (uses 'tz' param time zone!)
            },
        ]

        dm.session_set(session_list=session_list,
                       tz='US/Pacific'
                       )

        tz = pytz.timezone("US/Pacific")
        sess = AssetSession(session_list, tz)

        self.assertEqual(dm.session_get(), sess)

    def test_session_set_instance(self):
        dm = DataManager()
        session_list = [
            # Default session
            {
                'decision': '10:40',  # Decision time (uses 'tz' param time zone!)
                'dt': datetime.datetime(1900, 12, 31),  # Actual date of default session start
                'execution': '10:45',  # Execution time (uses 'tz' param time zone!)
                'start': '03:32'  # Start of the session time (uses 'tz' param time zone!)
            },
        ]

        tz = pytz.timezone("UTC")
        sess = AssetSession(session_list, tz)
        dm.session_set(session_instance=sess)
        self.assertEqual(dm.session_get(), sess)

    def test_session_set_errors(self):
        dm = DataManager()
        session_list = [
            # Default session
            {
                'decision': '10:40',  # Decision time (uses 'tz' param time zone!)
                'dt': datetime.datetime(1900, 12, 31),  # Actual date of default session start
                'execution': '10:45',  # Execution time (uses 'tz' param time zone!)
                'start': '03:32'  # Start of the session time (uses 'tz' param time zone!)
            },
        ]
        tz = pytz.timezone("UTC")
        sess = AssetSession(session_list, tz)



        self.assertRaises(SettingsError, dm.session_set, session_list=session_list, tz='US/Pacific', instrument='ES')
        self.assertRaises(SettingsError, dm.session_set, session_list=session_list, instrument='ES')
        self.assertRaises(SettingsError, dm.session_set, tz='US/Pacific', instrument='ES')
        self.assertRaises(SettingsError, dm.session_set, session_list=session_list, tz='US/Uansdjkashdikj')
        self.assertRaises(SettingsError, dm.session_set, session_instance=sess, session_list=session_list)
        self.assertRaises(SettingsError, dm.session_set, session_instance=sess, tz='UTC')
        self.assertRaises(SettingsError, dm.session_set)

        dm.session_set(session_list=session_list,
                       tz='US/Pacific'
                       )
        self.assertRaises(SettingsError, dm.session_set, instrument='ES')

    def test_instrument_info_get(self):
        with patch('tmqrfeed.datafeed.DataFeed.get_instrument_info') as mock_dfeed_get_instrument_info:
            dm = DataManager()
            dm.instrument_info_get('US.ES')

            self.assertEqual(True, mock_dfeed_get_instrument_info.called)
            self.assertEqual('US.ES', mock_dfeed_get_instrument_info.call_args[0][0])
