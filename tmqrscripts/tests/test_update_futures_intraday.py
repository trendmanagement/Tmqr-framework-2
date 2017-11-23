import unittest
from datetime import datetime
from tmqrscripts.update_futures_intraday import UpdateFuturesIntraday

class Test_futures_update(unittest.TestCase):

    def setUp(self):
        pass

    def test_check_if_holiday(self):
        x = UpdateFuturesIntraday()
        check_date = datetime(2017,11,23)
        print(check_date)
        is_business_day = x.check_if_business_day(check_date)
        print(is_business_day)
        self.assertEqual(is_business_day,False)

if __name__ == '__main__':
    unittest.main()