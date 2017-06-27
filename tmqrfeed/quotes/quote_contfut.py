import numpy as np
import pyximport

from tmqr.errors import *
from tmqrfeed.quotes.quote_base import QuoteBase

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.quotes.compress_daily_ohlcv import compress_daily
from tmqrfeed.quotes.dataframegetter import DataFrameGetter
from tmqrfeed.position import Position
from tmqr.settings import QDATE_MAX


class QuoteContFut(QuoteBase):
    """
    Continuous futures building quote engine
    """

    def __init__(self, instrument, **kwargs):
        super().__init__(**kwargs)

        self.timeframe = kwargs.get('timeframe', None)
        self.fut_offset = kwargs.get('fut_offset', 0)
        self.date_start = kwargs.get('date_start', self.dm.datafeed.date_start)
        self.date_end = kwargs.get('date_end', self.dm.datafeed.date_end)
        self.decision_time_shift = kwargs.get('decision_time_shift', 0)

        if self.timeframe is None:
            raise ArgumentError("'timeframe' kwarg is not set")
        if self.timeframe != 'D':
            raise ArgumentError("Only 'D' timeframe supported")
        if self.decision_time_shift < 0:
            raise ArgumentError("'decision_time_shift' kwarg must be >= 0")

        self.instrument = instrument

    def __str__(self):
        return f"QuoteContFut-{self.instrument}-{self.timeframe}"

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

    def apply_future_rollover(self, position, future_date_end):
        """
        Change position to zero if the last day before expiration occurred  
        :param position: 
        :param future_date_end: 
        :return: 
        """
        pos_last_date = position.last_date
        if pos_last_date.date() >= future_date_end:
            position.close(pos_last_date)

        return position

    def build(self):
        # Get futures chain
        fut_chain = self.dm.datafeed.get_fut_chain(self.instrument)

        # Create contracts list
        chain_values = fut_chain.get_list(self.date_start, offset=self.fut_offset)

        # Get deafult asset session
        asset_session = self.dm.session_get()

        # Build price series
        # 1. Iterate chains
        df_data = []
        positions_list = []
        for fut_chain_row in chain_values:
            fut_contract = fut_chain_row[0]
            date_start = fut_chain_row[1]
            date_end = fut_chain_row[2]

            if date_start > self.date_end.date():
                break

            try:
                # 2. Get futures raw series
                series = self.dm.series_get(fut_contract, date_start=max(date_start, self.date_start.date()),
                                            date_end=min(date_end, self.date_end.date()))

                # 3. Do resampling (timeframe compression)
                series, position = compress_daily(DataFrameGetter(series), fut_contract, asset_session,
                                                  self.decision_time_shift)


                # 4. Append compressed series to continuous futures series
                if len(df_data) == 0:
                    df_data.append(series)
                else:
                    df_data.append(self.calculate_fut_offset_series(df_data[-1], series))

                # Make sure that we have closed futures after rollover
                positions_list.append(self.apply_future_rollover(position, date_end))

            except IntradayQuotesNotFoundError:
                continue

        return self.merge_series(df_data), Position.merge(self.dm, positions_list)
