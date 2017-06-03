from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY, WEEKLY
from tmqr.errors import ArgumentError, WalkForwardOptimizationError, QuoteNotFoundError, StrategyError
from tmqrfeed.position import Position
from tmqrfeed import DataManager

WFO_ACTION_SKIP = 0
WFO_ACTION_OPTIMIZE = 1
WFO_ACTION_RUN = 2
WFO_ACTION_BREAK = 4


class StrategyBase:
    def __init__(self, datamanager: DataManager, **kwargs):
        self.dm = datamanager

        self.position = kwargs.get('position', Position(self.dm))
        self.wfo_params = kwargs.get('wfo_params', None)

        if self.wfo_params is None:
            raise StrategyError("Walk-forward optimization params are not set, check 'wfo_params' kwarg")

        self.wfo_last_period = kwargs.get('last_period', None)
        self.wfo_selected_alphas = kwargs.get('selected_alphas', [])
        self.wfo_opt_params = kwargs.get('opt_params', [])
        self.wfo_optimizer_class = kwargs.get('optimizer_class', None)
        if self.wfo_optimizer_class is None:
            raise StrategyError("'optimizer_class' kwarg is not set.")

        self.wfo_optimizer_class_kwargs = kwargs.get('optimizer_class_kwargs', {})




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

            if prev_period.date() > end_date:
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

    def process_position(self, exposure_df_list, oos_start, oos_end):
        """
        Processes positions based on picked swarm members 'exposure_df_list'
        :param exposure_df_list: list of results of 'calculate' method for each picked swarm member
        :param oos_start: start date of the OOS
        :param oos_end: end date of the OOS
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
    @staticmethod
    def date_now():
        return datetime.now().date()

    @staticmethod
    def get_next_wfo_action(wfo_last_period, wfo_current_period, quotes_index):
        if len(quotes_index) < 2:
            raise WalkForwardOptimizationError("Insufficient primary quotes length")

        if wfo_last_period is None:
            # This is a first run
            if wfo_current_period['iis_end'].date() > quotes_index[0].date():
                # Run optimization
                return WFO_ACTION_OPTIMIZE
            else:
                # Searching the WFO period which match quotes range
                return WFO_ACTION_SKIP
        else:
            if wfo_last_period['oos_end'] == wfo_current_period['oos_end']:
                # This step only possible when previously saved strategy has run once again
                # Typically is's possible in 2 cases:
                # 1. Online / daily run (even prior online weekend re-optimization)
                # 2. When the strategy run is delayed for several days and new OOS window arrived
                return WFO_ACTION_RUN

            if wfo_last_period['oos_end'] > wfo_current_period['oos_end']:
                # This step only possible when previously saved strategy has run once again
                # Skip previous WFO periods before active one
                return WFO_ACTION_SKIP

            if wfo_current_period['oos_start'].date() > quotes_index[-1].date():
                if wfo_current_period['oos_start'].date() <= StrategyBase.date_now() <= wfo_current_period[
                    'oos_end'].date():
                    #
                    # Special case for online calculation, when we have last Friday's quotes available
                    #   and we need to run re-optimization at Saturday/Sunday this will force us to do it
                    return WFO_ACTION_OPTIMIZE

                # Break calculation when next oos date grater last quotes index
                return WFO_ACTION_BREAK

            if wfo_last_period['oos_end'].date() < quotes_index[-1].date() and \
                            wfo_last_period['oos_end'].date() < wfo_current_period['oos_end'].date():
                # We have the historical data beyond oos_end date
                # No next step optimization
                return WFO_ACTION_OPTIMIZE

        raise NotImplementedError('Not expected code flow')

    def run(self):
        """
        Run strategy instance and walk-forward optimization
        :return: 
        """
        # Initialize quotes
        self.setup()

        try:
            quotes_index = self.dm.quotes().index
        except QuoteNotFoundError:
            raise StrategyError("You should call 'self.dm.series_primary_set(...)' in strategy setup() "
                                "method to initialize quotes data")

        # Calculate WFO matrix for the historical data
        wfo_matrix = self._make_wfo_matrix()

        for wfo_period in wfo_matrix:
            wfo_action = self.get_next_wfo_action(self.wfo_last_period, wfo_period, quotes_index)

            if wfo_action == WFO_ACTION_SKIP:
                continue
            if wfo_action == WFO_ACTION_BREAK:
                break

            if wfo_action == WFO_ACTION_OPTIMIZE:
                # Set IIS range
                self.dm.quotes_range_set(wfo_period['iis_start'], wfo_period['iis_end'])

                # Do optimization and picking
                optimizer = self.wfo_optimizer_class(self, self.wfo_opt_params, **self.wfo_optimizer_class_kwargs)
                self.wfo_selected_alphas = optimizer.optimize()

                # Set WFO last period
                self.wfo_last_period = wfo_period

            # Reset quotes range to OOS
            self.dm.quotes_range_set(wfo_period['iis_start'], wfo_period['oos_end'])

            # Run predefined alphas params
            oos_exposure_df_list = []
            for alpha_params in self.wfo_selected_alphas:
                alpha_exposure_df = self.calculate(*alpha_params)
                oos_exposure_df_list.append(alpha_exposure_df)

            # Processing strategy position
            self.process_position(oos_exposure_df_list, wfo_period['oos_start'], wfo_period['oos_end'])

            # Reset quotes range
            self.dm.quotes_range_set()

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
