from collections import OrderedDict
from tmqr.errors import ArgumentError, PositionNotFoundError, PositionQuoteNotFoundError
from tmqrfeed.contracts import ContractBase
import warnings
from tmqr.logs import log


class Position:
    """
    Universal position management class for all types of strategies
    """

    def __init__(self, datamanager, position_dict=None):
        """
        Init the Position instance
        :param datamanager: DataManager class instance
        :param position_dict: position dictionary
        """
        if position_dict:
            self._position = position_dict
        else:
            self._position = OrderedDict()
        self.dm = datamanager

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

    def serialize(self):
        """
        Serialize position data to compatible for MongoDB format
        :return: 
        """
        pass

    @staticmethod
    def deserialize(self):
        """
        Deserialize position data from MongoDB format
        :param self: 
        :return: 
        """
        pass

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

    def get_transactions(self, date):
        """
        Get position transactions at given date
        :param date: 
        :return: 
        """
        pass

    def get_pnl(self, date):
        """
        Get position PnL at given date
        :param date: 
        :return: 
        """
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

    def get_pnl_series(self):
        """
        Calculates position PnL series for all transactions, also additional execution info provided
        :return: pandas.DataFrame
        """
        pass

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
