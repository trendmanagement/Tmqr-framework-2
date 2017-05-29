from datetime import datetime, date, time, timedelta

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY, WEEKLY

from tmqr.errors import ArgumentError
from tmqrfeed.position import Position


class StrategyBase:
    def __init__(self, datamanager, **kwargs):
        self.dm = datamanager

        self.position = kwargs.get('position', Position(self.dm))
        self.wfo_params = kwargs.get('wfo_params', None)

        if self.wfo_params is None:
            raise ArgumentError("Walk-forward optimization params are not set, check 'wfo_params' kwarg")

    def setup(self):
        """
        Initiate alpha algorithm
        - Setting up quotes data
        - Setting up ML model
        etc...
        :return: nothing, class instance can populate internal values 
        """
        pass

    #
    # Private methods
    #

    def _make_wfo_matrix(self):
        """
        Creates walk-forward optimization matrix, which contains periods and types of walk-forward steps
        :return: 
        """
        wfo_period = self.wfo_params['period'].lower()
        wfo_oos_periods = self.wfo_params['oos_periods']
        wfo_iis_periods = self.wfo_params['iis_periods']
        wfo_window_type = self.wfo_params['window_type'].lower()

        dt_idx = self.dm.quotes().index
        first_date = dt_idx[0]
        last_date = dt_idx[-1]

        # TODO: implement online recalculation and test

        start_date = date(first_date.year, 1, 1)
        end_date = last_date.date()
        if wfo_period == 'm':
            period_count = round((end_date - start_date).days / 30 / wfo_oos_periods) + 2
            rdelta_window = relativedelta(months=wfo_iis_periods)

            if wfo_oos_periods not in [1, 2, 3, 4, 6, 12]:
                raise ArgumentError("Keep WFO 'oos_periods' in [1, 2, 3, 4, 6, 12] to maintain IIS/OOS alignment")

            wfo_enumerator = rrule(freq=MONTHLY, count=period_count,
                                   # Note on:
                                   # dtstart=start_date + relativedelta(months=wfo_iis_periods-1),
                                   # Make sure that IIS months aligned properly
                                   # for interval=wfo_oos_periods
                                   # =2: Feb, Apr, Jun, Aug, Oct, Dec
                                   # =3: Mar, Jun, Sep, Dec
                                   # =4: Apr, Aug, Dec
                                   # =6: Jun, Dec
                                   # =12: Dec
                                   dtstart=start_date + relativedelta(months=wfo_iis_periods - 1),
                                   bysetpos=-1, byweekday=5, interval=wfo_oos_periods)

        elif wfo_period == 'w':
            period_count = round((end_date - start_date).days / 7) + 2
            rdelta_window = relativedelta(weeks=wfo_iis_periods)

            wfo_enumerator = rrule(freq=WEEKLY, count=period_count,
                                   dtstart=start_date,
                                   byweekday=5, interval=wfo_oos_periods)


        else:
            raise ArgumentError(f"Unexpected WFO 'period' value, expected 'W' or 'M', but got {wfo_period}")

        result = []
        prev_period = None

        for i, period_end in enumerate(wfo_enumerator):

            if i == 0 or period_end.date() - rdelta_window < first_date.date():
                # Make sure that starting IIS data is available
                prev_period = period_end
                continue

            if wfo_window_type == 'expanding':
                # Setting the IIS start period to the beginning of the quote history
                iis_start_dt = datetime.combine(first_date.date(), time(0, 0, 0))
            else:
                # Setting rolling window IIS period
                iis_start_dt = prev_period - rdelta_window

            result.append({
                'iis_start': iis_start_dt,
                'iis_end': prev_period,
                'oos_start': prev_period,
                'oos_end': period_end
            })

            if period_end.date() > end_date:
                break

            prev_period = period_end

        return result

    #
    #  Strategy calculation
    #
    def calculate(self, *args):
        """
        Calculate strategy logics
        :param args: optional strategy params (like MA periods, direction, etc)
        :return: Pandas.DataFrame aligned to primary quotes indexes and *'exposure'* column required, other columns
        also permitted to apply additional position management logic at the position initiation stage
        """
        raise NotImplementedError("You must implement 'calculate' method in child strategy class")

    def calculate_position(self, date, position, exposure_record):
        """
        Build position for current 'date' and 'exposure_record' of single alpha member
        :param date: date of the analysis
        :param position: position instance
        :param exposure_record: slice of 'exposure_df' at 'date'
        :return: nothing, processes position in place
        """
        pass

    def process_position(self, exposure_df_list):
        """
        Processes positions based on picked swarm members 'exposure_df_list'
        :param exposure_df_list: list of results of 'calculate' method for each picked swarm member
        :return: nothing, processes position in place 
        """
        pass

    #
    #  Strategy optimization
    #
    def score(self, exposure_df):
        """
        Optimization scoring method, produces a float number metric of strategy member performance, uses 'calculate'
        results (i.e. exposure_df) to calculate score number based on primary quotes 
        :param exposure_df: 'calculate' method exposure Pandas.DataFrame
        :return: float number
        """
        pass

    def pick(self, calculate_args_list):
        """
        Selection method from the list of strategy members' params in 'calculate_args_list'
        :param calculate_args_list: list of optimization arguments of 'calculate' method
        :return: List of the best performing 'calculate' args (i.e. swarm members)
        """
        pass

    #
    #  General methods
    #
    def run(self):
        """
        Run strategy instance and walk-forward optimization
        :return: 
        """
        # Code prototype

        # While position last_date < primary quotes last date
        #   If position last_date < next reopt date do:
        #        For period of 'begin trading window' to 'end reopt window':
        #        Get active alpha members
        #        Calculate exposure for each
        #        Process position of each
        pass

    @classmethod
    def load(cls, dm, strategy_name):
        """
        Loads strategy instance from DB
        :param dm: DataManager instance
        :param strategy_name: name of the strategy
        :return: StrategyClass instance
        """
        pass

    def save(self):
        """
        Saves strategy instance to the DB
        :return: 
        """
        pass
