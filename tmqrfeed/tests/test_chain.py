import unittest
from datetime import datetime

from tmqrfeed.assetinfo import AssetInfo
from tmqrfeed.chains import FutureChain
from tmqrfeed.contracts import FutureContract


class FutChainTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = {'futures_months': [3, 6, 9, 12],
                         'instrument': 'US.ES',
                         'market': 'US',
                         'rollover_days_before': 2,
                         'ticksize': 0.25,
                         'tickvalue': 12.5,
                         'timezone': 'US/Pacific',
                         'trading_session': [{'decision': '10:40',
                                              'dt': datetime(1900, 1, 1, 0, 0),
                                              'execution': '10:45',
                                              'start': '00:32'}]}
        self.ainfo = AssetInfo(self.info_dic)
        self.chain_tickers = ['US.F.CL.G11.110120',
                              'US.F.CL.H11.110222',
                              'US.F.CL.J11.110322',
                              'US.F.CL.K11.110419',
                              'US.F.CL.M11.110520',
                              'US.F.CL.N11.110622',
                              'US.F.CL.Q11.110720',
                              'US.F.CL.U11.110822',
                              'US.F.CL.V11.110921',
                              'US.F.CL.X11.111020',
                              'US.F.CL.Z11.111121',
                              'US.F.CL.F12.111221',
                              'US.F.CL.G12.120120',
                              'US.F.CL.H12.120222',
                              'US.F.CL.J12.120321',
                              'US.F.CL.K12.120420',
                              'US.F.CL.M12.120522',
                              'US.F.CL.N12.120620',
                              'US.F.CL.Q12.120720',
                              'US.F.CL.U12.120822',
                              'US.F.CL.V12.120920',
                              'US.F.CL.X12.121022',
                              'US.F.CL.Z12.121120',
                              ]

    def test_init(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        self.assertEqual('US.F.CL.M11.110520', chain._futchain.iloc[0].name.ticker)
        for i in range(1, len(chain._futchain)):
            row = chain._futchain.iloc[i]
            prev_row = chain._futchain.iloc[i - 1]
            fut = row.name

            self.assertTrue(fut.exp_month in [3, 6, 9, 12])
            self.assertEqual(True, row.date_end > row.date_start)
            self.assertEqual(True, row.date_start > prev_row.date_end)
            self.assertEqual(True, row.date_end < fut.exp_date)

    def test_futures(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)
        self.assertEqual(len(chain._futchain), len(chain.futures))


    def test_init_kwargs(self):
        chain1 = FutureChain(self.chain_tickers, self.ainfo)
        self.assertEqual('US.F.CL.M11.110520', chain1._futchain.iloc[0].name.ticker)

        chain = FutureChain(self.chain_tickers, self.ainfo,
                            rollover_days_before=3,
                            futures_months=[3, 6])
        self.assertEqual('US.F.CL.M11.110520', chain._futchain.iloc[0].name.ticker)
        self.assertTrue(chain1._futchain.iloc[0].date_end > chain._futchain.iloc[0].date_end)

        for i in range(1, len(chain._futchain)):
            row = chain._futchain.iloc[i]
            prev_row = chain._futchain.iloc[i - 1]
            fut = row.name

            self.assertTrue(fut.exp_month in [3, 6])
            self.assertEqual(True, row.date_end > row.date_start)
            self.assertEqual(True, row.date_start > prev_row.date_end)
            self.assertEqual(True, row.date_end < fut.exp_date)

        chain = FutureChain(self.chain_tickers, self.ainfo,
                            date_start=datetime(2012, 1, 1))
        self.assertEqual('US.F.CL.H12.120222', chain._futchain.iloc[0].name.ticker)

    def test_init_empty_or_none_tickers_list(self):
        self.assertRaises(ValueError, FutureChain, None, self.ainfo)
        self.assertRaises(ValueError, FutureChain, [], self.ainfo)

    def test_get_list(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        df = chain.get_list(datetime(2012, 5, 1))

        """'US.F.CL.G12.120120',
        'US.F.CL.H12.120222',
        'US.F.CL.J12.120321',
        'US.F.CL.K12.120420',
        'US.F.CL.M12.120522', +
        'US.F.CL.N12.120620',
        'US.F.CL.Q12.120720',
        'US.F.CL.U12.120822', +
        'US.F.CL.V12.120920',
        'US.F.CL.X12.121022',
        'US.F.CL.Z12.121120', +
        """
        self.assertEqual(3, len(df))
        self.assertEqual('US.F.CL.M12.120522', df.iloc[0].name.ticker)
        self.assertEqual(datetime(2012, 5, 18), df.iloc[0].date_end)
        self.assertEqual(datetime(2012, 2, 21), df.iloc[0].date_start)

        self.assertEqual('US.F.CL.U12.120822', df.iloc[1].name.ticker)
        self.assertEqual(datetime(2012, 8, 20), df.iloc[1].date_end)
        self.assertEqual(datetime(2012, 5, 21), df.iloc[1].date_start)

        self.assertEqual('US.F.CL.Z12.121120', df.iloc[2].name.ticker)
        self.assertEqual(datetime(2012, 11, 16), df.iloc[2].date_end)
        self.assertEqual(datetime(2012, 8, 21), df.iloc[2].date_start)

    def test_get_list_datepicking_check(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        df = chain.get_list(datetime(2012, 5, 18))

        """'US.F.CL.G12.120120',
        'US.F.CL.H12.120222',
        'US.F.CL.J12.120321',
        'US.F.CL.K12.120420',
        'US.F.CL.M12.120522', +
        'US.F.CL.N12.120620',
        'US.F.CL.Q12.120720',
        'US.F.CL.U12.120822', +
        'US.F.CL.V12.120920',
        'US.F.CL.X12.121022',
        'US.F.CL.Z12.121120', +
        """
        self.assertEqual(2, len(df))
        self.assertEqual('US.F.CL.U12.120822', df.iloc[0].name.ticker)
        self.assertEqual(datetime(2012, 8, 20), df.iloc[0].date_end)
        self.assertEqual(datetime(2012, 5, 21), df.iloc[0].date_start)

        self.assertEqual('US.F.CL.Z12.121120', df.iloc[1].name.ticker)
        self.assertEqual(datetime(2012, 11, 16), df.iloc[1].date_end)
        self.assertEqual(datetime(2012, 8, 21), df.iloc[1].date_start)



    def test_get_list_limit(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        df = chain.get_list(datetime(2012, 5, 1), limit=2)
        self.assertRaises(ValueError, chain.get_list, datetime(2012, 5, 1), limit=-2)

        """'US.F.CL.G12.120120',
        'US.F.CL.H12.120222',
        'US.F.CL.J12.120321',
        'US.F.CL.K12.120420',
        'US.F.CL.M12.120522', +
        'US.F.CL.N12.120620',
        'US.F.CL.Q12.120720',
        'US.F.CL.U12.120822', +
        'US.F.CL.V12.120920',
        'US.F.CL.X12.121022',
        'US.F.CL.Z12.121120', +
        """
        self.assertEqual(2, len(df))
        self.assertEqual('US.F.CL.M12.120522', df.iloc[0].name.ticker)
        self.assertEqual(datetime(2012, 5, 18), df.iloc[0].date_end)
        self.assertEqual(datetime(2012, 2, 21), df.iloc[0].date_start)

        self.assertEqual('US.F.CL.U12.120822', df.iloc[1].name.ticker)
        self.assertEqual(datetime(2012, 8, 20), df.iloc[1].date_end)
        self.assertEqual(datetime(2012, 5, 21), df.iloc[1].date_start)

    def test_get_list_offset(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        df = chain.get_list(datetime(2012, 5, 1), offset=1)

        self.assertRaises(ValueError, chain.get_list, datetime(2012, 5, 1), offset=-1)

        """'US.F.CL.G12.120120',
        'US.F.CL.H12.120222',
        'US.F.CL.J12.120321',
        'US.F.CL.K12.120420',
        'US.F.CL.M12.120522', +
        'US.F.CL.N12.120620',
        'US.F.CL.Q12.120720',
        'US.F.CL.U12.120822', +
        'US.F.CL.V12.120920',
        'US.F.CL.X12.121022',
        'US.F.CL.Z12.121120', +
        """
        self.assertEqual(2, len(df))
        self.assertEqual('US.F.CL.U12.120822', df.iloc[0].name.ticker)
        self.assertEqual(datetime(2012, 5, 18), df.iloc[0].date_end)
        self.assertEqual(datetime(2012, 2, 21), df.iloc[0].date_start)

        self.assertEqual('US.F.CL.Z12.121120', df.iloc[1].name.ticker)
        self.assertEqual(datetime(2012, 8, 20), df.iloc[1].date_end)
        self.assertEqual(datetime(2012, 5, 21), df.iloc[1].date_start)


        df = chain.get_list(datetime(2012, 5, 1), offset=1, limit=1)
        self.assertEqual(1, len(df))
        self.assertEqual('US.F.CL.U12.120822', df.iloc[0].name.ticker)
        self.assertEqual(datetime(2012, 5, 18), df.iloc[0].date_end)
        self.assertEqual(datetime(2012, 2, 21), df.iloc[0].date_start)

        self.assertRaises(ValueError, chain.get_list, datetime(2012, 5, 1), offset=3)

    def test_get(self):
        chain = FutureChain(self.chain_tickers, self.ainfo)

        self.assertEqual(True, isinstance(chain.get(datetime(2012, 5, 1)), FutureContract))
        self.assertEqual('US.F.CL.M12.120522', chain.get(datetime(2012, 5, 1)).ticker)
        self.assertEqual('US.F.CL.U12.120822', chain.get(datetime(2012, 5, 1), offset=1).ticker)
