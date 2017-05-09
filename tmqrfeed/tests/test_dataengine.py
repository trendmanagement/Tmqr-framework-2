import unittest
from unittest.mock import patch

from tmqrfeed.contracts import FutureContract
from tmqrfeed.dataengines import *
import lz4


class DataEngineTestCase(unittest.TestCase):
    def test_get_asset_info_bad_instrument(self):
        dfeed = DataEngineMongo()
        self.assertRaises(ArgumentError, dfeed.db_get_instrument_info, 'CL')
        self.assertRaises(ArgumentError, dfeed.db_get_instrument_info, '')
        self.assertRaises(ArgumentError, dfeed.db_get_instrument_info, 'CL.US.S')

    def test_get_asset_info_existing_instrument(self):
        deng = DataEngineMongo()
        ainfo = deng.db_get_instrument_info("US.ES")
        self.assertEqual('US.ES', ainfo['instrument'])
        self.assertEqual(12.5, ainfo['tickvalue'])

    def test_get_asset_info_nonexisting_instrument(self):
        deng = DataEngineMongo()
        ainfo = deng.db_get_instrument_info("US.NON_EXISTING_INSTRUMENT")
        self.assertEqual('US.NON_EXISTING_INSTRUMENT', ainfo['instrument'])
        self.assertEqual(1.0, ainfo['tickvalue'])

    def test_get_asset_info_non_existing_market(self):
        deng = DataEngineMongo()
        self.assertRaises(DataEngineNotFoundError, deng.db_get_instrument_info, "NONEXISTINGMARKET.ES")

    def test_get_futures_chain(self):
        deng = DataEngineMongo()
        list = deng.db_get_futures_chain("US.CL")

        prev_exp = None
        for t in list:
            self.assertTrue('tckr' in t)
            f = FutureContract(t['tckr'])

            if prev_exp is not None:
                self.assertTrue(f.expiration > prev_exp)
            prev_exp = f.expiration

    def test_get_futures_chain_with_date_filter(self):
        deng = DataEngineMongo()
        list = deng.db_get_futures_chain("US.CL", date_start=datetime(2012, 1, 1))

        prev_exp = None
        for t in list:
            self.assertTrue('tckr' in t)
            f = FutureContract(t['tckr'])

            self.assertTrue(f.expiration.year >= 2012)
            if prev_exp is not None:
                self.assertTrue(f.expiration > prev_exp)
            prev_exp = f.expiration

    def test_get_contract_info(self):
        deng = DataEngineMongo()
        ci = deng.db_get_contract_info('US.C.F-ZB-H11-110322.110121@89.0')
        self.assertEqual(ci['tckr'], 'US.C.F-ZB-H11-110322.110121@89.0')

        self.assertRaises(DataEngineNotFoundError, deng.db_get_contract_info, 'NON_EXISTING_TICKER')

    def test_get_raw_series_intraday(self):
        deng = DataEngineMongo()

        df, qtype = deng.db_get_raw_series('US.F.CL.Q12.120720', SRC_INTRADAY)
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(qtype, QTYPE_INTRADAY)
        self.assertEqual(True, len(df) > 0)

        df2, qtype2 = deng.db_get_raw_series('US.F.CL.Q12.120720', SRC_INTRADAY,
                                             date_start=datetime(2011, 8, 1),
                                             date_end=datetime(2012, 7, 19))
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(qtype, QTYPE_INTRADAY)
        self.assertEqual(True, len(df) > 0)
        self.assertEqual(True, len(df) > len(df2))
        self.assertEqual(datetime(2011, 8, 1).date(), df2.index[0].date())
        self.assertEqual(datetime(2012, 7, 19).date(), df2.index[-1].date())

        #
        # Check support of 'date' type for date_start, date_end
        #
        df2, qtype2 = deng.db_get_raw_series('US.F.CL.Q12.120720', SRC_INTRADAY,
                                             date_start=datetime(2011, 8, 1).date(),
                                             date_end=datetime(2012, 7, 19).date())
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(qtype, QTYPE_INTRADAY)
        self.assertEqual(True, len(df) > 0)
        self.assertEqual(True, len(df) > len(df2))
        self.assertEqual(datetime(2011, 8, 1).date(), df2.index[0].date())
        self.assertEqual(datetime(2012, 7, 19).date(), df2.index[-1].date())

        self.assertRaises(DataSourceNotFoundError, deng.db_get_raw_series, 'US.F.CL.Q12.120720', "NON_EXISTING_SOURCE")

        self.assertRaises(IntradayQuotesNotFoundError, deng.db_get_raw_series, 'US.F.CL.N83.830622', SRC_INTRADAY)

    def test_get_raw_series_intraday_db_corruption_error(self):
        deng = DataEngineMongo()

        with patch('pymongo.collection.Collection.find') as mock_find:
            mock_find.return_value = [
                {'ohlc': lz4.block.compress(pickle.dumps('NON_DATAFRAME_OBJECT')), 'dt': '2015-01-01'}]

            self.assertRaises(DBDataCorruptionError, deng.db_get_raw_series, 'US.F.CL.Q12.120720', SRC_INTRADAY)

    def test_db_get_option_chains(self):
        deng = DataEngineMongo()

        with patch('pymongo.collection.Collection.aggregate') as mock_aggregate:
            deng.db_get_option_chains('US.F.ES.H11.110318')

            expected_query = [
                {'$match': {
                    'underlying': 'US.F.ES.H11.110318',
                    'type': {'$in': ['P', 'C']},
                }},

                {'$sort': {'strike': 1}},

                {'$project': {'tckr': 1, 'exp': 1, 'strike': 1, 'type': 1}
                 },

                {'$group': {
                    '_id': {'date': '$exp'},
                    'chain': {'$push': '$$ROOT'},
                }
                },
                {'$sort': {"_id.date": 1}}
            ]
            self.assertEqual(expected_query, mock_aggregate.call_args[0][0])
            pass

    def test_get_raw_series_eod_options(self):
        deng = DataEngineMongo()

        with patch('pymongo.collection.Collection.find_one') as mock_find_one:
            mock_find_one.return_value = None
            self.assertRaises(OptionsEODQuotesNotFoundError, deng.db_get_raw_series, 'US.F.CL.Q12.120720',
                              SRC_OPTIONS_EOD)

            mock_find_one.reset_mock()
            mock_find_one.return_value = {'data': lz4.block.compress(pickle.dumps('NON_DATAFRAME_OBJECT'))}

            self.assertRaises(DBDataCorruptionError, deng.db_get_raw_series, 'US.F.CL.Q12.120720', SRC_OPTIONS_EOD)

            mock_find_one.reset_mock()
            mock_find_one.return_value = {
                'data': lz4.block.compress(
                    pickle.dumps(pd.DataFrame([{'iv': 0.1, 'dt': datetime(2011, 1, 1)}]).set_index('dt')))}

            df, qtype = deng.db_get_raw_series('US.F.CL.Q12.120720', SRC_OPTIONS_EOD)

            self.assertEqual(dict, type(df))
            self.assertEqual(pd.DataFrame, type(df['data']))
            self.assertEqual(QTYPE_OPTIONS_EOD, qtype)

    def test_db_load_index(self):
        deng = DataEngineMongo()

        with patch('pymongo.collection.Collection.find_one') as mock_find_one:
            mock_find_one.return_value = None
            self.assertRaises(DataEngineNotFoundError, deng.db_load_index, 'SOME_INDEX')

            mock_find_one.return_value = {"index": 'data'}
            self.assertEqual({"index": 'data'}, deng.db_load_index("index"))

            self.assertEqual({'name': 'index'}, mock_find_one.call_args[0][0])

    def test_db_save_index(self):
        with patch('pymongo.collection.Collection.create_index') as mock_create_index:
            with patch('pymongo.collection.Collection.replace_one') as mock_replace_one:
                deng = DataEngineMongo()
                idx_dict = {'name': 'index', 'test': 'test'}
                deng.db_save_index(idx_dict)

                self.assertTrue(mock_create_index.called)
                self.assertTrue(mock_replace_one.called)

                self.assertEqual([('name', pymongo.ASCENDING)], mock_create_index.call_args[0][0])

                self.assertEqual({'name': 'index'}, mock_replace_one.call_args[0][0])
                self.assertEqual(idx_dict, mock_replace_one.call_args[0][1])
                self.assertEqual({'upsert': True}, mock_replace_one.call_args[1])

    def test_db_get_rfr_series(self):
        deng = DataEngineMongo()

        with patch('pymongo.collection.Collection.find_one') as mock_find:
            rfr = pd.Series([1, 2],
                            index=[datetime(2011, 1, 1), datetime(2011, 1, 3)]
                            )
            mock_find.return_value = {'rfr_series': lz4.block.compress(pickle.dumps(rfr)),
                                      'market': 'US'}

            result = deng.db_get_rfr_series('US')

            self.assertTrue(isinstance(result, pd.Series))

            mock_find.return_value = None
            self.assertRaises(DataEngineNotFoundError, deng.db_get_rfr_series, 'US')
