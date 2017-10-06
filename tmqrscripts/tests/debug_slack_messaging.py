from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase

import pymongo
from pymongo import MongoClient

from tradingcore.signalapp import SignalApp, APPCLASS_EXO
from tradingcore.messages import *

signalapp = SignalApp('V2 calcs', APPCLASS_EXO, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)

signalapp.send(MsgStatus('V2_Index', 'V2 Indexes Running {0}'.format('TEST'), notify=True))

#print('6J_CallSpread_Short_Strategy_DSP_LPBP_Combination__Bearish_May_12_custom' in final_alpha_list)



