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

from tmqrindex.deployed.exo_callspread_dynkel_shorts_lp import EXOCallSpread_DynKel_shorts_lp
from tmqrindex.deployed.exo_putspread_dynkel_longs_lp import EXOPutSpread_DynKel_longs_lp
from tmqrindex.deployed.exo_semifuture_dynkel_20_80_longs_lp import EXOSemiFuture_DynKel_20_80_longs_lp
from tmqrindex.deployed.exo_semifuture_dynkel_80_20_shorts_lp import EXOSemiFuture_DynKel_80_20_shorts_lp

from tmqrindex.deployed.exo_active_leg_short_put_for_bullish_putspread import EXO_Active_leg_Short_Put_For_Bullish_PutSpread
from tmqrindex.deployed.exo_passive_leg_long_put_for_bullish_putspread import EXO_Passive_leg_Long_Put_For_Bullish_PutSpread
from tmqrindex.deployed.exo_riskreversal_active_calls_for_longs_dynkel_20_80_longs import EXO_RiskReversal_Active_Calls_For_Longs_DynKel_20_80_Longs
from tmqrindex.deployed.exo_riskreversal_passive_puts_for_longs_dynkel_20_80_longs import EXO_RiskReversal_Passive_Puts_For_Longs_DynKel_20_80_Longs
from tmqrindex.deployed.exo_active_leg_short_call_for_bearish_callspread import EXO_Active_leg_Short_Call_For_Bearish_CallSpread
from tmqrindex.deployed.exo_passive_leg_long_call_for_bearish_callspread import EXO_Passive_leg_Long_Call_For_Bearish_CallSpread
from tmqrindex.deployed.exo_riskreversal_active_calls_for_shorts_dynkel_80_20_shorts import EXO_RiskReversal_Active_Calls_For_Shorts_DynKel_80_20_Shorts
from tmqrindex.deployed.exo_riskreversal_passive_puts_for_shorts_dynkel_80_20_shorts import EXO_RiskReversal_Passive_Puts_For_Shorts_DynKel_80_20_Shorts

from tmqrindex.deployed.exo_riskreversal_active_puts_for_shorts_dynkel_80_20_shorts import EXO_RiskReversal_Active_Puts_For_Shorts_DynKel_80_20_Shorts
from tmqrindex.deployed.exo_riskreversal_passive_calls_for_shorts_dynkel_80_20_shorts import EXO_RiskReversal_Passive_Calls_For_Shorts_DynKel_80_20_Shorts


INSTRUMENT_LIST_TO_RUN_INDEXES = ['US.ES', 'US.CL', 'US.ZN', 'US.ZC', 'US.6J', 'US.6B', 'US.6E', 'US.6C', 'US.DC',
                                  'US.NG', 'US.ZW', 'US.ZS', 'US.GC', 'US.ZL', 'US.LE', 'US.HE']

INDEX_LIST = [

    # {
    #     'class': EXOLongEnhance_DT
    # },
    # {
    #     'class': EXOLongEnhance_DT_PutSpread
    # },
    # {
    #     'class': EXOShortEnhance_DT_2
    # },
    # {
    #     'class': EXOShortEnhance_DT_2_CallSpread
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_20_60_longs
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_20_80_longs
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_60_20_shorts
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_80_20_shorts
    # },
    # {
    #     'class': EXOCallSpread_DynKel_Shorts
    # },
    # {
    #     'class': EXOPutSpread_DynKel_Longs
    # },
    # {
    #     'class': EXOCallSpread_DynKel_shorts_lp
    # },
    # {
    #     'class': EXOPutSpread_DynKel_longs_lp
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_20_80_longs_lp
    # },
    # {
    #     'class': EXOSemiFuture_DynKel_80_20_shorts_lp
    # },


    #new separate legs
    #Longs
    #PAIRED
    {
        'class': EXO_Active_leg_Short_Put_For_Bullish_PutSpread
    },
    # {
    #     'class': EXO_Passive_leg_Long_Put_For_Bullish_PutSpread
    # },
    #
    # #PAIRED
    # {
    #     'class': EXO_RiskReversal_Active_Calls_For_Longs_DynKel_20_80_Longs
    # },
    # {
    #     'class': EXO_RiskReversal_Passive_Puts_For_Longs_DynKel_20_80_Longs
    # },
    #
    # #Shorts
    # #PAIRED
    # {
    #     'class': EXO_Active_leg_Short_Call_For_Bearish_CallSpread
    # },
    # {
    #     'class': EXO_Passive_leg_Long_Call_For_Bearish_CallSpread
    # },
    #
    # #PAIRED
    # {
    #     'class': EXO_RiskReversal_Active_Calls_For_Shorts_DynKel_80_20_Shorts
    # },
    # {
    #     'class': EXO_RiskReversal_Passive_Puts_For_Shorts_DynKel_80_20_Shorts
    # },
    #
    # #PAIRED
    # {
    #     'class': EXO_RiskReversal_Active_Puts_For_Shorts_DynKel_80_20_Shorts
    # },
    # {
    #     'class': EXO_RiskReversal_Passive_Calls_For_Shorts_DynKel_80_20_Shorts
    # },


    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOSemiFuture_DynKel_20_80_Longs
    # },
    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOSemiFuture_DynKel_80_20_Longs
    # },
    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOWeeklyCalendarRiskRestrictionShorts
    # },
    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOWeeklyCalendarRiskRestrictionLongs
    # },
    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOWeeklyCalendarPutSpread
    # },
    # {
    #     'instrument':'US.ES',
    #     'class': ES_EXOWeeklyCalendarRiskReversalLong
    # }
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