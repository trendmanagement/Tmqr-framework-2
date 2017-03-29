import unittest
from unittest.mock import MagicMock, patch

from tmqr.errors import *
from tmqrfeed.datafeed import DataFeed
from tmqrfeed.manager import DataManager


class DataManagerTestCase(unittest.TestCase):
    def test_init(self):
        self.assertRaises(TypeError, DataManager, datafeed_cls=None)
        dm = DataManager()
        self.assertTrue(DataFeed, type(dm.feed))

        eng_settings = {'test': 'test'}
        dm = DataManager(data_engine_settings=eng_settings)
        self.assertEqual(dm.feed.data_engine_settings, eng_settings)

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


if __name__ == '__main__':
    unittest.main()
