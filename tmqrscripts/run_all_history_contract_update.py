'''
Futures data updates script, all futures contracts
'''
import sys, os
sys.path.append('..')
sys.path.append('./tmqr_framwork2/')
sys.path.append(os.path.join(os.path.dirname(__file__),'../../'))

from load_futures_from_v1 import run_all_futures

run_all_futures()
