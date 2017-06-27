import re
from datetime import time, timedelta

from tmqr.errors import SettingsError, ArgumentError
from tmqr.settings import *


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
        self.sessions_serialized = sessions
        self.tz = tz

        self._check_integrity(sessions)
        self.sessions = self.parse(sessions)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return other.sessions == self.sessions and other.tz == self.tz

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return str(self.sessions_serialized)

    def __repr__(self):
        return self.__str__()

    def serialize(self):
        return {
            'trading_session': self.sessions_serialized,
            'tz': self.tz.zone
        }

    def parse(self, session_list):
        result = []
        for sess in session_list:
            result.append({
                'dt': sess['dt'].replace(hour=0, minute=0, second=0, microsecond=0),
                'decision': self._time_parse(sess['decision']),
                'start': self._time_parse(sess['start']),
                'execution': self._time_parse(sess['execution']),
            })
        return result

    def _check_integrity(self, session):
        """
        Checks the validity of input data
        :return:
        """

        def _check_time(session, name):
            str_time = session[name]
            if re.match(r'^\d\d:\d\d$', str_time) is None:
                raise SettingsError("Wrong time pattern for '{0}' required 'HH:MM' but '{1}' given".format(name,
                                                                                                           str_time
                                                                                                           ))

        if session is None or len(session) == 0:
            raise SettingsError("Asset trading session settings are empty")

        last_date = None
        for s in session:
            #
            #  Key presence checks
            #
            if 'decision' not in s:
                raise SettingsError("'decision' record missing in session info")
            if 'dt' not in s:
                raise SettingsError("'dt' record missing in session info")
            if 'execution' not in s:
                raise SettingsError("'execution' record missing in session info")
            if 'start' not in s:
                raise SettingsError("'start' record missing in session info")
            #
            # Values checks
            #
            _check_time(s, 'decision')
            _check_time(s, 'execution')
            _check_time(s, 'start')

            if not isinstance(s['dt'], datetime):
                raise SettingsError("'dt' must be datetime instance")

            if last_date is None:
                last_date = s['dt'].date()
            else:
                if s['dt'].date() < last_date:
                    raise SettingsError("Session dates must be in ascending order")
                if s['dt'].date() == last_date:
                    raise SettingsError("Session dates are duplicated")

    def _time_parse(self, str_time):
        """
        Produce datetime instance from source_date and str_time ('HH:MM' pattern) + adds timezone info
        :param str_time: Session time string pattern 'HH:MM'
        :return:
        """
        hh = int(str_time[:2])
        mm = int(str_time[3:])
        return time(hh, mm)

    def get(self, date, decision_time_shift=0):
        """
        Get trading session params for particular date
        :param date: datetime like object
        :param decision_time_shift: decision time offset in minutes
        :return: tuple of (start, decision, execution, next_sess_date) tz-aware dates for particular date
        """
        if decision_time_shift < 0:
            raise ArgumentError("'decision_time_shift' argument must be >= 0")

        return self._get_sess_params(date, decision_time_shift)

    def _get_sess_params(self, date, decision_time_shift=0):
        if date.tzinfo is None:
            dt = date
        else:
            dt = date.replace(tzinfo=None)

        for i, sess in enumerate(reversed(self.sessions)):
            if dt >= sess['dt']:
                start = self.tz.localize(datetime.combine(dt, sess['start']))
                decision = self.tz.localize(datetime.combine(dt, sess['decision'])) - timedelta(
                    minutes=decision_time_shift)
                execution = self.tz.localize(datetime.combine(dt, sess['execution']))
                if i > 0:
                    next_sess_date = self.tz.localize(self.sessions[len(self.sessions) - i]['dt'])
                else:
                    next_sess_date = None
                return start, decision, execution, next_sess_date

        raise SettingsError("Trading sessions information doesn't contain records for so early date, "
                            "try to add '1900-01-01' record to implement default session")
