
import cython
import numpy as np

DTYPE = np.float
ctypedef np.float64_t DTYPE_t


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def find_time_indexes(dfg, timestamps_list):

    cdef DTYPE_t _last_px
    cdef np.uint64_t[:] npdatetime = dfg.index.values.astype('datetime64[s]').view(np.uint64)

    cdef np.ndarray[DTYPE_t, ndim=2] data = dfg.data

    cdef int ic = dfg.cols['c']
    cdef int count = data.shape[1]
    cdef int i = 0
    cdef int ts_idx = 0
    values = []

    if len(timestamps_list) == 0:
        return []

    dates = []
    for t in timestamps_list:
        # Make sure that timezones are equal
        if t.tzinfo.zone != dfg.tz.zone:
            # TODO: change to argument error
            raise ValueError("timestamps_list's and quotes dataframe timezones are inequal")

        dates.append(np.datetime64(t.replace(tzinfo=None)))

    # Create Numpy sorted dates array
    cdef np.uint64_t[:] target_timestamps = np.array(dates, dtype='datetime64[s]').view(np.uint64)


    cdef np.ndarray[np.int64_t, ndim=1] ts_indexes = np.searchsorted(npdatetime, target_timestamps)

    return ts_indexes
