from collections import OrderedDict
from tmqr.errors import ArgumentError, PositionNotFoundError, PositionQuoteNotFoundError, PositionReadOnlyError
from tmqrfeed.contracts import ContractBase
from tmqr.logs import log
import pandas as pd
from datetime import timedelta
import pickle
import io


class Position:
    """
    Universal position management class for all types of strategies
    """

    def __init__(self, datamanager, position_dict=None, **kwargs):
        """
        Init the Position instance
        :param datamanager: DataManager class instance
        :param position_dict: position dictionary
        :param kwargs: position init keyword args
        """
        if position_dict:
            self._position = position_dict
        else:
            self._position = OrderedDict()
        self.dm = datamanager
        self.kwargs = kwargs

    #
    # Private methods
    #
    #

    def _prev_day_key(self, date=None):
        """
        Gets previous day key which is less than 'date'
        :param date: if date is None returns date of the last key
        :return: previous date key datetime
        """
        # This method intended to be used for 'keep_previous_position' method
        # And it's expected that this loop will iterate only 1-2 steps
        for k in reversed(self._position.keys()):
            if date is None:
                return k
            if k < date:
                return k

        if date is None:
            raise PositionNotFoundError(f"Position doesn't have any records")
        else:
            raise PositionNotFoundError(f"Position at the day less than {date} is not found")

    def _check_position_validity(self, net_position_dict):
        """
        Checks the input data validity to prevent position data corruption
        :param net_position_dict: dict of {asset: (decision_px, exec_px, qty), ... }
        :return: nothing
        :raises: ArgumentError
        """
        if not isinstance(net_position_dict, dict):
            raise ArgumentError(f"'net_position_dict' must be dictionary type")

        for asset, pos_value in net_position_dict.items():
            if not isinstance(asset, ContractBase):
                raise ArgumentError(f"'net_position_dict' keys must be ContractBase derived class instance, "
                                    f"but got type {type(asset)}")
            if not isinstance(pos_value, tuple):
                raise ArgumentError(f"'net_position_dict' values must be tuples, but got type {type(pos_value)}")
            if len(pos_value) != 3:
                raise ArgumentError(f"'net_position_dict' values must be tuples of (decision_px, exec_px, qty),"
                                    f" but got different length {pos_value}")

    #
    # Position save/load
    #
    #

    def serialize(self):
        """
        Serialize position data to compatible for MongoDB format
        :return: 
        """
        result = OrderedDict()
        for dt, asset_dict in self._position.items():
            asset_dict_converted = result.setdefault(dt, {})

            asset_keys = tuple(asset_dict.keys())
            for k in asset_keys:
                asset_dict_converted[k.ticker] = asset_dict[k]

        res_dict = {
            'data': pickle.dumps(result),
            'kwargs': self.kwargs,
        }

        return res_dict

    @classmethod
    def deserialize(cls, pos_data, datamanager=None, as_readonly=False):
        """
        Deserialize position data from MongoDB format
        :param pos_data: 
        :param datamanager: DataManager instance for position's assets
        :param as_readonly: return PositionReadOnlyView instead of the Position instance
        :return: Position class or PositionReadOnlyView class instance
        """
        deserialized_kwargs = pos_data.get('kwargs', {})
        pos_dict = pickle.loads(pos_data['data'])

        result = OrderedDict()
        for dt, asset_dict in pos_dict.items():
            asset_dict_converted = result.setdefault(dt, {})

            asset_keys = tuple(asset_dict.keys())
            for k in asset_keys:
                asset_dict_converted[ContractBase.deserialize(k, datamanager)] = asset_dict[k]

        if as_readonly:
            return PositionReadOnlyView(datamanager, result, **deserialized_kwargs)
        else:
            return Position(datamanager, position_dict=result, **deserialized_kwargs)



    #
    # Position management
    #
    #
    def almost_expired_ratio(self, date, rollover_days_before_fut=None, rollover_days_before_opt=None):
        """
        Return the fraction of contracts in the position 'rollover_days_before' near expiration
        :param date: current date
        :param rollover_days_before_fut: Days before futures rollover (default: uses InstrumentInfo values) 
        :param rollover_days_before_opt: Days before options rollover (default: uses InstrumentInfo values)
        :return: 0.0 - if no contracts of the position are near expiration, 1.0 - if all contracts about to be expired,
                 value in range 0.0 < almost_expired_ratio < 1.0 if only part of the position near expiration
        """
        rollover_count = 0.0
        count = 0.0

        pos = self._position.get(date, None)
        if not pos:
            return 0.0

        for asset in pos.keys():
            count += 1.0

            if asset.ctype == 'F':
                if rollover_days_before_fut:
                    rollover_fut = rollover_days_before_fut
                else:
                    rollover_fut = asset.instrument_info.rollover_days_before

                if asset.to_expiration_days(date) <= rollover_fut:
                    rollover_count += 1.0

            elif asset.ctype == 'P' or asset.ctype == 'C':
                if rollover_days_before_opt:
                    rollover_opt = rollover_days_before_opt
                else:
                    rollover_opt = asset.instrument_info.rollover_days_before_options

                if asset.to_expiration_days(date) <= rollover_opt:
                    rollover_count += 1.0

        if count == 0:
            return 0.0
        else:
            return rollover_count / count


    def close(self, date):
        """
        Close all position at given date
        :param date: 
        :return: nothing, changes position in place
        """
        try:
            pos_dict = self._position[date]
            for asset, pos_rec in pos_dict.items():
                # Apply zero-qty to all position records, but keep the prices
                pos_dict[asset] = (pos_rec[0], pos_rec[1], 0.0)
        except KeyError:
            # Nothing to close at 'date', just skipping
            pass


    def set_net_position(self, date, net_position_dict):
        """
        Set net position at given date (overwrites old position if it exists). This method intended to be used
        by low-level Quote* algorithms to initiate positions, generic strategies should use add_net_position() method.
        
        This method allow to change position at the previous date, use with care this could ruin data validity.
        :param date: 
        :param net_position_dict: dict of {asset: (decision_px, exec_px, qty), ... }
        :return: nothing, changes position in place
        """
        # Do sanity checks
        self._check_position_validity(net_position_dict)

        # Overwrite the position
        self._position[date] = net_position_dict

    def keep_previous_position(self, date):
        """
        Keeps position at previous day 
        :param date: current date
        :return:  nothing, changes position in place
        """
        if self._position and date < self._prev_day_key(date=None):
            # check if 'date' >= last date of the position
            raise ArgumentError(f'Managing position at date less then last available date is not allowed')

        try:
            updated_position = {}
            prev_position = self.get_net_position(self._prev_day_key(date))
            for asset, pos_rec in prev_position.items():
                if pos_rec[2] == 0.0:
                    # Skipping closed position
                    continue

                # Get actual prices for position
                decision_price, exec_price = self.dm.price_get(asset, date)

                updated_position[asset] = (decision_price, exec_price, pos_rec[2])

            # Add updated position record at specified date
            self.add_net_position(date, updated_position, qty=1.0)
        except PositionNotFoundError as exc:
            log.warn(f'keep_previous_position: {str(exc)}')

    def add_net_position(self, date, net_position_dict, qty=1.0):
        """
        Add net position at given date. 
        This method adds to current position holdings, and calculates required transactions to maintain the new position.
        :param date: 
        :param net_position_dict:
        :param qty: qty times of the net_position, negative values allowed
        :return: nothing, changes position in place
        """

        if self._position and date < self._prev_day_key(date=None):
            # check if 'date' >= last date of the position
            raise ArgumentError(f'Managing position at date less then last available date is not allowed')

        # Do sanity checks
        self._check_position_validity(net_position_dict)

        pos_dict = self._position.setdefault(date, {})
        for asset, new_position in net_position_dict.items():
            # Searching existing positions first
            current_position = pos_dict.get(asset, None)
            if not current_position:
                pos_dict[asset] = (new_position[0], new_position[1], new_position[2] * qty)
            else:
                assert current_position[0] == new_position[0]
                assert current_position[1] == new_position[1]
                pos_dict[asset] = (
                    current_position[0], current_position[1], new_position[2] * qty + current_position[2])

    def add_transaction(self, date, asset, qty):
        """
        Add new transaction for the position at given date
        :param date: 
        :param asset: 
        :param qty:
        :return: nothing, changes position in place
        """
        if self._position and date < self._prev_day_key(date=None):
            # check if 'date' >= last date of the position
            raise ArgumentError(f'Managing position at date less then last available date is not allowed')

        pos_dict = self._position.setdefault(date, {})

        decision_price, exec_price = self.dm.price_get(asset, date)

        # Searching existing positions first
        pos_record = pos_dict.get(asset, None)
        if not pos_record:
            pos_dict[asset] = (decision_price, exec_price, qty)
        else:
            assert pos_record[0] == decision_price
            assert pos_record[1] == exec_price
            pos_dict[asset] = (pos_record[0], pos_record[1], qty + pos_record[2])



    @staticmethod
    def merge(datamanager, positions_list):
        """
        Merges list of Positions to single Position class instance. Useful for campaign position building, alpha members position, etc.
        :param datamanager: DataManager instance
        :param positions_list: list of Position class instances to merge
        :return: 
        """

        def merge_pos_record(result_dict, new_dict):
            for asset, pos_value in new_dict.items():
                result_value = result_dict.get(asset, None)

                if not result_value:
                    # Asset is not found just add new value
                    result_dict[asset] = pos_value
                else:
                    # Checking the decision and execution prices equality
                    assert result_value[0] == pos_value[0]
                    assert result_value[1] == pos_value[1]

                    # Summing the qty of position
                    result_dict[asset] = (result_value[0], result_value[1], result_value[2] + pos_value[2])

        result_pos_dict = OrderedDict()

        # Get list of unique dates for all positions
        merged_dates_set = set()
        for pos in positions_list:
            merged_dates_set.update(pos._position.keys())

        # Iterate dates in a sorted order
        for date in sorted(merged_dates_set):
            result_record = result_pos_dict.setdefault(date, {})

            # Iterate over all positions
            for pos in positions_list:
                try:
                    pos_record = pos._position[date]
                    # Merge positions records
                    merge_pos_record(result_record, pos_record)
                except KeyError:
                    continue

        return Position(datamanager, position_dict=result_pos_dict)

    #
    # Position information
    #

    @property
    def last_date(self):
        return self._prev_day_key(date=None)

    def get_asset_price(self, date, asset):
        """
        Get asset prices from position holdings
        :param date: required date
        :param asset: ContractBase class instance        
        :return: tuple (decision_price, exec_price)
        """
        assets_dict = self._position.get(date, None)
        if assets_dict:
            pos_tuple = assets_dict.get(asset, None)
            if pos_tuple:
                return pos_tuple[0], pos_tuple[1]  # decision_px, exec_px

        raise PositionQuoteNotFoundError(f'Quote is not found in the position for {asset} at {date}')

    def has_position(self, date):
        return date in self._position and sum([abs(x[2]) for x in self._position[date].values()]) > 0

    def get_net_position(self, date):
        """
        Get net position at given date
        :param date: date of position slice
        :return: 
        """
        try:
            return self._position[date]
        except KeyError:
            raise PositionNotFoundError(f'No positions records found at {date}')

    def _calc_transactions(self, date, current_pos, prev_pos):
        result = {}

        assert current_pos is not None, 'current_pos must be initialized'

        if prev_pos is None:
            intersected_assets = set(current_pos)
        else:
            intersected_assets = set(current_pos) | set(prev_pos)

        for asset in intersected_assets:
            prev_values = prev_pos.get(asset, None) if prev_pos is not None else None
            curr_values = current_pos.get(asset, None)

            if prev_values is None:
                costs_value = self.dm.costs_get(asset, curr_values[2])
                result[asset] = (curr_values[0], curr_values[1], curr_values[2], costs_value, costs_value, costs_value)
            elif curr_values is None:
                # Skip old closed positions
                if prev_values[2] != 0:
                    decision_price, exec_price = self.dm.price_get(asset, date)
                    costs_value = self.dm.costs_get(asset, -prev_values[2])

                    pnl_decision = asset.dollar_pnl(prev_values[0], decision_price, prev_values[2])
                    pnl_execution = asset.dollar_pnl(prev_values[1], exec_price, prev_values[2])

                    result[asset] = (decision_price, exec_price, -prev_values[2],
                                     pnl_decision + costs_value, pnl_execution + costs_value, costs_value)
            else:
                # Calculating transactions for existing position
                trans_qty = curr_values[2] - prev_values[2]
                costs_value = self.dm.costs_get(asset, trans_qty)
                pnl_decision = asset.dollar_pnl(prev_values[0], curr_values[0], prev_values[2])
                pnl_execution = asset.dollar_pnl(prev_values[1], curr_values[1], prev_values[2])

                result[asset] = (curr_values[0], curr_values[1], trans_qty,
                                 pnl_decision + costs_value, pnl_execution + costs_value, costs_value)

        return result

    def _transactions_stats(self, trans_dict):
        pnl_change_decision = 0.0
        pnl_change_execution = 0.0
        ncontracts_executed = 0.0
        noptions_executed = 0.0
        costs = 0.0

        for asset, trans in trans_dict.items():
            pnl_change_decision += trans[3]
            pnl_change_execution += trans[4]

            if asset.ctype in ('P', 'C'):
                noptions_executed += abs(trans[2])
            else:
                ncontracts_executed += abs(trans[2])

            costs += trans[5]


        return {
            'pnl_change_decision': pnl_change_decision,
            'pnl_change_execution': pnl_change_execution,
            'ncontracts_executed': ncontracts_executed,
            'noptions_executed': noptions_executed,
            'costs': costs
        }

    def get_pnl_series(self):
        """
        Calculates position PnL series for all transactions, also additional execution info provided
        :return: pandas.DataFrame
        """
        pnl_result = []
        prev_pos = None

        for dt, pos_list in self._position.items():
            transactions = self._calc_transactions(dt, pos_list, prev_pos)
            stats = self._transactions_stats(transactions)
            res = {'dt': dt}
            res.update(stats)

            pnl_result.append(res)
            prev_pos = pos_list

        df_result = pd.DataFrame(pnl_result).set_index('dt')
        df_result['equity_decision'] = df_result['pnl_change_decision'].cumsum()
        df_result['equity_execution'] = df_result['pnl_change_execution'].cumsum()

        return df_result

    def __repr__(self):
        pos = self.get_net_position(self.last_date)

        with io.StringIO() as txt_buf:
            txt_buf.write("{0:<40}{1:>10}{2:>10}{3:>10}\n".format('Asset', 'DecisionPx', 'ExecPx', 'Qty'))

            for asset, pos_rec in pos.items():
                txt_buf.write("{0:<40}{1:>10}{2:>10}{3:>10}\n".format(str(asset), pos_rec[0], pos_rec[1], pos_rec[2]))

            return txt_buf.getvalue()





