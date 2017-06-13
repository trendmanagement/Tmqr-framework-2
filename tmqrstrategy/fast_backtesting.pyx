cimport cython
import numpy as np
import pandas as pd
cimport numpy as np
from tmqr.errors import ArgumentError

DTYPE_float = np.float
ctypedef np.float64_t DTYPE_t_float
ctypedef np.uint64_t DTYPE_t_uint64
ctypedef np.uint8_t DTYPE_t_uint8

np.import_array()


@cython.cdivision(True)
@cython.boundscheck(False)
def exposure(np.ndarray[DTYPE_t_float, ndim=1] price_series,
             np.ndarray[DTYPE_t_uint8, ndim=1, cast=True] entry_rule,
             np.ndarray[DTYPE_t_uint8, ndim=1, cast=True] exit_rule,
             int direction,
             size_exposure=None,
             int nbar_stop=0
             ):
    """
    Fast implementation of exposure Series calculation based on entry and exit rules
    :param price_series: price series
    :param entry_rule: boolean series entry rule
    :param exit_rule: boolean series exit rule
    :param direction: trade direction
    :param size_exposure: exposure size, can be integer or series (for custom sized entries) (default: 1.0)
    :param nbar_stop: implement exit in number of bars after entry point
    :return: pd.Series of exposure values
    """

    cdef int inpos = -1  # inpos - last index of the entry bar
    cdef int i = 0
    cdef float pnl = 0.0
    cdef float px = 0.0
    cdef int barcount = price_series.shape[0]

    if len(entry_rule) != barcount:
        raise ArgumentError("'entry_rule' length != price length")
    if len(exit_rule) != barcount:
        raise ArgumentError("'exit_rule' length != price length")

    cdef np.ndarray[DTYPE_t_float, ndim=1] exposure = np.zeros(barcount)
    cdef np.ndarray[DTYPE_t_float, ndim=1] qty_arr

    if size_exposure is None:
        qty_arr = np.ones(barcount, dtype=np.float)
    elif isinstance(size_exposure, (float, int, np.float, np.int)):
        qty_arr = np.ones(barcount, dtype=np.float) * size_exposure
    else:
        if len(size_exposure) != barcount:
            raise ArgumentError("'size_exposure' length != price length")

        if isinstance(size_exposure, pd.Series):
            qty_arr = size_exposure.values
        else:
            qty_arr = size_exposure

    for i in range(barcount):
        if inpos == -1:
            # We have a signal, let's open position
            if entry_rule[i] == 1:
                inpos = i
                exposure[i] = direction * qty_arr[inpos]
            else:
                exposure[i] = 0.0

        else:
            # Calculate pl
            if exit_rule[i] == 1 or (nbar_stop > 0 and (i - inpos) >= nbar_stop):
                inpos = -1
                exposure[i] = 0.0
            else:
                exposure[i] = direction * qty_arr[inpos]

    return exposure

@cython.cdivision(True)
@cython.boundscheck(False)
def exposure_trades(np.ndarray[DTYPE_t_float, ndim=1] price_series,
                    np.ndarray[DTYPE_t_float, ndim=1] exposure,
                    costs=None):
    """
    Get exposure based trades PnL array
    :param price_series: price series
    :param exposure: exposure values
    :param costs: costs per 1 contract of exposure (if None - no costs)
    :return:
    """
    # Calculate trade-by-trade payoffs
    cdef float profit = 0.0
    cdef int entry_i = -1

    cdef int barcount = price_series.shape[0]

    cdef int i = 0
    cdef int v = 0
    cdef float _costs_value = 0.0
    cdef float current_exp = 0.0
    cdef float prev_exp = 0.0
    cdef int _trade_start_i = -1

    cdef int has_costs = costs is not None

    if len(exposure) != barcount:
        raise ArgumentError("'exposure' length is not equal to 'price_series' length")

    cdef np.ndarray[DTYPE_t_float, ndim=1] transaction_costs

    if has_costs:
        if isinstance(costs, (float, int, np.float, np.int)):
            transaction_costs = np.ones(barcount, dtype=np.float) * float(costs)
        else:
            if len(costs) != barcount:
                raise ArgumentError("'costs' length != price length")
            transaction_costs = costs

    trades_list = []

    for i in range(1, barcount):
        # Calculate cumulative profit inside particular trade
        current_exp = exposure[i]
        prev_exp = exposure[i - 1]

        if _trade_start_i == -1 and current_exp != 0:
            assert prev_exp == 0
            _trade_start_i = i
            profit = 0.0

        if _trade_start_i != -1:
            profit += (price_series[i] - price_series[i - 1]) * prev_exp

            # Apply transaction costs
            if has_costs:
                _costs_value = calc_costs(transaction_costs[i], 0, prev_exp, current_exp)
                profit += _costs_value

            # We are in trade
            if i == barcount - 1 or current_exp == 0:
                # Add unclosed trades to list and handle exit signals
                trades_list.append(profit)
                _trade_start_i = -1

    return np.array(trades_list)

