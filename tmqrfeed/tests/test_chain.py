import unittest
from tmqrfeed.chains import FutureChain


class FutChainTestCase(unittest.TestCase):
    def test_init(self):
        tickers = ['US.F.CL.H83.830320', 'US.F.CL.M83.830520']
        chain = FutureChain(tickers)
        self.assertEqual(len(chain), 2)
        self.assertEqual(chain.futures[0].ticker, 'US.F.CL.H83.830320')
        self.assertEqual(chain.futures[1].ticker, 'US.F.CL.M83.830520')
