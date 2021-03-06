import unittest

import pytz

from tmqr.errors import *
from tmqr.settings import *
from tmqrfeed.assetsession import AssetSession

class AssetSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:32'},

                {
                    'decision': '11:40',
                    'dt': datetime(2010, 12, 31),
                    'execution': '11:45',
                    'start': '01:32'},

                {
                    'decision': '12:40',
                    'dt': datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:32'},
            ]
        }

        self.info_dic_single_session = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:32'},
            ]
        }


    def test_session_init(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution, next_sess = sess.get(tz.localize(datetime(2005, 2, 5, 12, 45)))

        self.assertEqual(start, tz.localize(datetime(2005, 2, 5, 0, 32)))
        self.assertEqual(decision, tz.localize(datetime(2005, 2, 5, 10, 40)))
        self.assertEqual(execution, tz.localize(datetime(2005, 2, 5, 10, 45)))

    def test_session_init_integritychecks_none(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        self.assertRaises(SettingsError, AssetSession, None, tz)

    def test_session_init_integritychecks_zero_len(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        self.assertRaises(SettingsError, AssetSession, [], tz)

    def test_session_init_integritychecks_names_in_dict(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        s_correct = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        AssetSession(s_correct, tz)

        s_wrong1 = [{  # 'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            # 'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            # 'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            # 'start': '00:32'},
        }
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong2 = [{
            'decision': '1040',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '1045',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '0032'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong2, tz)

        s_wrong3 = [{
            'decision': '10:40',
            'dt': None,
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong3, tz)

        s_wrong_order = [{
            'decision': '10:40',
            'dt': datetime(2000, 1, 1),
            'execution': '10:45',
            'start': '00:32'},

            {
                'decision': '10:40',
                'dt': datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong_order, tz)

        s_wrong_dt_dupe = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},

            {
                'decision': '10:40',
                'dt': datetime(1900, 1, 1, 12, 1),
                'execution': '10:45',
                'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong_dt_dupe, tz)

    def test_session_get_item(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution, next_sess = sess.get(tz.localize(datetime(2010, 12, 30, 12, 45)))

        self.assertEqual(start, tz.localize(datetime(2010, 12, 30, 0, 32)))
        self.assertEqual(decision, tz.localize(datetime(2010, 12, 30, 10, 40)))
        self.assertEqual(execution, tz.localize(datetime(2010, 12, 30, 10, 45)))

        start, decision, execution, next_sess = sess.get(tz.localize(datetime(2010, 12, 31, 12, 45)))

        self.assertEqual(start, tz.localize(datetime(2010, 12, 31, 1, 32)))
        self.assertEqual(decision, tz.localize(datetime(2010, 12, 31, 11, 40)))
        self.assertEqual(execution, tz.localize(datetime(2010, 12, 31, 11, 45)))

        start, decision, execution, next_sess = sess.get(tz.localize(datetime(2011, 1, 1, 12, 45)))

        self.assertEqual(start, tz.localize(datetime(2011, 1, 1, 2, 32)))
        self.assertEqual(decision, tz.localize(datetime(2011, 1, 1, 12, 40)))
        self.assertEqual(execution, tz.localize(datetime(2011, 1, 1, 12, 45)))

    def test_session_get_item_decision_time_shift(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution, next_sess = sess.get(tz.localize(datetime(2010, 12, 30, 12, 45)),
                                                         decision_time_shift=5)

        self.assertRaises(ArgumentError, sess.get, tz.localize(datetime(2010, 12, 30, 12, 45)), decision_time_shift=-5)

        self.assertEqual(start, tz.localize(datetime(2010, 12, 30, 0, 32)))
        self.assertEqual(decision, tz.localize(datetime(2010, 12, 30, 10, 35)))
        self.assertEqual(execution, tz.localize(datetime(2010, 12, 30, 10, 45)))



    def test_session_get_item_too_early(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        self.assertRaises(SettingsError, sess.get, datetime(1800, 12, 30, 12, 45, tzinfo=tz))

    def test_session_get_sess_params(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution, next = sess._get_sess_params(datetime(2001, 12, 30, 12, 45))
        self.assertEqual(start, tz.localize(datetime(2001, 12, 30, 0, 32)))
        self.assertEqual(decision, tz.localize(datetime(2001, 12, 30, 10, 40)))
        self.assertEqual(execution, tz.localize(datetime(2001, 12, 30, 10, 45)))
        self.assertEqual(next, tz.localize(datetime(2010, 12, 31)))

        """
                    'dt': datetime(1900, 1, 1),
                    'dt': datetime(2010, 12, 31),
                    'dt': datetime(2011, 1, 1),
        """
        start, decision, execution, next = sess._get_sess_params(datetime(2010, 12, 31, 12, 45))
        self.assertEqual(next, tz.localize(datetime(2011, 1, 1)))

        start, decision, execution, next = sess._get_sess_params(datetime(2012, 12, 31, 12, 45))
        self.assertEqual(next, None)

    def test_session_equality(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        tz2 = pytz.UTC
        s_correct = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]

        sess = AssetSession(s_correct, tz)
        sess2 = AssetSession(s_correct, tz)
        sess3 = AssetSession(s_correct, tz2)

        self.assertEqual(sess, sess2)
        self.assertNotEqual(sess, sess3)
        self.assertNotEqual(sess, None)
        self.assertNotEqual(sess, 'something')

    def test_session_serialize(self):
        tz2 = pytz.UTC
        s_correct = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        sess = AssetSession(s_correct, tz2).serialize()

        self.assertEqual(dict, type(sess))
        self.assertEqual(s_correct, sess['trading_session'])
        self.assertEqual('UTC', sess['tz'])

    def test_session_str_repr(self):
        tz2 = pytz.UTC
        s_correct = [{
            'decision': '10:40',
            'dt': datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        sess = AssetSession(s_correct, tz2)
        self.assertEqual(str(s_correct), str(sess))
        self.assertEqual(str(s_correct), repr(sess))