#
# Scoring functions
#
cdef float calc_costs(float transaction_costs, float rollover_costs, float prev_exp, float current_exp):
    """
    Internal C-compiled costs function
    :param transaction_costs: 
    :param rollover_costs: 
    :param prev_exp: 
    :param current_exp: 
    :return: 
    """
    # If rollover occurred
    cdef float _costs_value = 0.0
    if rollover_costs != 0:
        _costs_value += (-abs(rollover_costs) * abs(prev_exp))

    _costs_value += (-abs(transaction_costs) * abs(prev_exp - current_exp))

    return _costs_value

@cython.cdivision(True)
@cython.boundscheck(False)
def score_netprofit(np.ndarray[DTYPE_t_float, ndim=1] price_series,
                    np.ndarray[DTYPE_t_float, ndim=1] exposure,
                    costs=None):
    """
    Fast score metric: NetProfit
    :param price_series: price series
    :param exposure: exposure values
    :param costs: costs per 1 contract of exposure (if None - no costs)
    :return:
    """
    # Calculate trade-by-trade payoffs
    cdef float profit = 0.0
    cdef int entry_i = -1

    cdef int barcount = price_series.shape[0]

    cdef int i = 0
    cdef int v = 0
    cdef float _costs_value = 0.0
    cdef float current_exp = 0.0
    cdef float prev_exp = 0.0

    cdef int has_costs = costs is not None

    if len(exposure) != barcount:
        raise ArgumentError("'exposure' length is not equal to 'price_series' length")

    cdef np.ndarray[DTYPE_t_float, ndim=1] transaction_costs

    if has_costs:
        if isinstance(costs, (float, int, np.float, np.int)):
            transaction_costs = np.ones(barcount, dtype=np.float) * float(costs)
        else:
            if len(costs) != barcount:
                raise ArgumentError("'costs' length != price length")
            transaction_costs = costs

    for i in range(1, barcount):
        # Calculate cumulative profit inside particular trade
        current_exp = exposure[i]
        prev_exp = exposure[i - 1]

        profit += (price_series[i] - price_series[i - 1]) * prev_exp

        # Apply transaction costs
        if has_costs:
            _costs_value = calc_costs(transaction_costs[i], 0, prev_exp, current_exp)
            profit += _costs_value

    return profit

@cython.cdivision(True)
@cython.boundscheck(False)
def score_modsharpe(np.ndarray[DTYPE_t_float, ndim=1] price_series,
                    np.ndarray[DTYPE_t_float, ndim=1] exposure,
                    costs=None):
    """
    Fast score metric: ModSharpe = ( Avg(TradeProfit) / StDev(TradeProfit) )
    :param price_series: price series
    :param exposure: exposure values
    :param costs: costs per 1 contract of exposure (if None - no costs)
    :return: is trades count < 5 returns float('nan')
    """
    cdef np.ndarray[DTYPE_t_float, ndim=1] trades = exposure_trades(price_series, exposure, costs)

    if len(trades) < 5:
        return float('nan')

    return np.mean(trades) / np.std(trades)
