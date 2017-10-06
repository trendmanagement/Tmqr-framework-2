from exobuilder.data.datasource_mongo import DataSourceMongo
from tradingcore.execution_manager import ExecutionManager
from exobuilder.data.assetindex_mongo import AssetIndexMongo
from exobuilder.data.exostorage import EXOStorage
from tmqr.settings import *
try:
    assetindex = AssetIndexMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
    storage = EXOStorage(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
    datasource = DataSourceMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1, assetindex, futures_limit=10, options_limit=10,
                                 exostorage=storage)

    exmgr = ExecutionManager(MONGO_CONNSTR_V1, datasource, dbname=MONGO_EXO_DB_V1)
    exmgr.account_positions_process(write_to_db=True)

    position_pushed_to_realtime = True
except Exception as e:
    print(e)
    pass