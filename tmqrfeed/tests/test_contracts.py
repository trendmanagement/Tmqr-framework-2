import unittest
from tmqrfeed.contracts import *
from datetime import datetime

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
        self.assertRaises(ValueError, ContractBase, 'US.AAPL')


    def test_contractbase_parse_ticker(self):
        contract = ContractBase('US.S.AAPL')
        self.assertEqual(contract._parse('US.S.AAPL'), ['US', 'S', 'AAPL'])
        self.assertEqual(contract._parse('US.F.CL.M83.830520'), 'US.F.CL.M83.830520'.split('.'))
        self.assertEqual(contract._parse('US.C.F-ZB-H11-110322.110121@89.0'), ['US', 'C', 'F-ZB-H11-110322', '110121', '89.0'])

    def test_futurecontract_init(self):
        contract = FutureContract('US.F.CL.M83.830520')
        self.assertEqual(contract.ctype, 'F')
        self.assertEqual(contract.name, 'CLM83')
        self.assertEqual(contract.instrument, 'US.CL')
        self.assertEqual(contract.instrument, contract.underlying)
        self.assertEqual(contract.expiration, datetime(1983, 5, 20))

    def test_futurecontract_wrong_ctype_or_tockens_count(self):
        self.assertRaises(ValueError, FutureContract, 'US.S.AAPL')
        self.assertRaises(ValueError, FutureContract, 'US.F.CLM83.830520')


    def test_futurecontract_parse_expiration(self):
        self.assertRaises(ValueError, FutureContract._parse_expiration, 'xxx')
        self.assertRaises(ValueError, FutureContract._parse_expiration, '59032x')
        self.assertRaises(ValueError, FutureContract._parse_expiration, '592320')

        self.assertEquals(datetime(1983, 5, 20), FutureContract._parse_expiration('830520'))
        self.assertEquals(datetime(2013, 5, 20), FutureContract._parse_expiration('130520'))
        self.assertEquals(datetime(2049, 5, 20), FutureContract._parse_expiration('490520'))
        self.assertEquals(datetime(1950, 5, 20), FutureContract._parse_expiration('500520'))

    def test_optioncontract_init(self):
        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0')
        self.assertEqual(contract.ctype, 'C')
        self.assertEqual(contract.name, 'ZBH11.110121@89.0')
        self.assertEqual(contract.instrument, 'US.ZB')
        self.assertEqual(contract.underlying.ticker, 'US.F.ZB.H11.110322')
        self.assertEqual(contract.expiration, datetime(2011, 1, 21))
        self.assertEqual(contract.strike, 89.0)

        self.assertRaises(ValueError, OptionContract, 'US.C.F-ZB-H11-110322.XX.110121@89.0')
        self.assertRaises(ValueError, OptionContract, 'US.F.F-ZB-H11-110322.110121@89.0')

    def test_optioncontract_underlying(self):
        contract = OptionContract('US.C.S-AAPL.110121@89.0')
        self.assertEqual(contract.ctype, 'C')
        self.assertEqual(contract.name, 'AAPL.110121@89.0')
        self.assertEqual(contract.instrument, 'US.AAPL')
        self.assertEqual(contract.underlying.ticker, 'US.S.AAPL')
        self.assertEqual(True, isinstance(contract.underlying, ContractBase))
