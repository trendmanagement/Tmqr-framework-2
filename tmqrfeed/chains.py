from tmqrfeed.contracts import FutureContract
from pandas.tseries.offsets import BDay
from datetime import datetime
import pandas as pd

class FutureChain:
    """
    Futures chain class
    """

    def __init__(self, fut_tckr_list, asset_info, **kwargs):
        self.ainfo = asset_info
        self.rollover_days_before = kwargs.get('rollover_days_before', self.ainfo.rollover_days_before)
        self.futures_months = kwargs.get('futures_months', self.ainfo.futures_months)
        self.date_start = kwargs.get('date_start', None)

        raw_futures = [FutureContract(f) for f in fut_tckr_list]
        self.futchain = self._generate_chains(raw_futures)



    def _generate_chains(self, raw_futures):
        """
        Creates historical chains
        :param raw_futures:
        :return:
        """
        prev_fut = None
        date_start = datetime(1900, 1, 1) if self.date_start is None else self.date_start

        chain = []

        for i, fut in enumerate(raw_futures):
            if fut.exp_date < date_start:
                continue
            if fut.exp_month not in self.futures_months:
                continue

            if prev_fut is None:
                prev_fut = fut
                continue
            else:
                chain.append({
                    'ticker': fut,
                    'date_start': prev_fut.exp_date - BDay(self.rollover_days_before + 1),
                    'date_end': fut.exp_date - BDay(self.rollover_days_before),
                })
                prev_fut = fut

        return pd.DataFrame(chain).set_index('ticker')



    def __len__(self):
        return len(self.futchain)
