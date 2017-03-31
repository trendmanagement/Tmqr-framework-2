import unittest
from unittest.mock import patch

from tmqrfeed.contracts import FutureContract
from tmqrfeed.dataengines import *


class DataEngineTestCase(unittest.TestCase):
    def test_get_asset_info_bad_instrument(self):
        dfeed = DataEngineMongo()
        self.assertRaises(ValueError, dfeed.db_get_instrument_info, 'CL')
        self.assertRaises(ValueError, dfeed.db_get_instrument_info, '')
        self.assertRaises(ValueError, dfeed.db_get_instrument_info, 'CL.US.S')

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
                self.assertTrue(f.exp_date > prev_exp)
            prev_exp = f.exp_date

    def test_get_futures_chain_with_date_filter(self):
        deng = DataEngineMongo()
        list = deng.db_get_futures_chain("US.CL", date_start=datetime(2012, 1, 1))

        prev_exp = None
        for t in list:
            self.assertTrue('tckr' in t)
            f = FutureContract(t['tckr'])

            self.assertTrue(f.exp_date.year >= 2012)
            if prev_exp is not None:
                self.assertTrue(f.exp_date > prev_exp)
            prev_exp = f.exp_date

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

        self.assertRaises(DataSourceNotFoundError, deng.db_get_raw_series, 'US.F.CL.Q12.120720', "NON_EXISTING_SOURCE")

        self.assertRaises(IntradayQuotesNotFoundError, deng.db_get_raw_series, 'US.F.CL.N83.830622', SRC_INTRADAY)

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
