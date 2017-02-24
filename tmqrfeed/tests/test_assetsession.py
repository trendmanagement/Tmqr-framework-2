import unittest
import datetime
from tmqrfeed.assetinfo import AssetInfo
from tmqrfeed.assetsession import AssetSession
import pytz

class AssetSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {'futures_months': [3, 6, 9, 12],
                         'instrument': 'US.ES',
                         'market': 'US',
                         'rollover_days_before': 2,
                         'ticksize': 0.25,
                         'tickvalue': 12.5,
                         'timezone': 'US/Pacific',
                         'trading_session': [{'decision': '10:40',
                                              'dt': datetime.datetime(1900, 1, 1),
                                              'execution': '10:45',
                                              'start': '00:32'},

                                             {'decision': '11:40',
                                              'dt': datetime.datetime(2010, 12, 31),
                                              'execution': '11:45',
                                              'start': '01:32'},

                                             {'decision': '12:40',
                                              'dt': datetime.datetime(2011, 1, 1),
                                              'execution': '12:45',
                                              'start': '02:32'},
                                            ]
                         }


    def test_session_init(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)


        start, decision, execution = sess[datetime.datetime(2005, 2, 5, 12, 45)]

        self.assertEqual(start, datetime.datetime(2005, 2, 5, 0, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2005, 2, 5, 10, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2005, 2, 5, 10, 45, tzinfo=tz))

    def test_session_init_integritychecks_none(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        self.assertRaises(ValueError, AssetSession, None, tz)

    def test_session_init_integritychecks_zero_len(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        self.assertRaises(ValueError, AssetSession, [], tz)

    def test_session_init_integritychecks_names_in_dict(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        s_correct = [{'decision': '10:40',
                                              'dt': datetime.datetime(1900, 1, 1),
                                              'execution': '10:45',
                                              'start': '00:32'},
                                            ]
        AssetSession(s_correct, tz)

        s_wrong1 = [{ # 'decision': '10:40',
                      'dt': datetime.datetime(1900, 1, 1),
                      'execution': '10:45',
                      'start': '00:32'},
                     ]
        self.assertRaises(ValueError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{  'decision': '10:40',
            # 'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(ValueError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{'decision': '10:40',
                     'dt': datetime.datetime(1900, 1, 1),
                     # 'execution': '10:45',
                     'start': '00:32'},
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{'decision': '10:40',
                     'dt': datetime.datetime(1900, 1, 1),
                     'execution': '10:45',
                     #'start': '00:32'},
                     }
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong1, tz)

        s_wrong2 = [{'decision': '1040',
                     'dt': datetime.datetime(1900, 1, 1),
                     'execution': '10:45',
                     'start': '00:32'},
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{'decision': '10:40',
                     'dt': datetime.datetime(1900, 1, 1),
                     'execution': '1045',
                     'start': '00:32'},
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{'decision': '10:40',
                     'dt': datetime.datetime(1900, 1, 1),
                     'execution': '10:45',
                     'start': '0032'},
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong2, tz)


        s_wrong3 = [{'decision': '10:40',
                     'dt': None,
                     'execution': '10:45',
                     'start': '00:32'},
                    ]
        self.assertRaises(ValueError, AssetSession, s_wrong3, tz)

        s_wrong_order = [{'decision': '10:40',
                      'dt': datetime.datetime(2000, 1, 1),
                      'execution': '10:45',
                      'start': '00:32'},

                    {'decision': '10:40',
                      'dt': datetime.datetime(1900, 1, 1),
                      'execution': '10:45',
                      'start': '00:32'},
                     ]
        self.assertRaises(ValueError, AssetSession, s_wrong_order, tz)

        s_wrong_dt_dupe= [{'decision': '10:40',
                          'dt': datetime.datetime(1900, 1, 1),
                          'execution': '10:45',
                          'start': '00:32'},

                         {'decision': '10:40',
                          'dt': datetime.datetime(1900, 1, 1, 12, 1),
                          'execution': '10:45',
                          'start': '00:32'},
                         ]
        self.assertRaises(ValueError, AssetSession, s_wrong_dt_dupe, tz)


    def test_session_get_item(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution = sess[datetime.datetime(2010, 12, 30, 12, 45)]

        self.assertEqual(start, datetime.datetime(2010, 12, 30, 0, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2010, 12, 30, 10, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2010, 12, 30, 10, 45, tzinfo=tz))

        start, decision, execution = sess[datetime.datetime(2010, 12, 31, 12, 45)]

        self.assertEqual(start, datetime.datetime(2010, 12, 31, 1, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2010, 12, 31, 11, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2010, 12, 31, 11, 45, tzinfo=tz))

        start, decision, execution = sess[datetime.datetime(2011, 1, 1, 12, 45)]

        self.assertEqual(start, datetime.datetime(2011, 1, 1, 2, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2011, 1, 1, 12, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2011, 1, 1, 12, 45, tzinfo=tz))

    def test_session_get_item_too_early(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        self.assertRaises(ValueError, sess.__getitem__, datetime.datetime(1800, 12, 30, 12, 45))