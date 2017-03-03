import datetime
import unittest

import pandas as pd
import pytz

from tmqr.errors import *
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
                'dt': datetime.datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:32'},

                {
                    'decision': '11:40',
                    'dt': datetime.datetime(2010, 12, 31),
                    'execution': '11:45',
                    'start': '01:32'},

                {
                    'decision': '12:40',
                    'dt': datetime.datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:32'},
            ]
        }


    def test_session_init(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution = sess.get(datetime.datetime(2005, 2, 5, 12, 45, tzinfo=tz))

        self.assertEqual(start, datetime.datetime(2005, 2, 5, 0, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2005, 2, 5, 10, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2005, 2, 5, 10, 45, tzinfo=tz))

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
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        AssetSession(s_correct, tz)

        s_wrong1 = [{  # 'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            # 'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
            # 'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong1 = [{
            'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            # 'start': '00:32'},
        }
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong1, tz)

        s_wrong2 = [{
            'decision': '1040',
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{
            'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '1045',
            'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong2, tz)

        s_wrong2 = [{
            'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
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
            'dt': datetime.datetime(2000, 1, 1),
            'execution': '10:45',
            'start': '00:32'},

            {
                'decision': '10:40',
                'dt': datetime.datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong_order, tz)

        s_wrong_dt_dupe = [{
            'decision': '10:40',
            'dt': datetime.datetime(1900, 1, 1),
            'execution': '10:45',
            'start': '00:32'},

            {
                'decision': '10:40',
                'dt': datetime.datetime(1900, 1, 1, 12, 1),
                'execution': '10:45',
                'start': '00:32'},
        ]
        self.assertRaises(SettingsError, AssetSession, s_wrong_dt_dupe, tz)

    def test_session_get_item(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution = sess.get(datetime.datetime(2010, 12, 30, 12, 45, tzinfo=tz))

        self.assertEqual(start, datetime.datetime(2010, 12, 30, 0, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2010, 12, 30, 10, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2010, 12, 30, 10, 45, tzinfo=tz))

        start, decision, execution = sess.get(datetime.datetime(2010, 12, 31, 12, 45, tzinfo=tz))

        self.assertEqual(start, datetime.datetime(2010, 12, 31, 1, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2010, 12, 31, 11, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2010, 12, 31, 11, 45, tzinfo=tz))

        start, decision, execution = sess.get(datetime.datetime(2011, 1, 1, 12, 45, tzinfo=tz))

        self.assertEqual(start, datetime.datetime(2011, 1, 1, 2, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2011, 1, 1, 12, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2011, 1, 1, 12, 45, tzinfo=tz))

    def test_session_get_item_too_early(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        self.assertRaises(SettingsError, sess.get, datetime.datetime(1800, 12, 30, 12, 45, tzinfo=tz))

    def test_session_get_sess_params(self):
        tz = pytz.timezone(self.info_dic['timezone'])
        sess = AssetSession(self.info_dic['trading_session'], tz)

        start, decision, execution, next = sess._get_sess_params(datetime.datetime(2001, 12, 30, 12, 45, tzinfo=tz))
        self.assertEqual(start, datetime.datetime(2001, 12, 30, 0, 32, tzinfo=tz))
        self.assertEqual(decision, datetime.datetime(2001, 12, 30, 10, 40, tzinfo=tz))
        self.assertEqual(execution, datetime.datetime(2001, 12, 30, 10, 45, tzinfo=tz))
        self.assertEqual(next, datetime.datetime(2010, 12, 31, tzinfo=tz))

        """
                    'dt': datetime.datetime(1900, 1, 1),
                    'dt': datetime.datetime(2010, 12, 31),
                    'dt': datetime.datetime(2011, 1, 1),
        """
        start, decision, execution, next = sess._get_sess_params(datetime.datetime(2010, 12, 31, 12, 45, tzinfo=tz))
        self.assertEqual(next, datetime.datetime(2011, 1, 1, tzinfo=tz))

        start, decision, execution, next = sess._get_sess_params(datetime.datetime(2012, 12, 31, 12, 45, tzinfo=tz))
        self.assertEqual(next, None)

    def test_session_filter_dataframe_errors(self):
        info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '11:40',
                'dt': datetime.datetime(1900, 1, 1),
                'execution': '11:45',
                'start': '11:30'},

                {
                    'decision': '11:40',
                    'dt': datetime.datetime(2009, 12, 31),
                    'execution': '11:45',
                    'start': '01:30'},

                {
                    'decision': '12:40',
                    'dt': datetime.datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:30'},
            ]
        }
        tz = pytz.timezone(info_dic['timezone'])
        sess = AssetSession(info_dic['trading_session'], tz)

        base_date = datetime.datetime(2008, 10, 10)
        data = [
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 29)), 'v': 0},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 30)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 31)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 39)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 40)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 41)), 'v': 0},
        ]
        df = pd.DataFrame(data).set_index('dt').tz_localize(tz)

        self.assertRaises(ArgumentError, sess.filter_dataframe, df.tz_convert('UTC'))
        self.assertRaises(ArgumentError, sess.filter_dataframe, None)
        self.assertRaises(ArgumentError, sess.filter_dataframe, [])
        self.assertRaises(ArgumentError, sess.filter_dataframe, df)

    def test_session_filter_dataframe(self):
        info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime.datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:30'},

                {
                    'decision': '11:40',
                    'dt': datetime.datetime(2009, 12, 31),
                    'execution': '11:45',
                    'start': '01:30'},

                {
                    'decision': '12:40',
                    'dt': datetime.datetime(2011, 1, 1),
                    'execution': '12:45',
                    'start': '02:30'},
            ]
        }
        tz = pytz.timezone(info_dic['timezone'])
        sess = AssetSession(info_dic['trading_session'], tz)

        base_date = datetime.datetime(2008, 10, 10)
        data = [
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 29)), 'v': 0},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 30)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 31)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 39)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 40)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 41)), 'v': 0},
        ]
        df = pd.DataFrame(data).set_index('dt').tz_localize(tz)

        result = sess.filter_dataframe(df)
        for d in data:
            if d['v'] == 1:
                self.assertTrue(d['dt'] in result.index)
            elif d['v'] == 0:
                self.assertFalse(d['dt'] in result.index)
        #
        # Session 2
        #
        base_date = datetime.datetime(2010, 10, 10)
        data = [
            {'dt': datetime.datetime.combine(base_date, datetime.time(1, 29)), 'v': 0},
            {'dt': datetime.datetime.combine(base_date, datetime.time(1, 30)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(1, 31)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(11, 39)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(11, 40)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(11, 41)), 'v': 0},
        ]
        df = pd.DataFrame(data).set_index('dt').tz_localize(tz)

        result = sess.filter_dataframe(df)
        for d in data:
            if d['v'] == 1:
                self.assertTrue(d['dt'] in result.index, msg=str(d['dt']))
            elif d['v'] == 0:
                self.assertFalse(d['dt'] in result.index, msg=str(d['dt']))

        #
        # Session 3
        #
        base_date = datetime.datetime(2012, 10, 10)
        data = [
            {'dt': datetime.datetime.combine(base_date, datetime.time(2, 29)), 'v': 0},
            {'dt': datetime.datetime.combine(base_date, datetime.time(2, 30)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(2, 31)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(12, 39)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(12, 40)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(12, 41)), 'v': 0},
        ]
        df = pd.DataFrame(data).set_index('dt').tz_localize(tz)

        result = sess.filter_dataframe(df)
        for d in data:
            if d['v'] == 1:
                self.assertTrue(d['dt'] in result.index, msg=str(d['dt']))
            elif d['v'] == 0:
                self.assertFalse(d['dt'] in result.index, msg=str(d['dt']))

    def test_session_filter_dataframe_single_session(self):
        info_dic = {
            'futures_months': [3, 6, 9, 12],
            'instrument': 'US.ES',
            'market': 'US',
            'rollover_days_before': 2,
            'ticksize': 0.25,
            'tickvalue': 12.5,
            'timezone': 'US/Pacific',
            'trading_session': [{
                'decision': '10:40',
                'dt': datetime.datetime(1900, 1, 1),
                'execution': '10:45',
                'start': '00:30'},
            ]
        }
        tz = pytz.timezone(info_dic['timezone'])
        sess = AssetSession(info_dic['trading_session'], tz)

        base_date = datetime.datetime(2012, 10, 10)
        data = [
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 29)), 'v': 0},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 30)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(0, 31)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 39)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 40)), 'v': 1},
            {'dt': datetime.datetime.combine(base_date, datetime.time(10, 41)), 'v': 0},
        ]
        df = pd.DataFrame(data).set_index('dt').tz_localize(tz)

        result = sess.filter_dataframe(df)
        for d in data:
            if d['v'] == 1:
                self.assertTrue(d['dt'] in result.index)
            elif d['v'] == 0:
                self.assertFalse(d['dt'] in result.index)
