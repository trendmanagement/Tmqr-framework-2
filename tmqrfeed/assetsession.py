import re
from datetime import datetime, time

import pandas as pd

from tmqr.errors import SettingsError, ArgumentError


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
        self.tz = tz
        self._check_integrity(sessions)
        self.sessions = self.parse(sessions)

    def parse(self, session_list):
        result = []
        for sess in session_list:
            result.append({
                'dt': sess['dt'].replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=self.tz),
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
        return time(hh, mm, tzinfo=self.tz)

    def get(self, date):
        """
        Get trading session params for particular date
        :param date: datetime like object
        :return: tuple of (start, decision, execution) tz-aware dates for particular date
        """
        start, decision, execution, next_sess_date = self._get_sess_params(date)
        return start, decision, execution

    def _get_sess_params(self, date):
        for i, sess in enumerate(reversed(self.sessions)):
            if date >= sess['dt']:
                start = datetime.combine(date, sess['start'])
                decision = datetime.combine(date, sess['decision'])
                execution = datetime.combine(date, sess['execution'])
                if i > 0:
                    next_sess_date = self.sessions[len(self.sessions) - i]['dt']
                else:
                    next_sess_date = None
                return start, decision, execution, next_sess_date

        raise SettingsError("Trading sessions information doesn't contain records for so early date, "
                            "try to add '1900-01-01' record to implement default session")

    def filter_dataframe(self, dataframe):
        """
        Creates filtered dataframe and removes out-of-session datapoints
        :param dataframe:
        :return:
        """
        if dataframe.index.tz != self.tz:
            raise ArgumentError("DataFrame timezone info mismatch. DataFrame TZ: {0} Session TZ: {1}".format(
                dataframe.index.tz, self.tz
            ))

        df_list = []
        for i in range(1, len(self.sessions)):
            if i < len(self.sessions) - 1:
                date_start = self.sessions[i - 1]['dt']
                date_end = self.sessions[i]['dt']
                time_start = self.sessions[i - 1]['start']
                time_end = self.sessions[i - 1]['decision']
            else:
                date_start = self.sessions[i - 1]['dt']
                date_end = datetime(2100, 1, 1)
                time_start = self.sessions[i - 1]['start']
                time_end = self.sessions[i - 1]['decision']

            tmp_df = dataframe.ix[date_start:date_end]
            df_list.append(tmp_df.between_time(time_start, time_end))

        return pd.concat(df_list)
