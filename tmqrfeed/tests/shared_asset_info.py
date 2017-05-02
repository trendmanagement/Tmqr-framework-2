from datetime import datetime

from tmqr.settings import *

ASSET_INFO = {
    'futures_months': [3, 6, 9, 12],
    'instrument': 'US.ES',
    'market': 'US',
    'rollover_days_before': 2,
    'ticksize': 0.25,
    'tickvalue': 12.5,
    'timezone': 'US/Pacific',
    'data_futures_src': SRC_INTRADAY,
    'data_options_src': SRC_OPTIONS_EOD,
    'data_options_use_prev_date': True,
    'trading_session': [{
        'decision': '10:40',
        'dt': datetime(1900, 1, 1, 0, 0),
        'execution': '10:45',
        'start': '00:32'}],
    'extra_key': 'OK'
}
