import pytz
from tmqrfeed.assetsession import AssetSession


class AssetInfo:
    """
    AssetInfo class implements interface to raw asset information stored in the DB
    """
    def __init__(self, asset_info_dict):
        self._info_dict = asset_info_dict
        self.instrument = self._info_dict['instrument']
        self.market = self._info_dict['market']
        self.ticksize = self._info_dict['ticksize']
        self.tickvalue = self._info_dict['tickvalue']
        self.timezone = pytz.timezone(self._info_dict['timezone'])
        self.session = AssetSession(self._info_dict['trading_session'], self.timezone)


    def __getattr__(self, item):
        if item not in self._info_dict:
            raise KeyError("Value '{0}' is not found in AssetInfo record for {1}".format(item, self.instrument))
        return self._info_dict[item]