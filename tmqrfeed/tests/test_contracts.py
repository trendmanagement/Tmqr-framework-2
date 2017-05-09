import unittest
from unittest import mock

from tmqrfeed.contracts import *
from tmqrfeed.manager import DataManager
from tmqrfeed.tests.shared_asset_info import ASSET_INFO


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

        self.assertRaises(NotImplementedError, contract.__getattribute__, 'data_source')

    def test_contractbase_delta(self):
        contract = ContractBase('US.S.AAPL')
        self.assertEqual(1.0, contract.delta(None))

    def test_contractbase_point_value(self):
        dm = mock.MagicMock(DataManager())

        with mock.patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            contract = ContractBase('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)

            mock_instrument_info.ticksize = 0.0
            mock_instrument_info.tickvalue = 1.0
            self.assertRaises(SettingsError, contract.__getattribute__, 'point_value')

            mock_instrument_info.ticksize = 1.0
            mock_instrument_info.tickvalue = 0.0
            self.assertRaises(SettingsError, contract.__getattribute__, 'point_value')

            mock_instrument_info.ticksize = 2.0
            mock_instrument_info.tickvalue = 23.0

            self.assertEqual(1 / 2.0 * 23.0, contract.point_value)

            # Caching
            mock_instrument_info.ticksize = 0.0
            mock_instrument_info.tickvalue = 0.0
            self.assertEqual(1 / 2.0 * 23.0, contract.point_value)

    def test_contractbase_dollar_pnl(self):
        dm = mock.MagicMock(DataManager())

        with mock.patch('tmqrfeed.contracts.ContractBase.instrument_info') as mock_instrument_info:
            contract = ContractBase('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            mock_instrument_info.ticksize = 2.0
            mock_instrument_info.tickvalue = 23.0

            self.assertEqual(1 / 2.0 * 23.0, contract.point_value)

            self.assertEqual((101.0 - 100.0) * -5.0 * (1.0 / 2.0 * 23.0), contract.dollar_pnl(100.0, 101.0, -5))




    def test_contractbase_magic_funcs(self):
        contract = ContractBase('US.S.AAPL')
        contract3 = ContractBase('US.S.AAPL')
        contract2 = ContractBase('US.S.BBPL')

        self.assertEqual(contract.__hash__(), contract.ticker.__hash__())
        self.assertEqual(contract.__eq__(contract3), True)
        self.assertEqual(contract.__gt__(contract2), False)
        self.assertEqual(contract.__lt__(contract2), True)
        self.assertEqual(contract.__str__(), contract.ticker)
        self.assertEqual(contract.__repr__(), contract.ticker)

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
        self.assertEqual(contract.expiration, datetime(1983, 5, 20))
        self.assertEqual(contract.expiration_month, 6)

    def test_futurecontract_get_month_by_letter(self):
        contract = FutureContract('US.F.CL.M83.830520')
        self.assertEqual(contract.expiration_month, 6)

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



    def test_instrument_info(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_instrument_info') as eng_ainfo:
            dm = DataManager()
            eng_ainfo.return_value = ASSET_INFO

            contract = FutureContract('US.F.ES.M83.830520', datamanager=dm)

            self.assertEqual(dm.datafeed.get_instrument_info('US.ES'), contract.instrument_info)
            self.assertEqual(12.5, contract.instrument_info.tickvalue)

    def test__str__repr__(self):
        contract = FutureContract('US.F.ES.M83.830520')
        self.assertEqual('US.F.ES.M83.830520', str(contract))
        self.assertEqual('US.F.ES.M83.830520', repr(contract))

    def test_quotes_source(self):
        with mock.patch('tmqrfeed.dataengines.DataEngineMongo.db_get_instrument_info') as eng_ainfo:
            dm = DataManager()
            eng_ainfo.return_value = ASSET_INFO

            contract = ContractBase('US.F.ES.M83.830520', datamanager=dm)
            self.assertRaises(NotImplementedError, contract.__getattribute__, 'data_source')

            contract = FutureContract('US.F.ES.M83.830520', datamanager=dm)
            self.assertEqual(SRC_INTRADAY, contract.data_source)

            option = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            self.assertEqual(SRC_OPTIONS_EOD, option.data_source)

    def test_deserialize(self):
        dm = mock.MagicMock(DataManager())

        c = ContractBase.deserialize('US.F.ES.M83.830520', dm)
        self.assertEqual(type(c), FutureContract)
        self.assertEqual(c.dm, dm)

        c = ContractBase.deserialize('US.C.F-ZB-H11-110322.110121@89.0', dm)
        self.assertEqual(type(c), OptionContract)
        self.assertEqual(c.dm, dm)

        c = ContractBase.deserialize('US.P.F-ZB-H11-110322.110121@89.0', dm)
        self.assertEqual(type(c), OptionContract)
        self.assertEqual(c.dm, dm)

        c = ContractBase.deserialize('US.S.AAPL', dm)
        self.assertEqual(type(c), ContractBase)
        self.assertEqual(c.dm, dm)

        self.assertRaises(ArgumentError, ContractBase.deserialize, 'US')
        self.assertRaises(ArgumentError, ContractBase.deserialize, 'US..AAPL')
        self.assertRaises(ArgumentError, ContractBase.deserialize, 'US.   .AAPL')
        self.assertRaises(ArgumentError, ContractBase.deserialize, 'US.AAPL')

    def test_to_expiry_days(self):
        dm = mock.MagicMock(DataManager())

        c = ContractBase('US.S.AAPL', dm)

        self.assertEqual(c.to_expiration_days(datetime.now()), 1000000000)

    def test_contractbase_price(self):
        dm = mock.MagicMock(DataManager())
        dm.price_get.return_value = 100

        c = ContractBase('US.S.AAPL', dm)

        self.assertEqual(c.price(datetime(2011, 1, 1)), 100)

    def test_contractbase_risk_free_rate(self):
        dm = mock.MagicMock(DataManager())
        dm.riskfreerate_get.return_value = 100

        c = ContractBase('US.S.AAPL', dm)

        self.assertEqual(c.risk_free_rate(datetime(2011, 1, 1)), 100)
