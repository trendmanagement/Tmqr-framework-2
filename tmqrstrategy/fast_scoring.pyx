cimport cython
import numpy as np
import pandas as pd
cimport numpy as np

DTYPE_float = np.float
ctypedef np.float64_t DTYPE_t_float
ctypedef np.uint64_t DTYPE_t_uint64
ctypedef np.uint8_t DTYPE_t_uint8

np.import_array()

# TODO: unittest this module!

def exposure(data,
             np.ndarray[DTYPE_t_uint8, ndim=1, cast=True] entry_rule,
             np.ndarray[DTYPE_t_uint8, ndim=1, cast=True] exit_rule,
             int direction):
    cdef np.ndarray[DTYPE_t_float, ndim=1] price = data.values

    cdef int inpos = 0
    cdef int i = 0
    cdef float pnl = 0.0
    cdef float px = 0.0
    cdef int barcount = price.shape[0]

    cdef np.ndarray[DTYPE_t_float, ndim=1] pl = np.zeros(barcount)
    cdef np.ndarray[DTYPE_t_uint8, ndim=1] inpositon = np.zeros(barcount, dtype=np.uint8)

    for i in range(barcount):
        if inpos == 0:
            # We have a signal, let's open position
            if entry_rule[i] == 1:
                inpos = 1
                inpositon[i] = direction
            else:
                inpositon[i] = 0

        else:
            # Calculate pl
            if exit_rule[i] == 1:
                inpos = 0
                inpositon[i] = 0
            else:
                inpositon[i] = direction

    return pd.Series(inpositon, index=data.index)

def calc_costs(float transaction_costs, float rollover_costs, float prev_exp, float current_exp):
    # If rollover occurred
    cdef float _costs_value = 0.0
    if rollover_costs != 0:
        _costs_value += (-abs(rollover_costs) * abs(prev_exp))

    _costs_value += (-abs(transaction_costs) * abs(prev_exp - current_exp))

    return _costs_value

@cython.cdivision(True)
@cython.boundscheck(False)
def score_netprofit(np.ndarray[DTYPE_t_float, ndim=1] price_series,
                    exposure,
                    costs=None):
    # Calculate trade-by-trade payoffs
    cdef float profit = 0.0
    cdef int entry_i = -1

    cdef np.ndarray[DTYPE_t_float, ndim=1] _price = price_series

    try:
        _exposure = exposure.values
    except AttributeError:
        _exposure = exposure

    cdef int barcount = _price.shape[0]

    cdef int i = 0
    cdef int v = 0
    cdef float _costs_value = 0.0
    cdef float current_exp = 0.0
    cdef float prev_exp = 0.0

    cdef int has_costs = costs is not None

    cdef np.ndarray[DTYPE_t_float, ndim=1] rollover_costs
    cdef np.ndarray[DTYPE_t_float, ndim=1] transaction_costs

    if has_costs:
        transaction_costs = costs

    for i in range(1, barcount):
        # Calculate cumulative profit inside particular trade
        current_exp = _exposure[i]
        prev_exp = _exposure[i - 1]

        profit += (_price[i] - _price[i - 1]) * prev_exp

        # Apply transaction costs
        if has_costs:
            _costs_value = calc_costs(transaction_costs[i], 0, prev_exp, current_exp)
            profit += _costs_value

    return profit
