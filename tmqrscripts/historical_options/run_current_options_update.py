'''
Futures data updates script, all futures contracts
'''
# import sys
# sys.path.append('..')

# from tmqrscripts.historical_options.import_options_data import *
#
# run_current_options()


from tmqrscripts.historical_options.import_options_data import *

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--instrument", help="an instrument you want to backfill", type=str)
args = parser.parse_args()

if args.instrument is None:
    print('run all')
    run_current_options()
else:
    print('run ',args.instrument)
    run_current_options_selected_instrument(args.instrument)