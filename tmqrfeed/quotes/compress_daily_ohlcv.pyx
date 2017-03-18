cimport numpy as np
import numpy as np
DTYPE = np.float
ctypedef np.float64_t DTYPE_t
import pandas as pd


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def compress_daily(dfg, asset):
    """
    Calculate OHLCV based on 1-min data from PreProcessor
    :param dfg: DataFrameGetter instance
    :return:
    """

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

    exec_values = []
    exec_values_index = []

    # Session filter settings
    asset_session = asset.instrument_info.session
    cdef np.uint64_t sess_start = -1
    cdef np.uint64_t sess_decision = -1
    cdef np.uint64_t sess_execution = -1
    cdef np.uint64_t sess_next_date = -1

    cdef int is_newday = 1 #

    for i in range(count):
        # If new day occurred
        if last_date != npdate[i]:
            if last_date_idx >= 0:
                # Store previous OHLCV values
                values.append(
                    {
                        'o': _o,
                        'h': _h,
                        'l': _l,
                        'c': _c,
                        'v': _v,
                    }
                )
                values_index.append(npdate_buf[last_date_idx])

                # Store exec values
                exec_values.append({
                        'date': npdate_buf[last_date_idx],
                        'quote_time': dfg.index[exec_i],
                        'px': _exec_px,
                        'qty': 1,
                        'asset': asset,
                    }
                )

            # Calculate trading session params
            sess_start, sess_decision, sess_execution, sess_next_date = asset_session.get(dfg.index[i],
                                                                                          numpy_dtype=True)
            last_date = npdate[i]
            last_date_idx = i
            is_newday = 1


        if npdatetime[i] < sess_start or npdatetime[i] >= sess_execution:
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
            if npdatetime[i] < sess_decision:
                _h = max(_h, data[ih, i])
                _l = min(_l, data[il, i])
                _c = data[ic, i]
                _v += data[iv, i]
                _exec_px = _c
                exec_i = i
            else:
                _exec_px = _c
                exec_i = i


    # Process last values
    values.append(
                    {
                        'o': _o,
                        'h': _h,
                        'l': _l,
                        'c': _c,
                        'v': _v,
                    }
                )
    # Store exec values
    exec_values.append({
            'date': npdate_buf[last_date_idx],
            'quote_time': dfg.index[exec_i],
            'px': _exec_px,
            'qty': 1,
            'asset': asset,
        }
    )
    # TODO: need to use DATE + decision time as DF timestamps
    values_index.append(npdate_buf[last_date_idx])
    df_result = pd.DataFrame(values, index=values_index)
    df_result.index.rename('dt', inplace=True)
    return df_result, pd.DataFrame(exec_values).set_index(['date', 'asset'])
