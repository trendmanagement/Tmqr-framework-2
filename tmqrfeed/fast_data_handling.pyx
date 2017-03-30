
import cython
import numpy as np

from tmqr.errors import ArgumentError



DTYPE = np.float
ctypedef np.float64_t DTYPE_t


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def find_time_indexes(df, timestamps_list):

    cdef DTYPE_t _last_px
    cdef np.uint64_t[:] npdatetime = df.index.tz_localize(None).values.astype('datetime64[s]').view(np.uint64)

    cdef int count = len(df)
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
    cdef np.uint64_t[:] target_timestamps = np.array(dates, dtype='datetime64[s]').view(np.uint64)


    cdef np.ndarray[np.int64_t, ndim=1] ts_indexes = np.searchsorted(npdatetime, target_timestamps)

    return ts_indexes
