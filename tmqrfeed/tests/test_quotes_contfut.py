import numpy as np

try:
    from tmqr.settings_local import *
except:
    pass
import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()})

from tmqrfeed.datafeed import DataFeed
import unittest
from tmqrfeed.quotes.quote_contfut import QuoteContFut


class QuoteContFutTestCase(unittest.TestCase):
    def test_build(self):
        feed = DataFeed()
        qcont_fut = QuoteContFut('US.CL', datafeed=feed, timeframe='D')
        qcont_fut.build()
