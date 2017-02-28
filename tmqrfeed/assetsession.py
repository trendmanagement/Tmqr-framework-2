import re
from datetime import datetime, time


class AssetSession:
    """
    Implementation of instrument session handling
    """

    def __init__(self, sessions, tz):
        """
        Init asset session class
        :param sessions: list of sessions values
        :param tz: pytz instance of sessions
        """
        self.sessions = sessions
        self.tz = tz
        self._check_integrity()

    def _check_integrity(self):
        """
        Checks the validity of input data
        :return:
        """

        def _check_time(session, name):
            str_time = session[name]
            if re.match(r'^\d\d:\d\d$', str_time) is None:
                raise ValueError("Wrong time pattern for '{0}' required 'HH:MM' but '{1}' given".format(name,
                                                                                                        str_time
                                                                                                        ))

        if self.sessions is None or len(self.sessions) == 0:
            raise ValueError("Asset trading session settings are empty")

        last_date = None
        for s in self.sessions:
            #
            #  Key presence checks
            #
            if 'decision' not in s:
                raise ValueError("'decision' record missing in session info")
            if 'dt' not in s:
                raise ValueError("'dt' record missing in session info")
            if 'execution' not in s:
                raise ValueError("'execution' record missing in session info")
            if 'start' not in s:
                raise ValueError("'start' record missing in session info")
            #
            # Values checks
            #
            _check_time(s, 'decision')
            _check_time(s, 'execution')
            _check_time(s, 'start')

            if not isinstance(s['dt'], datetime):
                raise ValueError("'dt' must be datetime instance")

            if last_date is None:
                last_date = s['dt'].date()
            else:
                if s['dt'].date() < last_date:
                    raise ValueError("Session dates must be in ascending order")
                if s['dt'].date() == last_date:
                    raise ValueError("Session dates are duplicated")

    def _time_combine(self, source_date, str_time):
        """
        Produce datetime instance from source_date and str_time ('HH:MM' pattern) + adds timezone info
        :param source_date: Base date
        :param str_time: Session time string pattern 'HH:MM'
        :return:
        """
        hh = int(str_time[:2])
        mm = int(str_time[3:])
        return datetime.combine(source_date.date(),
                                time(hh, mm, tzinfo=self.tz))

    def __getitem__(self, item):
        """
        Get trading session params for particular date
        :param item: datetime like object
        :return: tuple of (start, decision, execution) tz-aware dates for particular date
        """
        for i, sess in enumerate(reversed(self.sessions)):
            if item.date() >= sess['dt'].date():
                start = self._time_combine(item, sess['start'])
                decision = self._time_combine(item, sess['decision'])
                execution = self._time_combine(item, sess['execution'])
                return start, decision, execution

        raise ValueError("Trading sessions information doesn't contain records for so early date, "
                         "try to add '1900-01-01' record to implement default session")
