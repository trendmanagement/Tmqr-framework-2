from tmqrindex.deployed.exo_long_enhance_dt import EXOLongEnhance_DT
from tmqrindex.deployed.exo_long_enhance_dt_putspread import EXOLongEnhance_DT_PutSpread
from tmqrindex.deployed.exo_short_enhance_dt_2 import EXOShortEnhance_DT_2
from tmqrindex.deployed.exo_short_enhance_dt_2_callspread import EXOShortEnhance_DT_2_CallSpread
from tmqrindex.deployed.es_exoweekly_calendar_risk_restriction_shorts import ES_EXOWeeklyCalendarRiskRestrictionShorts
from tmqrindex.deployed.es_exoweekly_calendar_risk_restriction_longs import ES_EXOWeeklyCalendarRiskRestrictionLongs
from tmqrindex.deployed.es_exoweekly_calendar_putspread import ES_EXOWeeklyCalendarPutSpread
from tmqrindex.deployed.es_exoweekly_calendar_risk_reversal_long import ES_EXOWeeklyCalendarRiskReversalLong

from tmqrindex.deployed.exo_semifuture_dynkel_20_60_longs import EXOSemiFuture_DynKel_20_60_longs
from tmqrindex.deployed.exo_semifuture_dynkel_20_80_longs import EXOSemiFuture_DynKel_20_80_longs
from tmqrindex.deployed.exo_semifuture_dynkel_60_20_shorts import EXOSemiFuture_DynKel_60_20_shorts
from tmqrindex.deployed.exo_semifuture_dynkel_80_20_shorts import EXOSemiFuture_DynKel_80_20_shorts
from tmqrindex.deployed.es_exo_semifuture_dynkel_20_80_longs import ES_EXOSemiFuture_DynKel_20_80_Longs
from tmqrindex.deployed.es_exo_semifuture_dynkel_80_20_longs import ES_EXOSemiFuture_DynKel_80_20_Longs

from tmqrindex.deployed.exo_callspread_dynkel_shorts import EXOCallSpread_DynKel_Shorts
from tmqrindex.deployed.exo_putspread_dynkel_longs import EXOPutSpread_DynKel_Longs

INSTRUMENT_LIST_TO_RUN_INDEXES = ['US.ES', 'US.CL', 'US.ZN', 'US.ZC', 'US.6J', 'US.6B', 'US.6E', 'US.6C', 'US.DC', 'US.NG', 'US.ZW', 'US.ZS']

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
    {
        'class': EXOSemiFuture_DynKel_20_60_longs
    },
    {
        'class': EXOSemiFuture_DynKel_20_80_longs
    },
    {
        'class': EXOSemiFuture_DynKel_60_20_shorts
    },
    {
        'class': EXOSemiFuture_DynKel_80_20_shorts
    },
    {
        'class': EXOCallSpread_DynKel_Shorts
    },
    {
        'class': EXOPutSpread_DynKel_Longs
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOSemiFuture_DynKel_20_80_Longs
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOSemiFuture_DynKel_80_20_Longs
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOWeeklyCalendarRiskRestrictionShorts
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOWeeklyCalendarRiskRestrictionLongs
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOWeeklyCalendarPutSpread
    },
    {
        'instrument':'US.ES',
        'class': ES_EXOWeeklyCalendarRiskReversalLong
    }
]

INSTRUMENT_OPT_CODE_LIST = [
    {
        'instrument':'US.ES',
        'opt_codes':['EW','EW1','EW2','EW3','EW4','']
    },
    {
        'instrument':'US.6E',
        'opt_codes':['EUU','']
    },
    {
        'instrument':'US.6B',
        'opt_codes':['GBU','']
    },
    {
        'instrument':'US.6C',
        'opt_codes':['CAU','']
    },
    {
        'instrument':'US.6A',
        'opt_codes':['ADU','']
    },
    {
        'instrument':'US.6J',
        'opt_codes':['JPU','']
    }
]