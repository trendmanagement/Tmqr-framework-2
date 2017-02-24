import unittest
import datetime
from tmqrfeed.assetinfo import AssetInfo
from tmqrfeed.assetsession import AssetSession
import pytz

class AssetInfoTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {'futures_months': [3, 6, 9, 12],
                         'instrument': 'US.ES',
                         'market': 'US',
                         'rollover_days_before': 2,
                         'ticksize': 0.25,
                         'tickvalue': 12.5,
                         'timezone': 'US/Pacific',
                         'trading_session': [{'decision': '10:40',
                                              'dt': datetime.datetime(1900, 1, 1, 0, 0),
                                              'execution': '10:45',
                                              'start': '00:32'}]}
    def test_init(self):
        ai = AssetInfo(self.info_dic)

        self.assertEqual(ai.instrument, 'US.ES')
        self.assertEqual(ai.market, 'US')
        self.assertEqual(ai.ticksize, 0.25)
        self.assertEqual(ai.tickvalue, 12.5)
        self.assertEqual(ai.timezone, pytz.timezone('US/Pacific'))

        # These values fetched dynamically
        self.assertEqual(ai.rollover_days_before, 2)
        self.assertEqual(ai.futures_months, [3, 6, 9, 12])

    def test_dynamic_params_getting(self):
        ai = AssetInfo(self.info_dic)
        self.assertEqual(ai.rollover_days_before, 2)
        self.assertRaises(KeyError, ai.__getattr__, 'nonexistingkey')



