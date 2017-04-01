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
        self.assertEqual(contract.expiration, datetime(2011, 1, 21))
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

    def test_get_pricing_context(self):
        def dm_price_get_sideeffect(asset, date):
            if isinstance(asset, FutureContract):
                return 500.0, 501.0
            if isinstance(asset, OptionContract):
                if asset.ctype == 'C':
                    return 0.25, 0.26
                else:
                    return 0.15, 0.16

        dm = mock.MagicMock(DataManager())
        dm.price_get.side_effect = dm_price_get_sideeffect

        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        self.assertEqual(None, contract._pricing_context)

        dt = datetime(2012, 1, 1)
        context = contract.get_pricing_context(dt)
        self.assertEqual(context, (datetime(2012, 1, 1), 500, 501, 0.25, 0.26, 0.0))

        # Check cached
        contract.set_pricing_context(datetime(2011, 1, 1), 100, 101, 0.4, 0.3, 0.04)
        context = contract.get_pricing_context(datetime(2011, 1, 1))
        self.assertEqual(context, (datetime(2011, 1, 1), 100, 101, 0.4, 0.3, 0.04))

        # Rewrite if date is different
        context = contract.get_pricing_context(dt)
        self.assertEqual(context, (datetime(2012, 1, 1), 500, 501, 0.25, 0.26, 0.0))
        self.assertEqual((datetime(2012, 1, 1), 500, 501, 0.25, 0.26, 0.0), contract._pricing_context)

    def test_to_expiration_days(self):
        dm = mock.MagicMock(DataManager())
        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)

        dt = datetime(2011, 1, 20)
        self.assertEqual(contract.to_expiration_days(dt), 1)

        dt = datetime(2011, 1, 20, 12, 2)
        self.assertEqual(contract.to_expiration_days(dt), 1)

    def test_to_expiration_years(self):
        dm = mock.MagicMock(DataManager())
        contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
        self.assertEqual(contract.to_expiration_years_from_days(1), (1 * 24.0 * 60 * 60) / 31536000.0)

    def test__calc_price(self):
        dm = mock.MagicMock(DataManager())

        with mock.patch('tmqrfeed.contracts.blackscholes') as mock_blacksholes:
            contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            contract._calc_price(100, 20, 0.001, 0.23)
            self.assertEqual(True, mock_blacksholes.called)
            self.assertEqual(mock_blacksholes.call_args[0], (1,
                                                             100,
                                                             89.0,
                                                             contract.to_expiration_years_from_days(20),
                                                             0.001,
                                                             0.23
                                                             ))

            mock_blacksholes.reset_mock()
            contract = OptionContract('US.P.F-ZB-H11-110322.110121@89.0', datamanager=dm)
            contract._calc_price(100, 20, 0.001, 0.23)
            self.assertEqual(True, mock_blacksholes.called)
            self.assertEqual(mock_blacksholes.call_args[0], (0,
                                                             100,
                                                             89.0,
                                                             contract.to_expiration_years_from_days(20),
                                                             0.001,
                                                             0.23
                                                             ))

    def test_price(self):
        dm = mock.MagicMock(DataManager())

        def sideeffect__calc_price(ulprice, days_to_expiration, rfr, iv):
            return iv

        with mock.patch('tmqrfeed.contracts.OptionContract.get_pricing_context') as mock_get_price_context:
            mock_get_price_context.return_value = (datetime(2011, 1, 20), 500, 501, 0.25, 0.26, 0.001)

            with mock.patch('tmqrfeed.contracts.OptionContract._calc_price') as mock__calc_price:
                contract = OptionContract('US.C.F-ZB-H11-110322.110121@89.0', datamanager=dm)
                mock__calc_price.side_effect = sideeffect__calc_price

                # Regular pricing
                mock__calc_price.reset_mock()
                decision_px, exec_px = contract.price(datetime(2011, 1, 20))
                self.assertEqual(decision_px, 0.25)
                self.assertEqual(exec_px, 0.26)
                self.assertEqual(2, len(mock__calc_price.call_args_list))
                self.assertEqual((500, 1, 0.001, 0.25), mock__calc_price.call_args_list[0][0])
                self.assertEqual((501, 1, 0.001, 0.26), mock__calc_price.call_args_list[1][0])

                # Custom UL price
                mock__calc_price.reset_mock()
                decision_px, exec_px = contract.price(datetime(2011, 1, 20), ulprice=200)
                self.assertEqual(decision_px, 0.25)
                self.assertEqual(exec_px, 0.26)
                self.assertEqual(2, len(mock__calc_price.call_args_list))
                self.assertEqual((200, 1, 0.001, 0.25), mock__calc_price.call_args_list[0][0])
                self.assertEqual((200, 1, 0.001, 0.26), mock__calc_price.call_args_list[1][0])

                # Custom days to exp
                mock__calc_price.reset_mock()
                decision_px, exec_px = contract.price(datetime(2011, 1, 20), days_to_expiration=20)
                self.assertEqual(decision_px, 0.25)
                self.assertEqual(exec_px, 0.26)
                self.assertEqual(2, len(mock__calc_price.call_args_list))
                self.assertEqual((500, 20, 0.001, 0.25), mock__calc_price.call_args_list[0][0])
                self.assertEqual((501, 20, 0.001, 0.26), mock__calc_price.call_args_list[1][0])

                # Custom risk free rate
                mock__calc_price.reset_mock()
                decision_px, exec_px = contract.price(datetime(2011, 1, 20), riskfreerate=0.1)
                self.assertEqual(decision_px, 0.25)
                self.assertEqual(exec_px, 0.26)
                self.assertEqual(2, len(mock__calc_price.call_args_list))
                self.assertEqual((500, 1, 0.1, 0.25), mock__calc_price.call_args_list[0][0])
                self.assertEqual((501, 1, 0.1, 0.26), mock__calc_price.call_args_list[1][0])

                # Custom IV change
                mock__calc_price.reset_mock()
                decision_px, exec_px = contract.price(datetime(2011, 1, 20), iv_change=-0.1)
                self.assertEqual(decision_px, 0.15)
                self.assertEqual(exec_px, 0.16)
                self.assertEqual(2, len(mock__calc_price.call_args_list))
                self.assertEqual((500, 1, 0.001, 0.15), mock__calc_price.call_args_list[0][0])
                self.assertEqual((501, 1, 0.001, 0.16), mock__calc_price.call_args_list[1][0])