class PositionReadOnlyView(Position):
    """
    Position read only view used to view precalculated Index position with decision_time_shift
    this class used as proxy to get position using original decision time of the instrument.
    Only get_net_position() method allowed, other methods will raise PositionReadOnlyError()
    """

    def __init__(self, datamanager, position_dict=None, **kwargs):
        super().__init__(datamanager, position_dict=position_dict, **kwargs)
        self.decision_time_shift = kwargs.get('decision_time_shift', 0)

        if self.decision_time_shift < 0:
            raise ArgumentError("'decision_time_shift' arg must be >= 0")

    def get_net_position(self, date):
        shifted_date = date - timedelta(minutes=self.decision_time_shift)
        return super().get_net_position(shifted_date)

    def get_asset_price(self, date, asset):
        raise PositionQuoteNotFoundError(f'Operation is not allowed for PositionReadOnlyView instance')

    def get_pnl_series(self):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def serialize(self):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def set_net_position(self, date, net_position_dict):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def add_transaction(self, date, asset, qty):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def add_net_position(self, date, net_position_dict, qty=1.0):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def close(self, date):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def keep_previous_position(self, date):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')

    def _prev_day_key(self, date=None):
        raise PositionReadOnlyError(f'Operation is not allowed for PositionReadOnlyView instance')
