import unittest
from unittest.mock import MagicMock, patch

from tmqr.errors import *
from tmqrfeed.contracts import *
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.manager import DataManager
from tmqrfeed.chains import *


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
                self.assertTrue(mock_dm_series_check.called)

                self.assertRaises(DataManagerError, dm.series_primary_set, quote_cls_mock, 'test', kwtest=True)
                self.assertTrue(quote_cls_mock.called)
                self.assertEqual(('test',), quote_cls_mock.call_args[0])
                self.assertEqual({'kwtest': True}, quote_cls_mock.call_args[1])
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
                    self.assertEqual({'kwtest': True}, quote_cls_mock.call_args[1])
                    self.assertTrue(quote_mock.build.called)

                    self.assertEqual('quotes', dm._secondary_quotes['name1'])
                    self.assertEqual('pos', dm._secondary_positions['name1'])

                    self.assertRaises(DataManagerError, dm.series_extra_set, 'name1', quote_cls_mock, 'test',
                                      kwtest=True)

    def test_get_series(self):
        with patch('tmqrfeed.datafeed.DataFeed.get_raw_series') as mock_get_raw_series:
            dm = DataManager()
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
        with patch('tmqrfeed.datafeed.DataFeed.get_raw_series') as mock_get_raw_series:
            dm = DataManager()
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
            self.assertEqual(kwargs['date_start'], QDATE_MAX)
            self.assertEqual(kwargs['date_end'], QDATE_MIN)

    def test_series_align(self):
        dm = DataManager()
        # Just mock for 100% coverage
        # TODO: implement align test
        self.assertEqual('extra', dm.series_align(None, 'extra'))

    def test_series_check(self):
        dm = DataManager()
        # Just mock for 100% coverage
        # TODO: implement check test
        self.assertEqual(True, dm.series_check(None))

    def test__price_get_from_datafeed(self):
        dm = DataManager()
        fut = FutureContract('US.F.CL.G12.120120', datamanager=dm)

        dm._price_get_from_datafeed(fut, datetime.datetime(2012, 1, 9))

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

        dm._primary_positions = {
            datetime.datetime(2012, 1, 1): {
                stk: (0.1, 0.2, 1),
                opt: (1, 2, 4)
            }
        }

        dt = datetime.datetime(2012, 1, 1)
        # No date time
        self.assertEqual((None, None), dm._price_get_positions_cached(stk, datetime.datetime(2012, 1, 2)))

        # No asset
        self.assertEqual((None, None), dm._price_get_positions_cached(fut, datetime.datetime(2012, 1, 1)))

        # Existing assets, working also with options
        self.assertEqual((0.1, 0.2), dm._price_get_positions_cached(stk, datetime.datetime(2012, 1, 1)))
        self.assertEqual((1, 2), dm._price_get_positions_cached(opt, datetime.datetime(2012, 1, 1)))

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
