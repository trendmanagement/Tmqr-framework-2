cimport numpy as np
import cython
import numpy as np
from tmqr.errors import ArgumentError, IntradayQuotesNotFoundError


DTYPE = np.float
ctypedef np.float64_t DTYPE_t


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def find_quotes(df, timestamps_list):

    cdef DTYPE_t _last_px
    cdef np.uint64_t[:] npdatetime = df.index.tz_localize(None).values.astype('datetime64[s]').view(np.uint64)

    cdef int barcount = len(df)
    cdef int i = 0
    cdef int ts_idx = 0
    values = []

    if len(timestamps_list) == 0:
        return []

    dates = []
    for t in timestamps_list:
        # Make sure that timezones are equal
        if t.tzinfo.zone != df.index.tzinfo.zone:
            raise ArgumentError("timestamps_list's and quotes dataframe timezones are not equal")

        dates.append(np.datetime64(t.replace(tzinfo=None)))

    # Create Numpy sorted dates array
    # Converting timestamps to 'second' resolution and view them as int64, to get valid comparison with DF index
    cdef np.uint64_t[:] target_timestamps = np.array(dates, dtype='datetime64[s]').view(np.uint64)

    # Performing fast binary search of timestamps
    cdef np.ndarray[np.int64_t, ndim=1] ts_indexes = np.searchsorted(npdatetime, target_timestamps)

    # Do errors checks
    result = []
    for i in range(len(ts_indexes)):
        ts_idx = ts_indexes[i]
        if ts_idx == 0:
            # Quote is not found
            raise IntradayQuotesNotFoundError(f"Quote is not found at {timestamps_list[i]}")
        elif ts_idx == barcount:
            # We have quotes, but couldn't find exact bar, just picking previous bar price
            result.append((df.index[ts_idx-1], df['c'][ts_idx-1]))
        else:
            if npdatetime[ts_idx] == target_timestamps[i]:
                # Exact quotes match
                result.append((df.index[ts_idx], df['c'][ts_idx]))
            else:
                # We have quotes, but couldn't find exact bar, just picking previous bar price
                result.append((df.index[ts_idx-1], df['c'][ts_idx-1]))
    return result
