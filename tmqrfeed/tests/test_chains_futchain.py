import unittest
import pandas as pd
from tmqr.errors import *
from tmqr.settings import *
from tmqrfeed.chains import FutureChain
from tmqrfeed.contracts import FutureContract
from tmqrfeed.instrumentinfo import InstrumentInfo
from tmqrfeed.tests.shared_asset_info import ASSET_INFO



class FutChainTestCase(unittest.TestCase):
    def setUp(self):
        self.info_dic = ASSET_INFO
        self.ainfo = InstrumentInfo(self.info_dic)
        self.tickers = ['US.F.CL.G11.110120',
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
        self.chain_tickers = [x for x in self.tickers]
        self.chain = FutureChain(self.chain_tickers, 'DM', rollover_days_before=2,
                                 futures_months=[3, 6, 9, 12])

    def test_init(self):

        self.assertEqual('US.F.CL.M11.110520', self.chain._futchain[0][0])
        for i in range(1, len(self.chain._futchain)):
            row = self.chain._futchain[i]
            prev_row = self.chain._futchain[i - 1]
            fut = row[0]

            self.assertTrue(fut.expiration_month in [3, 6, 9, 12])
            self.assertEqual(True, row[2] > row[1])
            self.assertEqual(True, row[1] == prev_row[2])
            self.assertEqual(True, row[2] < fut.expiration.date())

        self.assertRaises(ArgumentError, FutureChain, self.chain_tickers, None, rollover_days_before=2,
                          futures_months=[3, 6, 9, 12])

        self.assertRaises(ArgumentError, FutureChain, self.chain_tickers, 'DM', rollover_days_before=None,
                          futures_months=[3, 6, 9, 12])

        self.assertRaises(ArgumentError, FutureChain, self.chain_tickers, 'DM', rollover_days_before=2,
                          futures_months=None)

    def test_futures(self):
        self.assertEqual(len(self.chain._futchain), len(self.chain.get_all()))

    def test_init_kwargs(self):
        chain1 = FutureChain(self.chain_tickers, 'DM', rollover_days_before=2,
                             futures_months=[3, 6, 9, 12])
        self.assertEqual('US.F.CL.M11.110520', chain1._futchain[0][0])

        chain = FutureChain(self.chain_tickers, 'DM',
                            rollover_days_before=3,
                            futures_months=[3, 6])
        self.assertEqual('US.F.CL.M11.110520', chain._futchain[0][0])
        self.assertTrue(chain1._futchain[0][2] > chain._futchain[0][2])

        for i in range(1, len(chain._futchain)):
            row = chain._futchain[i]
            prev_row = chain._futchain[i - 1]
            fut = row[0]

            self.assertTrue(fut.expiration_month in [3, 6])
            self.assertEqual(True, row[2] > row[1])
            self.assertEqual(True, row[1] == prev_row[2])
            self.assertEqual(True, row[2] < fut.expiration.date())


    def test_init_empty_or_none_tickers_list(self):
        self.assertRaises(ArgumentError, FutureChain, None, 'DM', rollover_days_before=3,
                          futures_months=[3, 6])
        self.assertRaises(ArgumentError, FutureChain, [], 'DM', rollover_days_before=3,
                          futures_months=[3, 6])

    def test_bisect(self):

        date = datetime(2012, 1, 1)
        fut_idx = self.chain.bisect_right(self.chain._futchain, date.date())
        self.assertEqual(('US.F.CL.H12.120222', pd.Timestamp('2011-11-17 00:00:00').date(),
                          pd.Timestamp('2012-02-20 00:00:00').date()),
                         self.chain._futchain[fut_idx]
                         )

    def test_get_list(self):

        clist = self.chain.get_list(datetime(2012, 5, 1))

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
        self.assertEqual(3, len(clist))
        self.assertEqual('US.F.CL.M12.120522', clist[0][0])
        self.assertEqual(datetime(2012, 5, 18).date(), clist[0][2])
        self.assertEqual(datetime(2012, 2, 20).date(), clist[0][1])

        self.assertEqual('US.F.CL.U12.120822', clist[1][0])
        self.assertEqual(datetime(2012, 8, 20).date(), clist[1][2])
        self.assertEqual(datetime(2012, 5, 18).date(), clist[1][1])

        self.assertEqual('US.F.CL.Z12.121120', clist[2][0])
        self.assertEqual(datetime(2012, 11, 16).date(), clist[2][2])
        self.assertEqual(datetime(2012, 8, 20).date(), clist[2][1])

    def test_get_list_datepicking_check(self):

        df = self.chain.get_list(datetime(2012, 5, 18))

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
        self.assertEqual('US.F.CL.U12.120822', df[0][0])
        self.assertEqual(datetime(2012, 8, 20).date(), df[0][2])
        self.assertEqual(datetime(2012, 5, 18).date(), df[0][1])

        self.assertEqual('US.F.CL.Z12.121120', df[1][0])
        self.assertEqual(datetime(2012, 11, 16).date(), df[1][2])
        self.assertEqual(datetime(2012, 8, 20).date(), df[1][1])

    def test_get_list_out_of_date(self):

        self.assertRaises(ChainNotFoundError, self.chain.get_list, datetime(2212, 5, 18))

    def test_get_list_limit(self):

        df = self.chain.get_list(datetime(2012, 5, 1), limit=2)
        self.assertRaises(ArgumentError, self.chain.get_list, datetime(2012, 5, 1), limit=-2)

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
        self.assertEqual('US.F.CL.M12.120522', df[0][0])
        self.assertEqual(datetime(2012, 5, 18).date(), df[0][2])
        self.assertEqual(datetime(2012, 2, 20).date(), df[0][1])

        self.assertEqual('US.F.CL.U12.120822', df[1][0])
        self.assertEqual(datetime(2012, 8, 20).date(), df[1][2])
        self.assertEqual(datetime(2012, 5, 18).date(), df[1][1])

    def test_get_list_offset(self):

        df = self.chain.get_list(datetime(2012, 5, 1), offset=1)

        self.assertRaises(ArgumentError, self.chain.get_list, datetime(2012, 5, 1), offset=-1)

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
        self.assertEqual('US.F.CL.U12.120822', df[0][0])
        self.assertEqual(datetime(2012, 8, 20).date(), df[0][2])
        self.assertEqual(datetime(2012, 5, 18).date(), df[0][1])

        self.assertEqual('US.F.CL.Z12.121120', df[1][0])
        self.assertEqual(datetime(2012, 11, 16).date(), df[1][2])
        self.assertEqual(datetime(2012, 8, 20).date(), df[1][1])

        df = self.chain.get_list(datetime(2012, 5, 1), offset=1, limit=1)
        self.assertEqual(1, len(df))
        self.assertEqual('US.F.CL.U12.120822', df[0][0])
        self.assertEqual(datetime(2012, 8, 20).date(), df[0][2])
        self.assertEqual(datetime(2012, 5, 18).date(), df[0][1])

        self.assertRaises(ChainNotFoundError, self.chain.get_list, datetime(2012, 5, 1), offset=3)

    def test_get(self):

        self.assertEqual(True, isinstance(self.chain.get_contract(datetime(2012, 5, 1)), FutureContract))
        self.assertEqual('US.F.CL.M12.120522', self.chain.get_contract(datetime(2012, 5, 1)).ticker)
        self.assertEqual('US.F.CL.U12.120822', self.chain.get_contract(datetime(2012, 5, 1), offset=1).ticker)
