'''
Futures data updates script, all futures contracts
'''
# import sys
# sys.path.append('..')

import argparse

from tmqrscripts.historical_futures.load_futures_from_v1 import *

parser = argparse.ArgumentParser()
parser.add_argument("--instrument", help="an instrument you want to backfill", type=str)
args = parser.parse_args()

if args.instrument is None:
    print('run all')
    run_current_futures_history_all_instruments()
else:
    print('run ',args.instrument)
    run_current_futures_history_selected_instrument(args.instrument)