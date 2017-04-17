from tmqr.errors import SettingsError
import pandas as pd
from tmqrfeed.manager import DataManager

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

    def setup(self):
        """
        Initiate index algorithm
        - Setting up quotes data
        - Setting up ML model
        etc...
        :return: nothing, class instance can populate internal values 
        """
        pass

    def process_data(self):
        """
        Process and build main data for index, Index instance must implement data updates explicitly 
        :return: nothing, changes self.data in place
        """
        pass

    def process_position(self, date, index_data):
        """
        Process and build main position of index
        :param date: decision making date
        :param index_data: self.data slice from beginning to 'date' (prevents future reference)
        :return: nothing, changes self.position in place
        """
        pass

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

        # Setting data up
        self.setup()

        try:
            # Try to set data and position
            self.set_data_and_position()
        except NotImplementedError:
            self.process_data()

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
        return self._index_name

    def serialize(self):
        """
        Save index data and position to compatible format for MongoDB serialization
        :return: 
        """
        pass

    @classmethod
    def deserialize(cls, datamanager, serialized_index_record):
        """
        Deserialize index data, position and context from MongoDB serialized format
        :param datamanager: DataManager instance
        :param serialized_index_record: MongoDB dict like object
        :return: new Index cls instance
        """
        pass

    @property
    def fields(self):
        """
        List of the index field names
        :return:
        """
        if self.data:
            return self.data.columns
        else:
            return []
