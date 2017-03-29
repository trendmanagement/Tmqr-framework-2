import unittest
from unittest.mock import MagicMock, patch

from tmqr.errors import *
from tmqrfeed.contracts import *
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.manager import DataManager


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

        dm._price_get_from_datafeed(fut, datetime(2012, 1, 9))
