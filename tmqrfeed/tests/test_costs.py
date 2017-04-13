import unittest
from tmqrfeed.costs import Costs
from tmqrfeed.contracts import ContractBase


class CostsTestCase(unittest.TestCase):
    def test_init_defaults(self):
        c = Costs()
        self.assertEqual(c.per_contract, 0.0)
        self.assertEqual(c.per_option, 0.0)

    def test_init_arguments(self):
        c = Costs(10, 20)
        self.assertEqual(c.per_contract, 10.0)
        self.assertEqual(c.per_option, 20.0)

    def test_calc_costs(self):
        fut = ContractBase("US.S.AAPL")
        fut.ctype = 'F'

        opt1 = ContractBase("US.C.AAPL")
        opt1.ctype = 'C'

        opt2 = ContractBase("US.P.AAPL")
        opt2.ctype = 'P'

        self.assertEqual(-10 * 10, Costs(10, 20).calc_costs(fut, 10))
        self.assertEqual(-10 * 10, Costs(10, 20).calc_costs(fut, -10))
        self.assertEqual(-10 * 10, Costs(-10, 20).calc_costs(fut, -10))
        self.assertEqual(-10 * 10, Costs(-10, 20).calc_costs(fut, 10))

        self.assertEqual(-20 * 10, Costs(10, 20).calc_costs(opt1, 10))
        self.assertEqual(-20 * 10, Costs(10, 20).calc_costs(opt1, -10))
        self.assertEqual(-20 * 10, Costs(-10, 20).calc_costs(opt1, -10))
        self.assertEqual(-20 * 10, Costs(-10, 20).calc_costs(opt1, 10))

        self.assertEqual(-20 * 10, Costs(-10, 20).calc_costs(opt2, 10))
