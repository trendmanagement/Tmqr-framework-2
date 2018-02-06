import unittest
from tmqrscripts.signal_campaign_complete_push_to_realtime import CampaignUpdateCheckPushToRealtime

class Test_SignalCampaignComplete(unittest.TestCase):
    def setUp(self):
        print('In setUp()')
        self.cucpr = CampaignUpdateCheckPushToRealtime()


    def tearDown(self):
        print('In tearDown()')
        del self.cucpr

    def test_campaign_check(self):
        self.cucpr.run_query_to_test_campaign_components(True)