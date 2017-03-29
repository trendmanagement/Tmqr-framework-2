import numpy as np
import pyximport

from tmqr.errors import *
from tmqrfeed.quotes.quote_base import QuoteBase

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily
from tmqrfeed.quotes.dataframegetter import DataFrameGetter


class QuoteContFut(QuoteBase):
    """
    Continuous futures building quote engine
    """

    def __init__(self, instrument, **kwargs):
        super().__init__(**kwargs)

        self.timeframe = kwargs.get('timeframe', None)
        self.fut_offset = kwargs.get('fut_offset', 0)
        self.date_start = kwargs.get('date_start', self.dm.datafeed.date_start)
        self.date_end = kwargs.get('date_end', None)

        if self.timeframe is None:
            raise ArgumentError("'timeframe' kwarg is not set")
        if self.timeframe != 'D':
            raise ArgumentError("Only 'D' timeframe supported")

        self.instrument = instrument

    def calculate_fut_offset_series(self, prev_series, new_series):
        try:
            prev_prices = prev_series.loc[prev_series.index[-1]]
            new_prices = new_series.loc[prev_series.index[-1]]
            # Calculating futures rollover factor
            fut_offset = new_prices['exec'] - prev_prices['exec']
        except KeyError:
            fut_offset = 0.0

        new_series[['o', 'h', 'l', 'c', 'exec']] -= fut_offset
        new_series = new_series[new_series.index > prev_series.index[-1]]
        return new_series



    def build(self):
        # Get futures chain
        fut_chain = self.dm.datafeed.get_fut_chain(self.instrument)

        # Create contracts list
        chain_values = fut_chain.get_list(self.date_start, offset=self.fut_offset)

        # Build price series
        # 1. Iterate chains
        df_data = []
        df_positions = []
        for row in chain_values.iterrows():
            fut_contract, fut_range = row
            try:
                # 2. Get futures raw series
                series = self.dm.series_get(fut_contract)
                # 3. Do resampling (timeframe compression)
                series, positions = compress_daily(DataFrameGetter(series), fut_contract)


                # 4. Append compressed series to continuous futures series
                if len(df_data) == 0:
                    df_data.append(series)
                else:
                    df_data.append(self.calculate_fut_offset_series(df_data[-1], series))
                df_positions.append(positions)

            except IntradayQuotesNotFoundError:
                continue

        return self.merge_series(df_data), self.merge_positions(df_positions)
