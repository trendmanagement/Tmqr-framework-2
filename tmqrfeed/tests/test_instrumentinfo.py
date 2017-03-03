import datetime
import unittest

import pytz

from tmqr.errors import InstrumentInfoNotFound
from tmqr.settings import *
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.instrumentinfo import InstrumentInfo


class InstrumentInfoTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'data_futures_src': SRC_INTRADAY,
            'data_options_src': SRC_OPTIONS,
            'trading_session': [{
                                    'decision': '10:40',
                'dt': datetime(1900, 1, 1, 0, 0),
                                    'execution': '10:45',
                                    'start': '00:32'}]}

    def test_init(self):
        ai = InstrumentInfo(self.info_dic)

        self.assertEqual(ai.instrument, 'US.ES')
        self.assertEqual(ai.market, 'US')
        self.assertEqual(ai.ticksize, 0.25)
        self.assertEqual(ai.tickvalue, 12.5)
        self.assertEqual(ai.timezone, pytz.timezone('US/Pacific'))

        # These values fetched dynamically
        self.assertEqual(ai.rollover_days_before, 2)
        self.assertEqual(ai.futures_months, [3, 6, 9, 12])
        self.assertEqual(True, isinstance(ai.session, AssetSession))

    def test_init_bad_dict(self):
        self.assertRaises(InstrumentInfoNotFound, InstrumentInfo, {})
        self.assertRaises(InstrumentInfoNotFound, InstrumentInfo, None)
        self.assertRaises(InstrumentInfoNotFound, InstrumentInfo, {'weird': 'no_data'})


    def test_dynamic_params_getting(self):
        ai = InstrumentInfo(self.info_dic)
        self.assertEqual(ai.rollover_days_before, 2)
        self.assertRaises(InstrumentInfoNotFound, ai.__getattr__, 'nonexistingkey')

    def test_dynamic_get_with_default(self):
        ai = InstrumentInfo(self.info_dic)
        self.assertEqual(1.0, ai.get('nonexistingkey', 1.0))
        self.assertEqual(None, ai.get('nonexistingkey'))
