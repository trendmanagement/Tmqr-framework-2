import unittest
from tmqrfeed.manager import DataManager
from tmqrindex.index_contfut import IndexContFut
from unittest.mock import patch, MagicMock
from tmqr.errors import *
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from datetime import datetime
import pytz
from tmqrfeed.assetsession import AssetSession

class IndexContFutTestCase(unittest.TestCase):
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
        dm = MagicMock(DataManager())
        idx = IndexContFut(dm, instrument='CL')
        self.assertEqual(idx.instrument, 'CL')

        self.assertRaises(ArgumentError, IndexContFut, dm)

    def test_setup(self):
        dm = MagicMock(DataManager())
        idx = IndexContFut(dm, instrument='CL')

        idx.setup()

        self.assertTrue(dm.series_primary_set.called)
        self.assertEqual(QuoteContFut, dm.series_primary_set.call_args[0][0])
        self.assertEqual('CL', dm.series_primary_set.call_args[0][1])
        self.assertEqual({'timeframe': 'D', 'decision_time_shift': 5}, dm.series_primary_set.call_args[1])
        self.assertEqual('CL', dm.session_set.call_args[0][0])

    def test_presaved_session(self):
        dm = MagicMock(DataManager())

        idx = IndexContFut(dm, instrument='CL', session=self.sess)

        idx.setup()

        self.assertTrue(dm.series_primary_set.called)
        self.assertEqual(QuoteContFut, dm.series_primary_set.call_args[0][0])
        self.assertEqual('CL', dm.series_primary_set.call_args[0][1])
        self.assertEqual({'timeframe': 'D', 'decision_time_shift': 5}, dm.series_primary_set.call_args[1])
        self.assertEqual(self.sess, dm.session_set.call_args[1]['session_instance'])

    def test_set_data_and_position(self):
        dm = MagicMock(DataManager())
        dm.quotes.return_value = "QUOTES"
        dm.position.return_value = "POSITION"

        idx = IndexContFut(dm, instrument='CL')
        idx.set_data_and_position()

        self.assertTrue(dm.position.called)
        self.assertTrue(dm.quotes.called)
        self.assertEqual("QUOTES", idx.data)
        self.assertEqual("POSITION", idx.position)
