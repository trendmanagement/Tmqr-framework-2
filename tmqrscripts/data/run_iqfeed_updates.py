#! /usr/bin/env python3
# coding=utf-8

"""
This is an example that launches IQConnect.exe.

You need a file called passwords.py (described in README.md that can be
imported here.

This code just launches IQConnect.exe and returns.

You probably want this to launch from cron and exit when you stop
trading, either at an end of day or at an end of week.

You probably also want to  open a socket to IQConnect.exe and maybe read
from the Admin Socket and log some data or put it on a dashboard.  You
can find out for example if your trading code is not reading ticks fast
enough or if the socket get closed.

Note that IQConnect.exe exits once the last connection to it is closed
so you want to keep at least one socket to it open unless you want
IQConnect.exe to exit.

Read the comments and code in service.py for more details.

This program launches an instance of IQFeed.exe if it isn't running, creates
an AdminConn and writes messages received by the AdminConn to stdout. It looks
for a file with the name passed as the option ctrl_file, defaults to
/tmp/stop_iqfeed.ctrl. When it sees that file it drops it's connection to
IQFeed.exe, deletes the control file and exits. If there are no other open
connections to IQFeed.exe, IQFeed.exe will by default exit 5 seconds later.

"""

import os
import time
import argparse
import pyiqfeed as iq
from tmqrscripts.data.common import get_futures_tickers_for_live, get_instruments_list
from tmqrfeed import DataManager
import pytz
import numpy as np

dtn_product_id = 'NIKOLAS_JOYCE_13424'
dtn_login = '470998'
dtn_password = '43354519'

timezone_est = pytz.timezone('US/Eastern')

class TMQRIQFeedBarListener(iq.VerboseBarListener):

    def process_latest_bar_update(self, bar_data: np.array):
        for bar in bar_data:
            bar_time = iq.date_us_to_datetime(bar[1], bar[2])
            print(f"UPD  {bar_time}: {bar}")

    def process_live_bar(self, bar_data: np.array):
        for bar in bar_data:
            bar_time = iq.date_us_to_datetime(bar[1], bar[2])
            print(f"LIVE {bar_time}: {bar}")

    def process_history_bar(self, bar_data: np.array):
        for bar in bar_data:
            bar_time = iq.date_us_to_datetime(bar[1], bar[2])
            print(f"HIST {bar_time}: {bar}")



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Launch IQFeed.")
    parser.add_argument('--nohup', action='store_true',
                        dest='nohup', default=False,
                        help="Don't kill IQFeed.exe when this script exists.")
    parser.add_argument('--headless', action="store_true",
                        dest='headless', default=False,
                        help="Launch IQFeed in a headless XServer.")
    parser.add_argument('--control_file', action='store',
                        dest='ctrl_file', default="/tmp/stop_iqfeed.ctrl",
                        help='Stop running if this file exists.')
    arguments = parser.parse_args()

    IQ_FEED = iq.FeedService(product=dtn_product_id,
                             version="IQFEED_LAUNCHER",
                             login=dtn_login,
                             password=dtn_password)

    nohup = arguments.nohup
    headless = arguments.headless
    ctrl_file = arguments.ctrl_file
    IQ_FEED.launch(timeout=30,
                   check_conn=True,
                   headless=headless,
                   nohup=nohup)

    # Modify code below to connect to the socket etc as described above
    admin = iq.AdminConn(name="Launcher")
    #
    #admin_listener = iq.VerboseAdminListener("Launcher-listen")
    admin_listener = iq.SilentAdminListener("Launcher-listen")
    admin.add_listener(admin_listener)

    bar_conn = iq.BarConn(name='pyiqfeed-Example-interval-bars')
    bar_listener = TMQRIQFeedBarListener("Bar Listener")
    bar_conn.add_listener(bar_listener)

    #
    # Get watchlist of tickers for live updates
    #
    dm = DataManager()
    instruments = {}
    iq_watchlist = {}
    for instr in get_instruments_list():
        instruments[instr['name']] = instr
        ticker_update_rec = get_futures_tickers_for_live(instr, dm)

        for tckr_rec in ticker_update_rec:
            # Apply UTF-8 encoding, because IQFeed sends tickers as encoded bytes (performance speedup)
            encoded_ticker = tckr_rec['iqfeed_ticker'].encode()
            iq_watchlist[encoded_ticker] = tckr_rec



    with iq.ConnConnector([bar_conn, admin]) as connector:
        for iq_ticker, watch_rec in iq_watchlist.items():
            data_start = watch_rec['last_date_utc'].astimezone(timezone_est)

            print(f"Subscribing {iq_ticker} from {data_start}")
            bar_conn.watch(symbol=iq_ticker, interval_len=60,
                           interval_type='s', update=10, lookback_bars=10) #, bgn_bars=data_start)

        while not os.path.isfile(ctrl_file):
            time.sleep(10)

    os.remove(ctrl_file)
