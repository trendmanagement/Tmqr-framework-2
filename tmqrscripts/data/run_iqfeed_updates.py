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
from tmqrscripts.data.common import get_futures_tickers_for_live, get_instruments_list, check_bday_or_holiday
from tmqrfeed import DataManager
from tmqr.logs import log
from tmqr.settings import *
from tmqr.serialization import object_save_compress, object_load_decompress
import pytz
import numpy as np
import pandas as pd
from pymongo import MongoClient
import datetime
import sys
import _thread
import logging
dtn_product_id = 'NIKOLAS_JOYCE_13424'

dtn_login = '470998'
dtn_password = '43354519'

# dtn_login = 'guest'
# dtn_password = 'auci0xun'

timezone_est = pytz.timezone('US/Eastern')
timezone_pst = pytz.timezone('US/Pacific')

IQFEED_V2_COLLECTION = 'quotes_intraday_iq'
# IQFEED_V2_COLLECTION = 'quotes_intraday' # TODO: replace after production deployment

IQFEED_V1_COLLECTION = 'futurebarcol_iq'


# IQFEED_V1_COLLECTION = 'futurebarcol'  # TODO: replace after production deployment


class TMQRIQFeedBarListener(iq.VerboseBarListener):
    def __init__(self, name: str, symbol_map):
        super().__init__(name)
        self.symbol_map = symbol_map

        client_v1 = MongoClient(MONGO_CONNSTR_V1_LIVE)
        self.db_v1 = client_v1[MONGO_DB_V1_LIVE]

        client_v2 = MongoClient(MONGO_CONNSTR)
        self.db_v2 = client_v2[MONGO_DB]

        self._last_bar_data = {}

    def _bar_v1_process(self, iq_ticker, date_utc, bar_array):
        ticker_dict = self.symbol_map[iq_ticker]
        # Make the datetime tz-aware (PST) and replace tz-info
        date_pst = date_utc.astimezone(timezone_pst).replace(tzinfo=None)

        req_dict = {
            "bartime": date_pst,
            "idcontract": ticker_dict['v1_contract_id'],
            "open": bar_array['open_p'],
            "high": bar_array['high_p'],
            "low": bar_array['low_p'],
            "close": bar_array['close_p'],
            "volume": float(bar_array['prd_vlm']),
            "errorbar": False,
        }

        self.db_v1[IQFEED_V1_COLLECTION].replace_one(
            {'idcontract': req_dict['idcontract'], 'bartime': req_dict['bartime']},
            req_dict, upsert=True
            )

    def _history_v2_flush(self, v2_ticker, date_utc, df_quotes):
        dt = datetime.datetime.combine(date_utc, datetime.time(0, 0, 0))

        if not check_bday_or_holiday(dt):
            # Filter holidays
            return

        merged_df = df_quotes

        v2_quotes_data = self.db_v2[IQFEED_V2_COLLECTION].find_one({'tckr': v2_ticker, 'dt': dt})

        if v2_quotes_data:
            df_old = object_load_decompress(v2_quotes_data['ohlc'])
            merged_df = df_quotes.combine_first(df_old)

        self.db_v2[IQFEED_V2_COLLECTION].replace_one(
            {'tckr': v2_ticker, 'dt': dt},
            {'tckr': v2_ticker, 'dt': dt, 'ohlc': object_save_compress(merged_df)}, upsert=True
        )

    def _history_v2_process(self, iq_ticker, bar_time_utc, bar_array):
        ticker_dict = self.symbol_map[iq_ticker]
        history_cache_last_date = ticker_dict.get('history_v2_last_date', None)

        if history_cache_last_date != bar_time_utc.date():
            if history_cache_last_date:
                # Flush the cache to the DB
                df_cache = ticker_dict['history_cache']
                df_cache.sort_index(inplace=True)
                # Writing the history to v2 DB
                self._history_v2_flush(ticker_dict['contract'].ticker, history_cache_last_date, df_cache)
                log.debug(
                    f"HIST V2 Update: {ticker_dict['contract'].ticker} at {history_cache_last_date} #{len(df_cache)} bars")

            # Re-initiate the cache
            # Create new dataframe
            df_cache = pd.DataFrame([{
                                         'dt': bar_time_utc,
                                         'o': bar_array['open_p'],
                                         'h': bar_array['high_p'],
                                         'l': bar_array['low_p'],
                                         'c': bar_array['close_p'],
                                         'v': float(bar_array['prd_vlm'])}]).set_index('dt')

            ticker_dict['history_v2_last_date'] = bar_time_utc.date()
            ticker_dict['history_cache'] = df_cache
        else:
            # It's the same day, just update the historical dataframe
            df_cache = ticker_dict['history_cache']
            df_cache.at[bar_time_utc, 'o'] = bar_array['open_p']
            df_cache.at[bar_time_utc, 'h'] = bar_array['high_p']
            df_cache.at[bar_time_utc, 'l'] = bar_array['low_p']
            df_cache.at[bar_time_utc, 'c'] = bar_array['close_p']
            df_cache.at[bar_time_utc, 'v'] = float(bar_array['prd_vlm'])




    def _bar_v2_process(self, iq_ticker, bar_time_utc, bar_array):
        if not check_bday_or_holiday(bar_time_utc):
            # Filter holidays
            return

        ticker_dict = self.symbol_map[iq_ticker]

        df_cache = pd.DataFrame([{
            'dt': bar_time_utc,
            'o': bar_array[3],
            'h': bar_array[4],
            'l': bar_array[5],
            'c': bar_array[6],
            'v': float(bar_array[8])}]).set_index('dt')

        self._history_v2_flush(ticker_dict['contract'].ticker, bar_time_utc.date(), df_cache)

    def check_bar_integrity(self,  bar_time_est, bar_data):
        iqticker = bar_data[0]

        recent_bar = self._last_bar_data.get(iqticker)

        if not recent_bar:
            self._last_bar_data[iqticker] = (bar_time_est, bar_data)
        else:
            # Do quotes integrity checks
            if not np.all(np.isfinite((bar_data['open_p'], bar_data['high_p'], bar_data['low_p'], bar_data['close_p'], bar_data['prd_vlm']))):
                log.error(f"{iqticker}: infinite data detected: {bar_data}")
                return False

            if not (bar_data['open_p'] > 0 and bar_data['high_p'] > 0 and bar_data['low_p'] > 0 and bar_data['close_p'] > 0 and bar_data['prd_vlm'] >= 0):
                log.error(f"{iqticker}: negative OHLCV detected: {bar_data}")
                return False

            recent_est_time = recent_bar[0]
            recent_bar_ohlc = recent_bar[1]

            if (bar_time_est-recent_est_time).total_seconds() < 5*60:
                if np.any([np.abs((bar_data[i] / recent_bar_ohlc[i]) - 1) > 0.01 for i in ['open_p', 'high_p', 'low_p', 'close_p']]):
                    log.warning(f"{iqticker}: Possible spike detected > +- 1%: OLD Bar {recent_bar_ohlc}, NEW Bar: {bar_data}")

            self._last_bar_data[iqticker] = (bar_time_est, bar_data)

        return True

    def process_latest_bar_update(self, bar_data: np.array):
        try:
            for bar in bar_data:
                bar_time_est = timezone_est.localize(iq.date_us_to_datetime(bar['date'], bar['time']) - datetime.timedelta(minutes=1))
                bar_time_utc = bar_time_est.astimezone(pytz.utc)

                if not self.check_bar_integrity(bar_time_est, bar):
                    return

                #log.debug(f"UPD {bar[0]} {bar_time_est}: {bar}")

                ticker_rec = self.symbol_map[bar['symbol']]

                ticker_rec['live_bar'] = {
                    'dt_utc': bar_time_utc,
                    'bar_array': bar,
                }

                #
                # Once new live bar arrives, flush the history cache to the DB
                #
                df_cache = ticker_rec.get('history_cache', None)
                if df_cache is not None:
                    if len(df_cache) > 0:
                        # Flush the cache to the DB
                        df_cache.sort_index(inplace=True)
                        # Writing the history to v2 DB
                        self._history_v2_flush(ticker_rec['contract'].ticker, ticker_rec['history_v2_last_date'], df_cache)

                        log.debug(
                            f"HIST V2 Live Flush: {ticker_rec['contract'].ticker} at {ticker_rec['history_v2_last_date']}"
                            f" #{len(df_cache)} bars")

                        log.info(
                            f"LIVE {ticker_rec['contract'].ticker}: Backfill has been finished. Last quote: {df_cache.index[-1]}")
                    else:
                        log.info(
                            f"LIVE {ticker_rec['contract'].ticker}: Backfill has been finished.")

                    del ticker_rec['history_cache']
                    del ticker_rec['history_v2_last_date']

                self._bar_v2_process(bar['symbol'], bar_time_utc, bar)
                self._bar_v1_process(bar['symbol'], bar_time_utc, bar)
        except:
            log.exception("Unhandled exception in process_history_bar()")

    def process_live_bar(self, bar_data: np.array):
        try:
            for bar in bar_data:
                bar_time = iq.date_us_to_datetime(bar[1], bar[2]) - datetime.timedelta(minutes=1)
                # print(f"LIVE {bar_time}: {bar}")
                ticker_rec = self.symbol_map[bar[0]]

                if 'live_bar' in ticker_rec:
                    if not np.all(bar == ticker_rec['live_bar']['bar_array']):
                        log.warning(
                            f"{bar[0]} live bar prices mismatch: New: {bar} Old: {ticker_rec['live_bar']['bar_array']}")
        except:
            log.exception("Unhandled exception in process_live_bar()")

    def process_history_bar(self, bar_data: np.array, force_db_write=False, ticker=None):
        try:
            for bar in bar_data:
                iq_tckr = ticker
                if iq_tckr is None:
                    iq_tckr = bar['symbol']

                bar_time_est = timezone_est.localize(iq.date_us_to_datetime(bar['date'], bar['time']) - datetime.timedelta(minutes=1))
                bar_time_utc = bar_time_est.astimezone(pytz.utc)

                if not self.check_bar_integrity(bar_time_est, bar):
                    log.debug(f"Historical bar integrity checks failed: {bar}")
                    return

                log.debug(f"HIST {iq_tckr} {bar_time_est}: {bar}")

                self._history_v2_process(iq_tckr, bar_time_utc, bar)

                self._bar_v1_process(iq_tckr, bar_time_utc, bar)

            if force_db_write and len(bar_data) > 0:
                # Flush the cache to the DB
                ticker_dict = self.symbol_map[iq_tckr]
                df_cache = ticker_dict['history_cache']
                df_cache.sort_index(inplace=True)
                # Writing the history to v2 DB
                self._history_v2_flush(ticker_dict['contract'].ticker, bar_time_utc.date(), df_cache)
                log.debug(
                    f"HIST V2 Update: {ticker_dict['contract'].ticker} at {bar_time_utc} #{len(df_cache)} bars")
        except:
            log.exception("Unhandled exception in process_history_bar()")

    def process_invalid_symbol(self, bad_symbol: str):
        log.error(f"Invalid Symbol: {bad_symbol}")

    def process_symbol_limit_reached(self, symbol: str):
        log.error(f"Symbol limit reached: {symbol}")

    def process_replaced_previous_watch(self, symbol: str):
        log.warning(f"Replaced previous watch: {symbol}")

    def process_error(self, fields):
        log.error(f"{self._name} Process Error: \n {fields}")

    def feed_is_stale(self) -> None:
        log.error("%s: Feed Disconnected" % self._name)

    def feed_is_fresh(self) -> None:
        log.info("%s: Feed Connected" % self._name)

    def feed_has_error(self) -> None:
        log.error("%s: Feed Reconnect Failed" % self._name)

    def process_conn_stats(self, stats) -> None:
        # print("%s: Connection Stats:" % self._name)
        # print(stats)

        # Skip information about connection stats
        pass


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
    parser.add_argument('--live_update_seconds', action='store',
                        dest='live_update_sec', default=5, type=int,
                        help='Update live bars every N seconds. If 0 updates with every tick (expect performance issues!)')
    parser.add_argument('--live_n_futures', action='store',
                        dest='live_n_futures', default=6, type=int,
                        help='Number of active futures to update in real-time')
    parser.add_argument('--historical_refresh_interval_min', action='store',
                        dest='historical_refresh_interval_min', default=2, type=int,
                        help='Interval of polling new IQFeed delayed historical data')


    arguments = parser.parse_args()

    log.setup('scripts', "IQFeedDataFeed", to_file=True, log_level=logging.DEBUG)
    log.info('Launching IQFeed datascript')

    #
    # Get watchlist of tickers for live updates
    #
    try:
        dm = DataManager()
        instruments = {}
        iq_watchlist = {}
        log.info("Getting symbols for live updates...")
        for instr in get_instruments_list():
            instruments[instr['name']] = instr
            ticker_update_rec = get_futures_tickers_for_live(instr, dm, nfuture_contracts=arguments.live_n_futures)

            for tckr_rec in ticker_update_rec:
                # Apply UTF-8 encoding, because IQFeed sends tickers as encoded bytes (performance speedup)
                encoded_ticker = tckr_rec['iqfeed_ticker'].encode()
                iq_watchlist[encoded_ticker] = tckr_rec
        log.info(f"{len(iq_watchlist)} symbols to watch")

        IQ_FEED = iq.FeedService(product=dtn_product_id,
                                 version="IQFEED_LAUNCHER",
                                 login=dtn_login,
                                 password=dtn_password)

        nohup = arguments.nohup
        headless = arguments.headless
        ctrl_file = arguments.ctrl_file
        historical_refresh_interval = arguments.historical_refresh_interval_min
        IQ_FEED.launch(timeout=30,
                       check_conn=True,
                       headless=headless,
                       nohup=nohup)

        # Modify code below to connect to the socket etc as described above
        admin = iq.AdminConn(name="Launcher")
        #
        # admin_listener = iq.VerboseAdminListener("Launcher-listen")
        admin_listener = iq.SilentAdminListener("Launcher-listen")
        admin.add_listener(admin_listener)

        bar_conn = iq.BarConn(name='pyiqfeed-Example-interval-bars')
        bar_listener = TMQRIQFeedBarListener("Bar Listener", iq_watchlist)
        bar_conn.add_listener(bar_listener)

        hist_conn = iq.HistoryConn()
        hist_listener = iq.VerboseIQFeedListener("History Bar Listener")
        hist_conn.add_listener(hist_listener)

        last_refresh_date = None
        time.sleep(5)

        with iq.ConnConnector([bar_conn, admin, hist_conn]) as connector:
            # Wain till IQFeed connected and initialized
            time.sleep(5)

            """
            for iq_ticker, watch_rec in iq_watchlist.items():
                data_start = watch_rec['last_date_utc'].astimezone(timezone_est)
                is_delayed = watch_rec['iqfeed_is_delayed']

                if not is_delayed:
                    log.info(f"Subscribing live updates {iq_ticker} from {data_start} {watch_rec['contract']}")
                    # Skip tickers which are not in delayed mode
                    bar_conn.watch(symbol=iq_ticker.decode(), interval_len=60,
                                   interval_type='s', update=arguments.live_update_sec, bgn_bars=data_start)
                time.sleep(0.05)
            """

            while not os.path.isfile(ctrl_file):
                if last_refresh_date is None or int((datetime.datetime.now() - last_refresh_date).total_seconds()/60) >= historical_refresh_interval:
                    # Do historical updates
                    start_time = time.time()

                    log.debug(f"Polling historical updates")
                    for iq_ticker_b, watch_rec in iq_watchlist.items():
                        iq_ticker = iq_ticker_b.decode()
                        data_start = watch_rec['last_date_utc'].astimezone(timezone_est)
                        is_delayed = watch_rec['iqfeed_is_delayed']

                        if is_delayed:
                            try:
                                # Process only delayed tickers
                                if last_refresh_date is None:
                                    log.info(f"Polling historical updates {iq_ticker} from {data_start} {watch_rec['contract']}")
                                    bars_data = hist_conn.request_bars_in_period(ticker=iq_ticker, interval_len=60, interval_type='s',
                                                                                 bgn_prd=datetime.datetime.now() - datetime.timedelta(days=10),
                                                                                 end_prd=datetime.datetime.now() + datetime.timedelta(days=2),
                                                                                 ascend=True,
                                                                                 timeout=120)
                                else:
                                    # If data has been recently updated, poll last hour to update the data
                                    bars_data = hist_conn.request_bars_for_days(ticker=iq_ticker, interval_len=60, interval_type='s',
                                                                                days=10, max_bars=10,
                                                                                ascend=True, timeout=10)
                                # Fix: Historical data comes without ticker, do monkey patch
                                bar_listener.process_history_bar(bars_data,
                                                                 force_db_write=True,
                                                                 ticker=iq_ticker_b,
                                                                 )
                            except BrokenPipeError:
                                log.error("IQConnect.exe unexpectedly exited")
                                sys.exit(-2)
                            except Exception as exc:
                                log.error(f'{type(exc)}: {exc}')



                    last_refresh_date = datetime.datetime.now()
                    # your code
                    elapsed_time = time.time() - start_time
                    log.info(f'Historical update finished in {elapsed_time}')


                time.sleep(10)

            log.info("Stopping service due to stop signal")

            os.remove(ctrl_file)

    except KeyboardInterrupt:
        log.info("Service stopped via Ctrl+C")
    except:
        log.exception("Unhandled exception in main loop")
        sys.exit(-1)

