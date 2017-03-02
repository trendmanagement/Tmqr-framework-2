import unittest
from unittest import mock

from tmqrfeed.contracts import *
from tmqrfeed.datafeed import DataFeed


class ContractsTestCase(unittest.TestCase):
    def test_contractbase_init(self):
        contract = ContractBase('US.S.AAPL')
        self.assertEqual(contract.ticker, 'US.S.AAPL')
        self.assertEqual(contract._toks, ['US', 'S', 'AAPL'])
        self.assertEqual(contract.market, 'US')
        self.assertEqual(contract.ctype, 'S')
        self.assertEqual(contract.instrument, 'US.AAPL')
        self.assertEqual(contract.name, 'AAPL')
        self.assertEqual(str(contract), contract.ticker)

    def test_contractbase_toshort_contract(self):
        self.assertRaises(ArgumentError, ContractBase, 'US.AAPL')

    def test_contractbase_parse_ticker(self):
        contract = ContractBase('US.S.AAPL')
        self.assertEqual(contract._parse('US.S.AAPL'), ['US', 'S', 'AAPL'])
        self.assertEqual(contract._parse('US.F.CL.M83.830520'), 'US.F.CL.M83.830520'.split('.'))
        self.assertEqual(contract._parse('US.C.F-ZB-H11-110322.110121@89.0'),
                         ['US', 'C', 'F-ZB-H11-110322', '110121', '89.0'])

    def test_futurecontract_init(self):
        contract = FutureContract('US.F.CL.M83.830520')
        self.assertEqual(contract.ctype, 'F')
        self.assertEqual(contract.name, 'CLM83')
        self.assertEqual(contract.instrument, 'US.CL')
        self.assertEqual(contract.instrument, contract.underlying)
        self.assertEqual(contract.exp_date, datetime(1983, 5, 20))
        self.assertEqual(contract.exp_month, 6)

    def test_futurecontract_get_month_by_letter(self):
        contract = FutureContract('US.F.CL.M83.830520')
        self.assertEqual(contract.exp_month, 6)

        """
        http://www.cmegroup.com/month-codes.html
        January	F
        February	G
        March	H
        April	J
        May	K
        June	M
        July	N
        August	Q
        September	U
        October	V
        November	X
        December	Z

        """
        self.assertEqual(contract._get_month_by_code('f'), 1)
        self.assertEqual(contract._get_month_by_code('g'), 2)
        self.assertEqual(contract._get_month_by_code('H'), 3)
        self.assertEqual(contract._get_month_by_code('J'), 4)
        self.assertEqual(contract._get_month_by_code('K'), 5)
        self.assertEqual(contract._get_month_by_code('M'), 6)
        self.assertEqual(contract._get_month_by_code('N'), 7)
        self.assertEqual(contract._get_month_by_code('Q'), 8)
        self.assertEqual(contract._get_month_by_code('U'), 9)
        self.assertEqual(contract._get_month_by_code('V'), 10)
        self.assertEqual(contract._get_month_by_code('X'), 11)
        self.assertEqual(contract._get_month_by_code('Z'), 12)
        self.assertRaises(KeyError, contract._get_month_by_code, 'A')

    def test_futurecontract_wrong_ctype_or_tockens_count(self):
        self.assertRaises(ArgumentError, FutureContract, 'US.S.AAPL')
        self.assertRaises(ArgumentError, FutureContract, 'US.F.CLM83.830520')

    def test_futurecontract_parse_expiration(self):
        contract = FutureContract('US.F.CL.M83.830520')
        self.assertRaises(ArgumentError, contract._parse_expiration, 'xxx')
        self.assertRaises(ArgumentError, contract._parse_expiration, '59032x')
        self.assertRaises(ArgumentError, contract._parse_expiration, '592320')

        self.assertEquals(datetime(1983, 5, 20), contract._parse_expiration('830520'))
        self.assertEquals(datetime(2013, 5, 20), contract._parse_expiration('130520'))
        self.assertEquals(datetime(2049, 5, 20), contract._parse_expiration('490520'))
        self.assertEquals(datetime(1950, 5, 20), contract._parse_expiration('500520'))

    def test_optioncontract_init(self):
        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0')
        self.assertEqual(contract.ctype, 'C')
        self.assertEqual(contract.name, 'ZBH11.110121@89.0')
        self.assertEqual(contract.instrument, 'US.ZB')
        self.assertEqual(contract.underlying.ticker, 'US.F.ZB.H11.110322')
        self.assertEqual(contract.exp_date, datetime(2011, 1, 21))
        self.assertEqual(contract.strike, 89.0)

        self.assertRaises(ArgumentError, OptionContract, 'US.C.F-ZB-H11-110322.XX.110121@89.0')
        self.assertRaises(ArgumentError, OptionContract, 'US.F.F-ZB-H11-110322.110121@89.0')

    def test_optioncontract_underlying(self):
        contract = OptionContract('US.C.S-AAPL.110121@89.0')
        self.assertEqual(contract.ctype, 'C')
        self.assertEqual(contract.name, 'AAPL.110121@89.0')
        self.assertEqual(contract.instrument, 'US.AAPL')
        self.assertEqual(contract.underlying.ticker, 'US.S.AAPL')
        self.assertEqual(True, isinstance(contract.underlying, ContractBase))

    def test_contract_info(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_contract_info') as eng_ainfo:
            feed = DataFeed()
            contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datafeed=feed)

            eng_ainfo.return_value = {
                "extra_data": {
                    "name": "C.US.USAG118900",
                    "year": 2011,
                    "monthint": 2,
                    "month": "G",
                    "sqlid": 1.0
                },
                "optcode": "",
                "underlying": "US.F.ZB.H11.110322",
                "mkt": "US",
                "type": "C",
                "tckr": "US.C.F-ZB-H11-110322.110121@89.0",
                "instr": "US.ZB",
                "exp": datetime(2011, 1, 21),
                "strike": 89.0,
                "opttype": "C"
            }

            self.assertEqual(1.0, contract.contract_info.extra('sqlid'))

    def test_instrument_info(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_instrument_info') as eng_ainfo:
            feed = DataFeed()
            eng_ainfo.return_value = {
                'futures_months': [3, 6, 9, 12],
                'instrument': 'US.ES',
                'market': 'US',
                'rollover_days_before': 2,
                'ticksize': 0.25,
                'tickvalue': 12.5,
                'timezone': 'US/Pacific',
                'trading_session': [{
                    'decision': '10:40',
                    'dt': datetime(1900, 1, 1, 0, 0),
                    'execution': '10:45',
                    'start': '00:32'}]}

            contract = FutureContract('US.F.ES.M83.830520', datafeed=feed)

            self.assertEqual(feed.get_instrument_info('US.ES'), contract.instrument_info)
            self.assertEqual(12.5, contract.instrument_info.tickvalue)

    def test__str__repr__(self):
        contract = FutureContract('US.F.ES.M83.830520')
        self.assertEqual('US.F.ES.M83.830520', str(contract))
        self.assertEqual('US.F.ES.M83.830520', repr(contract))
