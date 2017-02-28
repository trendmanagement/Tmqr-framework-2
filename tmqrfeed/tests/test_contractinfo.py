import unittest
from datetime import datetime

from tmqrfeed.contractinfo import *
from tmqrfeed.contracts import OptionContract, FutureContract


class ContractInfoTestCase(unittest.TestCase):
    def setUp(self):
        self.info = {
            "extra_data": {
                "name": "F.US.CLEQ83",
                "year": 1983.0,
                "monthint": 8,
                "month": "Q",
                "sqlid": 3.0
            },
            "underlying": "US.CL",
            "type": "F",
            "contr": "CL.Q83",
            "tckr": "US.F.CL.Q83.830720",
            "instr": "US.CL",
            "exp": datetime(1983, 7, 20),
            "mkt": "US"
        }

        self.info_no_extra = {

            "underlying": "US.CL",
            "type": "F",
            "contr": "CL.Q83",
            "tckr": "US.F.CL.Q83.830720",
            "instr": "US.CL",
            "exp": datetime(1983, 7, 20),
            "mkt": "US"
        }

        self.info_option = {
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

    def test_init(self):
        ci = ContractInfo(self.info)
        self.assertEqual(ci.ticker, "US.F.CL.Q83.830720")
        self.assertEqual(ci.ctype, 'F')
        self.assertEqual(ci.instrument, 'US.CL')
        self.assertEqual(ci.underlying, 'US.CL')
        self.assertEqual(ci.market, 'US')
        self.assertEqual(ci.exp_date, datetime(1983, 7, 20))

    def test_init_bad_values(self):
        self.assertRaises(ValueError, ContractInfo, None)
        self.assertRaises(ValueError, ContractInfo, {})

    def test_extra(self):
        ci = ContractInfo(self.info)
        self.assertEqual("F.US.CLEQ83", ci.extra('name'))
        self.assertEqual(None, ci.extra('name_some_not_exists', default=None))
        # Raises exception by default
        self.assertRaises(ContractInfoNotFound, ci.extra, 'name_some_not_exists')

        ci = ContractInfo(self.info_no_extra)
        self.assertRaises(ContractInfoNotFound, ci.extra, 'name_some_not_exists')
        self.assertEqual(None, ci.extra('name_some_not_exists', default=None))

    def test_not_applicable_fields(self):
        ci = ContractInfo(self.info)

        def _get_strike():
            return ci.strike

        self.assertRaises(ContractInfoNotApplicable, _get_strike)

        def _get_opt_type():
            return ci.opt_type

        self.assertRaises(ContractInfoNotApplicable, _get_opt_type)

    def test_strike_and_opttype(self):
        ci = ContractInfo(self.info_option)
        self.assertEqual(ci.ctype, "C")
        self.assertEqual(ci.opt_type, "C")
        self.assertEqual(ci.strike, 89.0)

    def test_check_integrity_good(self):
        info_dic = {
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

        ci = ContractInfo(info_dic)

        self.assertEqual(True, ci.check_integrity(OptionContract("US.C.F-ZB-H11-110322.110121@89.0")))

    def test_check_integrity_strike(self):
        info_dic = {
            "optcode": "",
            "underlying": "US.F.ZB.H11.110322",
            "mkt": "US",
            "type": "C",
            "tckr": "US.C.F-ZB-H11-110322.110121@89.0",
            "instr": "US.ZB",
            "exp": datetime(2011, 1, 21),
            "strike": 80.0,
            "opttype": "C"
        }

        ci = ContractInfo(info_dic)

        # Ticker mismatch
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          OptionContract("US.C.F-ZB-H11-110322.110121@89.0"))

    def test_check_integrity_ctype(self):
        info_dic = {
            "optcode": "",
            "underlying": "US.F.ZB.H11.110322",
            "mkt": "US",
            "type": "P",
            "tckr": "US.C.F-ZB-H11-110322.110121@89.0",
            "instr": "US.ZB",
            "exp": datetime(2011, 1, 21),
            "strike": 89.0,
            "opttype": "C"
        }

        ci = ContractInfo(info_dic)

        # Ticker mismatch
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          OptionContract("US.C.F-ZB-H11-110322.110121@89.0"))

    def test_check_integrity_expdate(self):
        info_dic = {
            "optcode": "",
            "underlying": "US.F.ZB.H11.110322",
            "mkt": "US",
            "type": "C",
            "tckr": "US.C.F-ZB-H11-110322.110121@89.0",
            "instr": "US.ZB",
            "exp": datetime(2011, 1, 22),
            "strike": 89.0,
            "opttype": "C"
        }

        ci = ContractInfo(info_dic)

        # Ticker mismatch
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          OptionContract("US.C.F-ZB-H11-110322.110121@89.0"))

        info_no_extra = {

            "underlying": "US.CL",
            "type": "F",
            "contr": "CL.Q83",
            "tckr": "US.F.CL.Q83.830720",
            "instr": "US.CL",
            "exp": datetime(1983, 7, 21),
            "mkt": "US"
        }
        ci = ContractInfo(info_no_extra)
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          FutureContract("US.F.CL.Q83.830720"))

    def test_check_integrity_ticker_mismatch(self):
        info_dic = {
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

        ci = ContractInfo(info_dic)

        # Ticker mismatch
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          OptionContract("US.C.F-ZB-H11-110322.110121@8.0"))

    def test_check_integrity_instrument_mismatch(self):
        info_dic = {
            "optcode": "",
            "underlying": "US.F.ZB.H11.110322",
            "mkt": "US",
            "type": "C",
            "tckr": "US.C.F-ZB-H11-110322.110121@89.0",
            "instr": "US.ZC",
            "exp": datetime(2011, 1, 21),
            "strike": 89.0,
            "opttype": "C"
        }

        ci = ContractInfo(info_dic)

        # Ticker mismatch
        self.assertRaises(ContractInfoIntegrityError, ci.check_integrity,
                          OptionContract("US.C.F-ZB-H11-110322.110121@89.0"))
