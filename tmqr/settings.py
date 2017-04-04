from datetime import datetime

# MongoDB credentials
#
MONGO_CONNSTR = 'mongodb://localhost'
MONGO_DB = 'tmqr2'

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
