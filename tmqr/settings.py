from datetime import datetime

# MongoDB credentials
#
MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmqr2?authMechanism=SCRAM-SHA-1'
MONGO_DB = 'tmqr2'

MONGO_CONNSTR_V1 = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
MONGO_EXO_DB_V1 = 'tmldb_v2'

MONGO_CONNSTR_V1_LIVE = 'mongodb://tml:tml@10.0.1.2/tmldb_test?authMechanism=SCRAM-SHA-1'
MONGO_DB_V1_LIVE = 'tmldb_test'

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

TWITTER_ACCESS_TOKEN = '956610364019392512-QdLMvzDPUO2zYjVAuSlMXGXCsZToar6'
TWITTER_ACCESS_TOKEN_SECRET = '3R1tiFq4oRpkNyp3pbwsnoKp8smbpCJB90Dt4wl47R0ZS'
CONSUMER_KEY = 'H16nSIP7NhWaqLDopZDH3HQYt'
CONSUMER_SECRET = 'RJvvFuk2WsLwcDhQTHPJqC50u43oT9RDTd2WU4OYcicIfuC07X'

COLLECTIVE2_SYSTEMID = '203005734'
COLLECTIVE2_PWD = 'test'
COLLECTIVE2_API_KEY = 'sgCrYWS6T3fl961BCVcO9PeEOQodcDlytaprVCXr13Qls6JJ2G'

# Allow any settings to be defined in settings_local.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
try:
    from tmqr.settings_local import *
except ImportError as e:
    if "settings_local" not in str(e):
        raise e
