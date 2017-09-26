from tmqrindex.deployed.exo_long_enhance_dt import EXOLongEnhance_DT
from tmqrindex.deployed.exo_long_enhance_dt_putspread import EXOLongEnhance_DT_PutSpread
from tmqrindex.deployed.exo_short_enhance_dt_2 import EXOShortEnhance_DT_2
from tmqrindex.deployed.exo_short_enhance_dt_2_callspread import EXOShortEnhance_DT_2_CallSpread
from tmqrindex.deployed.es_exoweekly_calendar_risk_restriction_shorts import ES_EXOWeeklyCalendarRiskRestrictionShorts
from tmqrindex.deployed.es_exoweekly_calendar_risk_restriction_longs import ES_EXOWeeklyCalendarRiskRestrictionLongs
from tmqrindex.deployed.es_exoweekly_calendar_putspread import ES_EXOWeeklyCalendarPutSpread

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
    }
]

INSTRUMENT_OPT_CODE_LIST = [
    {
        'instrument':'US.6E',
        'opt_codes':['EUU','']
    },
]