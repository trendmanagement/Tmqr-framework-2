import unittest

from tmqrfeed.dataengines import DataEngineMongo


class DataEngineTestCase(unittest.TestCase):
    def test_get_asset_info_bad_instrument(self):
        dfeed = DataEngineMongo()
        self.assertRaises(ValueError, dfeed.get_asset_info, 'CL')
        self.assertRaises(ValueError, dfeed.get_asset_info, '')
        self.assertRaises(ValueError, dfeed.get_asset_info, 'CL.US.S')

    def test_get_asset_info_existing_instrument(self):
        deng = DataEngineMongo()
        ainfo = deng.get_asset_info("US.ES")
        self.assertEqual('US.ES', ainfo['instrument'])
        self.assertEqual(12.5, ainfo['tickvalue'])

    def test_get_asset_info_nonexisting_instrument(self):
        deng = DataEngineMongo()
        ainfo = deng.get_asset_info("US.NON_EXISTING_INSTRUMENT")
        self.assertEqual('US.NON_EXISTING_INSTRUMENT', ainfo['instrument'])
        self.assertEqual(1.0, ainfo['tickvalue'])

    def test_get_asset_info_non_existing_market(self):
        deng = DataEngineMongo()
        self.assertRaises(ValueError, deng.get_asset_info, "NONEXISTINGMARKET.ES")
