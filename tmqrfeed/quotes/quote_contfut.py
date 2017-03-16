import numpy as np

from tmqr.errors import *
from tmqrfeed.quotes.quote_base import QuoteBase

FNAN = float('nan')

class QuoteContFut(QuoteBase):
    """
    Continuous futures building quote engine
    """

    def __init__(self, instrument, **kwargs):
        self.datafeed = kwargs.get('datafeed', None)
        if self.datafeed is None:
            raise ArgumentError("'datafeed' kwarg is not set")

        self.timeframe = kwargs.get('timeframe', None)
        self.fut_offset = kwargs.get('fut_offset', 0)
        self.date_start = kwargs.get('date_start', self.datafeed.date_start)
        self.date_end = kwargs.get('date_end', None)

        if self.timeframe is None:
            raise ArgumentError("'timeframe' kwarg is not set")

        self.instrument = instrument

    def ohlc_resampler(self, x):
        if x.name == 'o':
            if len(x) == 0:
                return FNAN
            else:
                return x[0]
        if x.name == 'h':
            return np.max(x)
        if x.name == 'l':
            return np.min(x)
        if x.name == 'c':
            if len(x) == 0:
                return FNAN
            else:
                return x[-1]
        if x.name == 'v':
            return np.sum(x)

        return FNAN

    def build(self):
        # Get futures chain
        fut_chain = self.datafeed.get_fut_chain(self.instrument)

        # Create contracts list
        chain_values = fut_chain.get_list(self.date_start, offset=self.fut_offset)

        # Build price series
        # 1. Iterate chains
        df_data = []
        for row in chain_values.iterrows():
            fut_contract, fut_range = row
            try:
                # 2. Get futures raw series
                series = fut_contract.get_series()
                # 3. Do resampling (timeframe compression)
                # 4. Append compressed series to continuous futures series
                df_data.append(series.resample('D').apply(self.ohlc_resampler).dropna())
            except IntradayQuotesNotFoundError:
                continue

        # 5. Store compressed series for future in buffer(for future quick price fetching)

        # Build transactions list
        pass
