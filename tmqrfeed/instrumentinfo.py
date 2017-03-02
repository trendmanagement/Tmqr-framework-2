import pytz

from tmqr.errors import InstrumentInfoNotFound
from tmqrfeed.assetsession import AssetSession


class InstrumentInfo:
    """
    InstrumentInfo class implements interface to raw asset information stored in the DB
    """

    def __init__(self, asset_info_dict):
        if asset_info_dict is None or len(asset_info_dict) == 0:
            raise InstrumentInfoNotFound("Empty instrument info")

        self._info_dict = asset_info_dict
        self.instrument = "UNKNOWN"
        try:
            self.instrument = self._info_dict['instrument']
            self.market = self._info_dict['market']
            self.ticksize = self._info_dict['ticksize']
            self.tickvalue = self._info_dict['tickvalue']
            self.timezone = pytz.timezone(self._info_dict['timezone'])
            session = self._info_dict['trading_session']
        except KeyError as exc:
            raise InstrumentInfoNotFound("Can't find record in instrument info for {0}. {1}".format(self.instrument,
                                                                                                    str(exc)))

        self.session = AssetSession(session, self.timezone)

    def get(self, item, default_value=None):
        """
        Get extra value of asset info
        :param item: asset info item
        :param default_value: default value if 'item' is not found
        :return:
        """
        return self._info_dict.get(item, default_value)

    def __getattr__(self, item):
        """
        Get extra value of asset info by name (like asset_info.some_item)
        :param item:
        :return:
        """
        if item not in self._info_dict:
            raise InstrumentInfoNotFound(
                "Value '{0}' is not found in AssetInfo record for {1}".format(item, self.instrument))
        return self._info_dict[item]
