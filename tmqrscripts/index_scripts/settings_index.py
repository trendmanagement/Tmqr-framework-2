from tmqrindex.deployed.exo_long_enhance_dt import EXOLongEnhance_DT
from tmqrindex.deployed.exo_long_enhance_dt_putspread import EXOLongEnhance_DT_PutSpread
from tmqrindex.deployed.exo_short_enhance_dt_2 import EXOShortEnhance_DT_2
from tmqrindex.deployed.exo_short_enhance_dt_2_callspread import EXOShortEnhance_DT_2_CallSpread

INDEX_LIST = [

    {
        'class': EXOLongEnhance_DT
    },
    {
        'class': EXOLongEnhance_DT_PutSpread
    },
    {
        'class': EXOShortEnhance_DT_2
    },
    {
        'class': EXOShortEnhance_DT_2_CallSpread
    },
]

INSTRUMENT_OPT_CODE_LIST = [
    {
        'instrument':'US.ES',
        'opt_codes':['EW','']
    },
]