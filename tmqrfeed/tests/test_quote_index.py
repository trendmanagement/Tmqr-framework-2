import unittest
from unittest.mock import MagicMock, patch
from tmqrfeed.quotes.quote_index import QuoteIndex
from tmqrfeed.manager import DataManager


class QuoteContFutTestCase(unittest.TestCase):
    def test_init(self):
        dm = DataManager()
        qi = QuoteIndex("index_name", datamanager=dm)

        self.assertEqual(qi.index_name, "index_name")

    def test_str(self):
        dm = DataManager()
        qi = QuoteIndex("index_name", datamanager=dm)

        self.assertEqual("QuoteIndex-index_name", str(qi))

    def test_build(self):
        with patch("tmqrindex.index_base.IndexBase.deserialize") as mock_deserialize:
            with patch("tmqrfeed.dataengines.DataEngineMongo.db_load_index") as mock_db_load_index:
                mock_index = MagicMock()
                mock_index.position = 'position'
                mock_index.data = 'data'

                mock_db_load_index.return_value = {'index': 'data'}

                mock_deserialize.return_value = mock_index

                dm = DataManager()
                qi = QuoteIndex("index_name", datamanager=dm)

                data, pos = qi.build()

                self.assertTrue(mock_deserialize.called)
                self.assertTrue(mock_db_load_index.called)

                self.assertEqual(dm, mock_deserialize.call_args[0][0])
                self.assertEqual({'index': 'data'}, mock_deserialize.call_args[0][1])
                self.assertEqual(True, mock_deserialize.call_args[1]['as_readonly'])

                self.assertEqual('data', data)
                self.assertEqual('position', pos)
