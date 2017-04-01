import cython
from libc.math cimport exp, log, sqrt

@cython.cdivision(True)
cdef float cnd(float d):
    cdef float a1 = 0.31938153
    cdef float a2 = -0.356563782
    cdef float a3 = 1.781477937
    cdef float a4 = -1.821255978
    cdef float a5 = 1.330274429
    cdef float rsqrt2pi = 0.39894228040143267793994605993438
    cdef float k = 1.0 / (1.0 + 0.2316419 * abs(d))
    cdef float ret_val = (rsqrt2pi * exp(-0.5 * d * d) *
                          (k * (a1 + k * (a2 + k * (a3 + k * (a4 + k * a5))))))
    if d > 0:
        return 1.0 - ret_val
    else:
        return ret_val

@cython.cdivision(True)
def blackscholes(int iscall, float ulprice, float strike, float toexpiry, float riskfreerate, float iv):
    cdef float  bsPrice = 0.0
    cdef float d1
    cdef float d2
    if toexpiry <= 0:
        # Calculate payoff at expiration
        if iscall == 1:
            return max(0.0, ulprice - strike)
        else:
            return max(0.0, strike - ulprice)

    d1 = (log(ulprice / strike) + (riskfreerate + iv * iv / 2) * toexpiry) / (iv * sqrt(toexpiry))
    d2 = d1 - iv * sqrt(toexpiry)

    if iscall == 1:
        bsPrice = ulprice * cnd(d1) - strike * exp(-riskfreerate * toexpiry) * cnd(d2)
    else:
        bsPrice = strike * exp(-riskfreerate * toexpiry) * cnd(-d2) - ulprice * cnd(-d1)
    return bsPrice
