from pymongo import MongoClient
from tmqr.settings import *
from tmqrfeed import DataManager
from datetime import timedelta
from tmqr.errors import QuoteNotFoundError
import pytz


def get_futures_tickers_for_live(instrument_record, dm, nfuture_contracts=6):
    """
    Create metadata for live futures tickers for updates
    :param instrument_record: record of instrument dict produced by get_instruments_list()
    :param dm: DataManager instance
    :return: list of tickers metadata for updates
    """
    #
    # Override instrument futures month settings, obtain all futures
    #
    fut_chain = dm.datafeed.get_fut_chain(instrument_record['name'], futures_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

    futures_tuple = fut_chain.get_list(datetime.now() - timedelta(days=7), offset=0, limit=nfuture_contracts)

    futures_records = []

    for fut, dt_start, dt_end in futures_tuple:
        try:
            last_quote_date = dm.datafeed.get_last_quote_date(fut.ticker, fut.data_source)
        except QuoteNotFoundError:
            last_quote_date = datetime.now().astimezone(pytz.utc) - timedelta(days=60)

        assert last_quote_date.tzinfo == pytz.utc

        futures_records.append({
            'contract': fut,
            'v1_contract_id': fut.contract_info.extra('sqlid'),
            'iqfeed_ticker': f"{instrument_record['iqfeed_ticker']}{fut.month_year_code}",
            'last_date_utc':  last_quote_date,
            'instrument': instrument_record['name'],
            }
        )

    return futures_records


def get_instruments_list():
    """
    Returns the list of available instrument for V2 with V1 and IQFeed metadata
    :return:
    """
    client_v2 = MongoClient(MONGO_CONNSTR)
    db_v2 = client_v2[MONGO_DB]

    client_v1 = MongoClient(MONGO_CONNSTR_V1)
    db_v1 = client_v1[MONGO_EXO_DB_V1]

    instruments = []

    for instr_dict in db_v2['asset_info'].find({}):
        if '$DEFAULT$' in instr_dict['instrument']:
            continue

        exchange_ticker_root = instr_dict['instrument'].split('.')[1]

        v1_instrum_dict = db_v1['instruments'].find_one({'exchangesymbol': exchange_ticker_root})

        v1_instrument_id = v1_instrum_dict.get('idinstrument', None)

        insrument_ = {
            'name': instr_dict['instrument'],
            'v1_instrument_id': v1_instrument_id,
            'v1_ticker': exchange_ticker_root,
            'iqfeed_ticker': instr_dict.get('iqfeed_ticker', exchange_ticker_root),
        }

        instruments.append(insrument_)

    return instruments



if __name__ == '__main__':
    dm = DataManager()
    for instr in get_instruments_list():
        ticker_update_rec = get_futures_tickers_for_live(instr, dm)
        pass