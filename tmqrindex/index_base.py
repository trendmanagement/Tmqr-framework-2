from tmqr.errors import SettingsError, ArgumentError, IndexReadOnlyError
import pandas as pd
from tmqrfeed.manager import DataManager
from tmqrfeed.position import Position
from datetime import timedelta

import lz4
import pickle

INSTRUMENT_NA = "N/A"


class IndexBase:
    """
    Data and positional index base class
    """

    _instrument = INSTRUMENT_NA
    """Underlying instrument for index.
        Could be non existing instrument if the index is globally related, like economic calendar events."""

    _index_name = 'IndexBase'
    """Name of the index algorithm"""

    _description_short = "Short description of the index values or position"
    """"Short description of the index values or position"""

    _description_long = "Long description of the index, could include description of the data fields meanings"
    """Long description of the index, could include description of the data fields meanings"""

    def __init__(self, datamanager: DataManager, **kwargs):
        self.dm = datamanager
        """DataManager instance"""

        self.context = kwargs.get('context', {})
        """Index settings context"""

        self.instrument = kwargs.get('instrument', self._instrument)
        """Index settings context"""

        self.data = kwargs.get('data', pd.DataFrame())
        """Main index data container as pandas.DataFrame (can be None)"""

        self.position = kwargs.get('position', None)
        """Main index position as tmqrfeed.position.Position (can be None)"""

        self.as_readonly = kwargs.get('as_readonly', False)
        """Make index read-only, only properties and field access allowed, call of methods will raise exception"""

        self._index_name = kwargs.get('index_name', self._index_name)
        self._description_long = kwargs.get('description_long', self._description_long)
        self._description_short = kwargs.get('description_short', self._description_short)

        if self.as_readonly:
            # Adjust index data by decision_time_shift
            assert self.data is not None, 'Unexpected: self.data is None'
            assert isinstance(self.data.index,
                              pd.DatetimeIndex), 'Unexpected: self.data.index must be pandas.DatetimeIndex'

            # Shifting index data by decision_time_shift (only in read-only mode, to fit actual decision time)
            self.data.set_index(self.data.index + timedelta(minutes=self.decision_time_shift),
                                inplace=True)



    def setup(self):
        """
        Initiate index algorithm
        - Setting up quotes data
        - Setting up ML model
        etc...
        :return: nothing, class instance can populate internal values 
        """
        raise NotImplementedError("You must implement setup() method in child class.")


    def set_data_and_position(self):
        """
        Implementation of this method mutually exclude process_data() and process_position() run
                
        :return: 
        """
        raise NotImplementedError("set_data_and_position() is not implemented by Index "
                                  "probably it uses process_data() and process_position()")

    def run(self):
        """
        Run index calculation or update
        :return: 
        """
        if self.as_readonly:
            raise IndexReadOnlyError("Only property and attribute access allowed when index in read-only mode")

        # Setting data up
        self.setup()

        self.set_data_and_position()

    @property
    def decision_time_shift(self):
        """
        Gets the Index execution 'decision_time_shift' minutes before standard instrument's decision time
        :return: 
        """
        shift = self.context.get('decision_time_shift', 5)
        if shift <= 0:
            raise SettingsError(f"'decision_time_shift' for {self.index_name} must be > 0")
        return shift

    @property
    def index_name(self):
        if self.instrument != INSTRUMENT_NA and f"{self.instrument}_" not in self._index_name:
            return f"{self.instrument}_{self._index_name}"
        else:
            return self._index_name

    @property
    def fields(self):
        """
        List of the index field names
        :return:
        """
        try:
            return list(self.data.columns)
        except:
            return []



    def serialize(self):
        """
        Save index data and position to compatible format for MongoDB serialization
        :return: 
        """
        result_dict = {
            'name': self.index_name,
            'instrument': self.instrument,
            'description_short': self._description_short,
            'description_long': self._description_long,
            'fields': self.fields,
            'data': lz4.block.compress(pickle.dumps(self.data)),
            'position': self.position.serialize() if self.position is not None else None,
            'context': self.context,
        }
        return result_dict

    @classmethod
    def deserialize(cls, datamanager, serialized_index_record, as_readonly=False):
        """
        Deserialize index data, position and context from MongoDB serialized format
        :param datamanager: DataManager instance
        :param serialized_index_record: MongoDB dict like object
        :param as_readonly: Deserialize position as read only
        :return: new Index cls instance
        """
        if cls._index_name != IndexBase._index_name and cls._index_name not in serialized_index_record['name']:
            raise ArgumentError(
                f"Index name {cls._index_name} doesn't match to DB index name {serialized_index_record['name']}")

        pos = None
        if serialized_index_record['position'] is not None:
            pos = Position.deserialize(serialized_index_record['position'],
                                       datamanager=datamanager,
                                       as_readonly=as_readonly)

        index_instance = cls(datamanager,
                             instrument=serialized_index_record['instrument'],
                             context=serialized_index_record['context'],
                             data=pickle.loads(lz4.block.decompress(serialized_index_record['data'])),
                             position=pos,
                             index_name=serialized_index_record['name'],
                             description_long=serialized_index_record['description_long'],
                             description_short=serialized_index_record['description_short'],
                             as_readonly=as_readonly)
        return index_instance

    def save(self):
        """
        Saves index data to database
        :return: 
        """
        if self.as_readonly:
            raise IndexReadOnlyError("Only property and attribute access allowed when index in read-only mode")

        self.dm.datafeed.data_engine.db_save_index(self.serialize())

    @classmethod
    def load(cls, datamanager: DataManager, instrument=INSTRUMENT_NA):
        """
        Loads index instance from DB
        :param datamanager: datamanager class instance
        :param instrument: instrument name (default: INSTRUMENT_NA)
        :return: 
        """
        if instrument == INSTRUMENT_NA:
            idx_name = cls._index_name
        else:
            idx_name = f"{instrument}_{cls._index_name}"

        return cls.deserialize(datamanager, datamanager.datafeed.data_engine.db_load_index(idx_name))
