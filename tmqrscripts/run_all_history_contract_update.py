'''
Futures data updates script, all futures contracts
'''
import sys
sys.path.append('..')
#sys.path.append('/tmqr_framework_2/')

from load_futures_from_v1 import run_all_futures

run_all_futures()
