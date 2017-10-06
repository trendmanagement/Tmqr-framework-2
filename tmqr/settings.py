from datetime import datetime

# MongoDB credentials
#
MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmqr2?authMechanism=SCRAM-SHA-1'
MONGO_DB = 'tmqr2'

MONGO_CONNSTR_V1 = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
MONGO_EXO_DB_V1 = 'tmldb_v2'

DEFAULT_TIMEZONE = 'US/Pacific'

#
# RabbitMQ credentials
RABBIT_HOST = '10.0.1.2'
RABBIT_USER = 'tmqr'
RABBIT_PASSW = 'tmqr'

#
# Datasources types for DataFeed
#
SRC_INTRADAY = 'quotes_intraday'
SRC_OPTIONS_EOD = 'quotes_options_eod'

#
# Quotes types returned by datafeed
#
QTYPE_INTRADAY = 1
QTYPE_EOD = 2
QTYPE_SINGLE = 3
QTYPE_OPTIONS_EOD = 4

#
# Min-max range of quotes
#
QDATE_MIN = datetime(1900, 1, 1)
QDATE_MAX = datetime(2100, 1, 1)

# Allow any settings to be defined in settings_local.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
try:
    from tmqr.settings_local import *
except ImportError as e:
    if "settings_local" not in str(e):
        raise e
