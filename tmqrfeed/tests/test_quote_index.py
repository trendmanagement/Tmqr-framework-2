import unittest
from unittest.mock import MagicMock, patch
from tmqrfeed.quotes.quote_index import QuoteIndex
from tmqrfeed import DataManager
from datetime import datetime
import pytz
from tmqrfeed.assetsession import AssetSession
from tmqr.errors import *


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

    def test_build_asset_session_set(self):
        with patch("tmqrindex.index_base.IndexBase.deserialize") as mock_deserialize:
            with patch("tmqrfeed.dataengines.DataEngineMongo.db_load_index") as mock_db_load_index:
                mock_index = MagicMock()
                mock_index.position = 'position'
                mock_index.data = 'data'

                #
                # Set the session
                #
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
                mock_index.session = AssetSession(session_list, tz)

                session2 = AssetSession(session_list, pytz.timezone("US/Pacific"))

                mock_db_load_index.return_value = {'index': 'data'}
                mock_deserialize.return_value = mock_index

                # Set session
                dm = DataManager()
                qi = QuoteIndex("index_name", datamanager=dm, set_session=True, check_session=True)
                data, pos = qi.build()
                self.assertEqual(dm.session_get(), mock_index.session)

                # Set session already set explicitly
                dm = DataManager()
                dm.session_set(session_instance=mock_index.session)
                qi = QuoteIndex("index_name", datamanager=dm, set_session=True, check_session=True)
                data, pos = qi.build()
                self.assertEqual(dm.session_get(), mock_index.session)

                # Set session already set explicitly
                dm = DataManager()
                dm.session_set(session_instance=session2)
                qi = QuoteIndex("index_name", datamanager=dm, set_session=True, check_session=True)
                self.assertRaises(SettingsError, qi.build)

                # Index has no session
                dm = DataManager()
                mock_index.session = None
                qi = QuoteIndex("index_name", datamanager=dm, set_session=True, check_session=True)
                self.assertRaises(SettingsError, qi.build)
