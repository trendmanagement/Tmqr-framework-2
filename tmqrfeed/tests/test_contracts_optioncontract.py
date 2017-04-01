import unittest
from unittest import mock

from tmqrfeed.contracts import *
from tmqrfeed.manager import DataManager


class OptionContractTestCase(unittest.TestCase):
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
            dm = DataManager()
            contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)

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

    def test_set_pricing_context(self):
        dm = DataManager()
        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        self.assertEqual(None, contract._pricing_context)

        contract.set_pricing_context(datetime(2011, 1, 1), 100, 101, 0.4, 0.3, 0.04)

        self.assertEqual((datetime(2011, 1, 1), 100, 101, 0.4, 0.3, 0.04), contract._pricing_context)
