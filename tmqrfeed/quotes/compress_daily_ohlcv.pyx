import cython
import numpy as np
cimport numpy as np

from tmqrfeed.position import Position


DTYPE = np.float
ctypedef np.float64_t DTYPE_t
import pandas as pd
from datetime import timedelta


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def compress_daily(dfg, asset, asset_session, int decision_time_shift=0):
    """
    Calculate OHLCV based on 1-min data from PreProcessor
    :param dfg: DataFrameGetter instance
    :return:
    """
    if decision_time_shift < 0:
        raise ValueError("'decision_time_shift' arg must be >= 0")

    cdef DTYPE_t _o, _h, _l, _c, _v, _exec_px

    npdate_buf = dfg.index.values.astype('datetime64[D]')

    cdef np.uint64_t[:] npdate = npdate_buf.view(np.uint64)
    cdef np.uint64_t[:] npdatetime = dfg.index.values.astype('datetime64[s]').view(np.uint64)

    cdef np.ndarray[DTYPE_t, ndim=2] data = dfg.data

    cdef int io = dfg.cols['o']
    cdef int ih = dfg.cols['h']
    cdef int il = dfg.cols['l']
    cdef int ic = dfg.cols['c']
    cdef int iv = dfg.cols['v']
    cdef int count = data.shape[1]
    cdef int i = 0
    cdef int exec_i = 0
    cdef np.uint64_t last_date = -1
    cdef int last_date_idx = -1
    values = []
    values_index = []

    position = Position(asset.dm, decision_time_shift=decision_time_shift)

    # Session filter settings
    cdef np.uint64_t sess_start = -1
    cdef np.uint64_t sess_decision = -1
    cdef np.uint64_t sess_execution = -1
    cdef np.uint64_t sess_next_date = -1
    dt_sess_start = dt_sess_decision = dt_sess_exec = dt_sess_next = None


    cdef int is_newday = 1 #

    for i in range(count):
        # If new day occurred
        if last_date != npdate[i]:
            if not is_newday:
                # Store previous OHLCV values
                values.append(
                    {
                        'o': _o,
                        'h': _h,
                        'l': _l,
                        'c': _c,
                        'v': _v,
                        'exec': _exec_px,
                    }
                )
                values_index.append(dt_sess_decision)

                # Store exec values in position
                position.set_net_position(dt_sess_decision, {asset: (_c, _exec_px, 1)})

            # Calculate trading session params
            dt_sess_start, dt_sess_decision, dt_sess_exec, dt_sess_next = asset_session.get(dfg.index[i], decision_time_shift)

            sess_start = np.datetime64(dt_sess_start.replace(tzinfo=None)).astype('datetime64[s]').view(np.uint64)
            sess_decision = np.datetime64(dt_sess_decision.replace(tzinfo=None)).astype('datetime64[s]').view(np.uint64)
            sess_execution = np.datetime64(dt_sess_exec.replace(tzinfo=None)).astype('datetime64[s]').view(np.uint64)

            last_date = npdate[i]
            last_date_idx = i
            is_newday = 1

        if npdatetime[i] < sess_start or npdatetime[i] > sess_execution:
            continue



        if is_newday:
            _o = data[io, i]
            _h = data[ih, i]
            _l = data[il, i]
            _c = data[ic, i]
            _v = data[iv, i]
            _exec_px = _c
            exec_i = i
            is_newday = 0
        else:
            if npdatetime[i] <= sess_decision:
                _h = max(_h, data[ih, i])
                _l = min(_l, data[il, i])
                _c = data[ic, i]
                _v += data[iv, i]
                _exec_px = _c
                exec_i = i
            else:
                _exec_px = data[ic, i]
                exec_i = i

    if not is_newday:
        # Process last values
        values.append(
            {
                'o': _o,
                'h': _h,
                'l': _l,
                'c': _c,
                'v': _v,
                'exec': _exec_px,
            }
        )
        # Store exec values
        position.set_net_position(dt_sess_decision, {asset: (_c, _exec_px, 1)})

        values_index.append(dt_sess_decision)

    df_result = pd.DataFrame(values, index=values_index)
    df_result.index.rename('dt', inplace=True)
    return df_result, position
