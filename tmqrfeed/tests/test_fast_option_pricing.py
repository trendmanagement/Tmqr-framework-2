import unittest
from  datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytz
import pyximport

from tmqr.errors import *

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.fast_option_pricing import blackscholes, blackscholes_greeks, GREEK_DELTA


class FastOptionsPricingTestCase(unittest.TestCase):
    def test_greeks(self):
        self.assertEqual(GREEK_DELTA, 0)

        self.assertEqual((1,), blackscholes_greeks(1, 110, 100, 0, 0, 0.1))
        self.assertEqual((0,), blackscholes_greeks(1, 90, 100, 0, 0, 0.1))
        self.assertEqual((-1,), blackscholes_greeks(0, 90, 100, 0, 0, 0.1))
        self.assertEqual((0,), blackscholes_greeks(0, 110, 100, 0, 0, 0.1))

        # TODO: check why ATM delta != 0.5 !!!
        # self.assertEqual(-0.5, blackscholes_greeks(0, 100, 100, 0.23, 0, 0.1))
        # self.assertEqual(0.5, blackscholes_greeks(1, 100, 100, 0.23, 0, 0.1))
