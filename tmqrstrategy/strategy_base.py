import time
from datetime import datetime, date
from datetime import time as dttime
from typing import List, Callable

import numpy as np
import pandas as pd
import pyximport
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY, WEEKLY

from tmqr.errors import ArgumentError, WalkForwardOptimizationError, QuoteNotFoundError, StrategyError, \
    PositionNotFoundError, ChainNotFoundError
from tmqr.logs import log
from tmqr.settings import QDATE_MIN
from tmqrfeed import DataManager
from tmqrfeed.position import Position

pyximport.install()
from tmqrstrategy.fast_backtesting import score_netprofit, exposure, score_modsharpe
from tmqr.serialization import object_from_path, object_to_full_path, object_load_decompress, object_save_compress

WFO_ACTION_SKIP = 0
WFO_ACTION_OPTIMIZE = 1
WFO_ACTION_RUN = 2
WFO_ACTION_BREAK = 4


class StrategyBase:
    def __init__(self, datamanager: DataManager, **kwargs):
        self.dm = datamanager  # type: DataManager

        self.position = kwargs.get('position', Position(self.dm))  # type: Position
        """Strategy position"""
        if not isinstance(self.position, Position):
            raise StrategyError(f"Expected to get Position type for kwarg['position'], got {type(self.position)}")

        self.name = kwargs.get('name', '')  # type: str
        """Explicit strategy name set in constructor (by default: uses strategy class name)"""

        if not self.name:
            raise StrategyError("You should set unique strategy 'name' in kwargs")

        self.wfo_params = kwargs.get('wfo_params', None)
        """ Walk-forward optimization parameters dictionary
        Example:
            wfo_params = {
                'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
                'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
                'oos_periods': 2,  # Number of months is OOS period
                'iis_periods': 2,  # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
            }
        """

        if self.wfo_params is None:
            raise StrategyError("Walk-forward optimization params are not set, check 'wfo_params' kwarg")

        self.wfo_last_period = kwargs.get('wfo_last_period', None)
        """Last WFO period IIS/OOS start/end dated information"""

        self.wfo_selected_alphas = kwargs.get('wfo_selected_alphas', [])
        """Selected alphas parameters for last OOS step"""

        self.wfo_opt_params = kwargs.get('wfo_opt_params', [])
        """
        Alpha strategy optimization parameters list
        Example:
        # Format: list of tuples ('param_name', param_values_list)
        opt_params = [
            ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
            ('period_fast', [1, 3, 10, 15, 20, 30])
        ]
        """

        self.wfo_scoring_type = kwargs.get('wfo_scoring_type', 'netprofit')
        """Scoring algorithm for swarm members estimation"""

        self.wfo_optimizer_class = kwargs.get('wfo_optimizer_class', None)  # type: Callable
        """OptimizerBase derived class (must be type, not the instance of the class!)"""

        self.wfo_costs_per_contract = kwargs.get('wfo_costs_per_contract', 0.0)
        """Costs per contract in $ used in scoring functions"""

        self.wfo_members_count = kwargs.get('wfo_members_count', 1)
        """Number of swarm members to select and trade at OOS stage of the WFO"""

        if self.wfo_optimizer_class is None:
            raise StrategyError("'wfo_optimizer_class' kwarg is not set.")

        self.wfo_optimizer_class_kwargs = kwargs.get('wfo_optimizer_class_kwargs', {})
        """Optimizer class extra parameters"""

        self.context = kwargs.get('context', {})
        """Extra strategy options (if required)"""

        self.exposure_series = kwargs.get('exposure_series', None)  # type: pd.DataFrame
        """Historical exposure values for OOS periods"""

        self.stats = kwargs.get('stats', {})
        """Alpha strategy backtest stats"""

    @property
    def strategy_name(self):
        """
        Strategy name, pass 'name' kwarg to strategy's constructor, or override this method.
        NOTE: This method could be overridden by child class to generate more sophisticated naming logic
        :return:
        """
        return self.name

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
                iis_start_dt = datetime.combine(first_date.date(), dttime(0, 0, 0))
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

    def exposure(self, entry_rule: pd.Series, exit_rule: pd.Series, direction: int, position_size=None,
                 nbar_stop: int = 0) -> pd.DataFrame:
        """
        Calculates entry/exit rule based exposure, uses DataManager's primary quotes to calculate exposure
        :param entry_rule: strategy entry rule
        :param exit_rule: strategy exit rule
        :param direction: direction of the trade (1 - long, -1 - short)
        :param position_size: position size (integer/float/ or pandas.Series) (default: 1.0)
        :param nbar_stop: N-bar stop exit (default: no bar stop)
        :return: pandas DataFrame with 'exposure' column
        """
        # Use fast Cythonized method to calculate exposure
        price_series = self.dm.quotes()['c']

        if len(price_series) != len(entry_rule) or not np.all(price_series.index == entry_rule.index):
            raise StrategyError("Entry rule index doesn't match primary price series index")

        if len(price_series) != len(exit_rule) or not np.all(price_series.index == exit_rule.index):
            raise StrategyError("Exit rule index doesn't match primary price series index")

        if direction not in [1, -1]:
            raise StrategyError("'direction' must be 1 or -1")

        if nbar_stop < 0:
            raise StrategyError("N-bar stop must be >= 0")

        if position_size is not None:
            if isinstance(position_size, (float, int, np.float, np.int)):
                if position_size == 0:
                    raise StrategyError("'position_size' is permanently zero")
            else:
                if isinstance(position_size, pd.Series):
                    if len(price_series) != len(position_size) or not np.all(price_series.index == position_size.index):
                        raise StrategyError("Position size index doesn't match primary price series index")
                else:
                    raise StrategyError("Position size must be pandas.Series type")


        exposure_series = exposure(price_series.values,
                                   entry_rule.values,
                                   exit_rule.values,
                                   direction,
                                   size_exposure=position_size,
                                   nbar_stop=nbar_stop)

        return pd.DataFrame({'exposure': exposure_series}, index=price_series.index)


    #
    #  Strategy calculation
    #
    def calculate(self, *args: list) -> pd.DataFrame:
        """
        Calculate strategy logics
        :param args: optional strategy params (like MA periods, direction, etc)
        :return: Pandas.DataFrame aligned to primary quotes indexes and *'exposure'* column required, other columns
        also permitted to apply additional position management logic at the position initiation stage
        """
        raise NotImplementedError("You must implement 'calculate' method in child strategy class")

    #
    #  Strategy optimization
    #
    def score(self, exposure_df: pd.DataFrame) -> float:
        """
        Optimization scoring method, produces a float number metric of strategy member performance, uses 'calculate'
        results (i.e. exposure_df) to calculate score number based on primary quotes 
        :param exposure_df: 'calculate' method exposure Pandas.DataFrame
        :return: float number
        """
        if self.wfo_scoring_type == 'netprofit':
            return score_netprofit(self.dm.quotes()['c'].values,
                                   exposure_df['exposure'].values,
                                   costs=self.wfo_costs_per_contract
                                   )
        elif self.wfo_scoring_type == 'modsharpe':
            return score_modsharpe(self.dm.quotes()['c'].values,
                                   exposure_df['exposure'].values,
                                   costs=self.wfo_costs_per_contract
                                   )
        else:
            raise StrategyError(f"Unsupported 'wfo_scoring_type' = {self.wfo_scoring_type}")

    def pick(self, calculate_args_list: list) -> list:
        """
        Selection method from the list of strategy members' params in 'calculate_args_list'
        :param calculate_args_list: list of optimization arguments of 'calculate' method
        :return: List of the best performing 'calculate' args (i.e. swarm members)
        """
        # TODO: make more sophisticated best members picks
        return calculate_args_list[:self.wfo_members_count]


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

                # TODO: check if this code flow is available
                # raise NotImplementedError('Not expected code flow')

    def process_stats(self):
        """
        Calculate alpha strategy statistics
        :return: stats dictionary
        """
        equity_df = self.position.get_pnl_series()

        if len(equity_df) == 0:
            return {
                'series': pd.DataFrame(columns=['equity', 'costs', 'exposure'])
            }
        equity_df.rename(columns={'equity_execution': 'equity'}, inplace=True)

        stats_series = equity_df

        #
        # Save exposure values
        #
        assert len(equity_df) == len(
            self.exposure_series), "Position equity index doesn't match to exposure_series index. Possible position calculation issues!"
        assert np.all(
            equity_df.index == self.exposure_series.index), "Position equity index doesn't match to exposure_series index. Possible position calculation issues!"

        if 'exposure' not in self.exposure_series.columns:
            log.warn(
                "'exposure' column doesn't exist in strategy.exposure_series, probably custom exposure dataframe or "
                "strategy.exposure() was not called inside strategy.calculate() method")
            stats_series.loc[:, 'exposure'] = float('nan')
        else:
            stats_series.loc[:, 'exposure'] = self.exposure_series['exposure']

        return {
            'series': stats_series[['equity', 'costs', 'exposure']]
        }



    def run(self):
        """
        Run strategy instance and walk-forward optimization
        :return: 
        """
        log.info(f'Starting strategy {self}. Date now: {datetime.now()}')
        total_time_begin = time.time()

        # Initialize quotes
        self.setup()

        try:
            quotes_index = self.dm.quotes().index
        except QuoteNotFoundError:
            raise StrategyError("You should call 'self.dm.series_primary_set(...)' in strategy setup() "
                                "method to initialize quotes data")

        log.debug(f'Quotes range: {quotes_index[0].date()} - {quotes_index[-1].date()}')

        # Calculate WFO matrix for the historical data
        wfo_matrix = self._make_wfo_matrix()

        timings_opimize = []
        timings_position = []

        for wfo_period in wfo_matrix:
            wfo_action = self.get_next_wfo_action(self.wfo_last_period, wfo_period, quotes_index)

            if wfo_action == WFO_ACTION_SKIP:
                continue
            if wfo_action == WFO_ACTION_BREAK:
                break

            if wfo_action == WFO_ACTION_OPTIMIZE:
                log.debug(f"Optimizing IIS: {wfo_period['iis_start'].date()} - {wfo_period['iis_end'].date()}")
                time_optimize_begin = time.time()

                # Set IIS range
                self.dm.quotes_range_set(wfo_period['iis_start'], wfo_period['iis_end'])

                # Do optimization and picking
                optimizer = self.wfo_optimizer_class(self, self.wfo_opt_params, **self.wfo_optimizer_class_kwargs)
                self.wfo_selected_alphas = optimizer.optimize()

                # Set WFO last period
                self.wfo_last_period = wfo_period

                timings_opimize.append(time.time() - time_optimize_begin)

            log.debug(f"Processing OOS: {wfo_period['oos_start'].date()} - {wfo_period['oos_end'].date()}")
            time_process_position_begin = time.time()
            # Reset quotes range to OOS
            self.dm.quotes_range_set(wfo_period['iis_start'], wfo_period['oos_end'])

            # Run predefined alphas params
            oos_exposure_df_list = []
            tz = None
            for alpha_params in self.wfo_selected_alphas:
                alpha_exposure_df = self.calculate(*alpha_params)
                oos_exposure_df_list.append(alpha_exposure_df)

            # Processing strategy position
            self.process_position(oos_exposure_df_list, wfo_period['oos_start'], wfo_period['oos_end'])

            # Reset quotes range
            self.dm.quotes_range_set()

            timings_position.append(time.time() - time_process_position_begin)

        avg_opt_time = 0.0
        if timings_opimize:
            avg_opt_time = sum(timings_opimize) / len(timings_opimize)

        avg_pos_time = 0.0
        if timings_position:
            avg_pos_time = sum(timings_position) / len(timings_position)

        #
        # Process stats
        #
        time_process_stats = time.time()
        self.stats = self.process_stats()


        log.info(
            f'Finished in {time.time() - total_time_begin:0.2f} seconds. '
            f'Avg. optimize time: {avg_opt_time:0.2f}sec '
            f'Avg. process time: {avg_pos_time:0.2f}sec '
            f'Avg. Stats time: {time.time() - time_process_stats:0.3f}')

    def calculate_position(self, date: datetime, exposure_record: pd.DataFrame) -> None:
        """
        Build position for current 'date' and 'exposure_record' for all alpha members
        :param date: date of the analysis
        :param exposure_record: slice of 'exposure_df' at 'date' for all members (pd.DataFrame)
        :return: nothing, processes position in place
        """
        raise NotImplementedError("You must implement 'calculate_position' method in child strategy class")

    @staticmethod
    def _check_exposure_df_list_integrity(exposure_df_list):

        # Check exposure df list index integrity
        for i, exp_df in enumerate(exposure_df_list):
            if not isinstance(exp_df, pd.DataFrame):
                raise ArgumentError("'exposure_df_list' members must be pandas.DataFrame, "
                                    "check strategy.calculate() method's return values")

            if i == 0:
                continue
            prev_exp_df = exposure_df_list[i - 1]

            # Check lengths equality
            if len(exp_df) != len(prev_exp_df):
                raise ArgumentError("'exposure_df_list' DataFrames' lengths are not equal")

            # Check datetime index equality
            if not np.all(exp_df.index == prev_exp_df.index):
                raise ArgumentError("'exposure_df_list' DataFrames' indexes values are not equal")

            # Check column names equality
            if not set(exp_df.columns) == set(prev_exp_df.columns):
                raise ArgumentError("'exposure_df_list' DataFrames' column names doesn't match each other")

    def _exposure_update(self, dt, exposure_df):
        if self.exposure_series is None:
            self.exposure_series = pd.DataFrame()

        if exposure_df is None:
            for col in self.exposure_series.columns:
                self.exposure_series.at[dt, col] = 0.0
        else:
            for k, v in exposure_df.sum().items():
                self.exposure_series.at[dt, k] = v


    def process_position(self, exposure_df_list: List[pd.DataFrame], oos_start: datetime, oos_end: datetime):
        """
        Processes positions based on picked swarm members 'exposure_df_list'
        :param exposure_df_list: list of results of 'calculate' method for each picked swarm member
        :param oos_start: start date of the OOS
        :param oos_end: end date of the OOS
        :return: nothing, processes position in place
        """
        #
        # Checking exposure_df_list for errors
        #
        self._check_exposure_df_list_integrity(exposure_df_list)

        if not exposure_df_list:
            log.warn(f"No swarm members selected for OOS period {oos_start.date()} - {oos_end.date()}")
            date_idx = self.dm.quotes().index
        else:
            date_idx = exposure_df_list[0].index

        # Get dates range between oos_start and oos_end
        # Get last position date
        try:
            position_last_date = self.position.last_date
        except PositionNotFoundError:
            position_last_date = QDATE_MIN

        # TODO: not decided is it's properly to use date(), because we have intraday systems to, NEED CHECK
        date_start = max(oos_start.date(), position_last_date.date())
        for dt in date_idx:
            if dt.date() <= date_start:
                # Skip all days before new data
                continue

            assert dt.date() < oos_end.date(), "unexpected behaviour"

            if not exposure_df_list:
                # In case then self.pick() returned nothing, i.e. turn all systems off
                # the position automatically will be closed

                # Close position to maintain flat equity line for a skipped period
                self.position.close(dt)

                # Set zero exposure
                self._exposure_update(dt, None)
            else:
                # Create exposure DataFrame slice at date 'dt' for all alpha members
                exposure_series = []
                for exp_df in exposure_df_list:
                    exposure_series.append(exp_df.loc[dt])

                exposure_df = pd.DataFrame(exposure_series)
                try:
                    # Run strategy position management
                    self.calculate_position(dt, exposure_df)

                except ChainNotFoundError as exc:
                    log.error(f"ChainNotFoundError: {dt}: {exc}")
                except QuoteNotFoundError as exc2:
                    log.error(f"QuoteNotFoundError: {dt}: {exc2}")

                # Update exposure stats
                if self.position.has_position(dt, check_pos_qty=False):
                    # Update exposure series only if position has record at date 'dt'
                    # This check will prevent position / exposure and equity index mismatch
                    self._exposure_update(dt, exposure_df)



    @classmethod
    def load(cls, datamanager, strategy_name):
        """
        Loads strategy instance from DB
        :param datamanager: DataManager instance
        :param strategy_name: name of the strategy
        :return: StrategyClass instance
        """
        return cls.deserialize(datamanager, datamanager.datafeed.data_engine.db_load_alpha(strategy_name))

    def save(self):
        """
        Saves strategy instance to the DB
        :return: 
        """
        self.dm.datafeed.data_engine.db_save_alpha(self.serialize())

    def serialize(self):
        """
        Save strategy data and position to compatible format for MongoDB serialization
        :return:
        """
        result_dict = {
            'name': self.strategy_name,
            'strategy_class': object_to_full_path(self),
            'wfo_params': self.wfo_params,
            'wfo_last_period': self.wfo_last_period,
            'wfo_selected_alphas': self.wfo_selected_alphas,
            'wfo_opt_params': self.wfo_opt_params,
            'wfo_scoring_type': self.wfo_scoring_type,
            'wfo_costs_per_contract': self.wfo_costs_per_contract,
            'wfo_members_count': self.wfo_members_count,
            'wfo_optimizer_class_kwargs': self.wfo_optimizer_class_kwargs,
            'wfo_optimizer_class': object_to_full_path(self.wfo_optimizer_class),
            'position': self.position.serialize(),
            'exposure_series': object_save_compress(self.exposure_series),
            'stats': object_save_compress(self.stats),
            'context': self.context,
        }
        return result_dict

    @classmethod
    def deserialize(cls, datamanager, serialized_strategy_record):
        """
        Deserialize strategy data, position and context from MongoDB serialized format
        :param datamanager: DataManager instance
        :param serialized_strategy_record: MongoDB dict like object
        :return: new Strategy cls instance
        """
        strategy_class = cls
        if strategy_class == StrategyBase:
            # The case when we try to load alpha dynamically using StrategyBase class
            # Getting strategy class from full-qualified class string
            strategy_class = object_from_path(serialized_strategy_record['strategy_class'])
        else:
            if object_to_full_path(cls) != serialized_strategy_record['strategy_class']:
                raise ArgumentError(f"Strategy class {object_to_full_path(cls)} doesn't match strategy class in the "
                                    f"serialized strategy record {serialized_strategy_record['strategy_class']}, try "
                                    f"to check strategy class or call StrategyBase.deserialize() to load dynamically")

        serialized_strategy_record['position'] = Position.deserialize(serialized_strategy_record['position'],
                                                                      datamanager)
        serialized_strategy_record['exposure_series'] = object_load_decompress(
            serialized_strategy_record['exposure_series'])
        serialized_strategy_record['stats'] = object_load_decompress(serialized_strategy_record['stats'])
        serialized_strategy_record['wfo_optimizer_class'] = object_from_path(
            serialized_strategy_record['wfo_optimizer_class'])

        return strategy_class(datamanager, **serialized_strategy_record)
