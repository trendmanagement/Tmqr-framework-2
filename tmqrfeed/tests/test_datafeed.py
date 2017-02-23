import unittest
from tmqrfeed.datafeed import DataFeed
from tmqrfeed._dataengines import DataEngineMongo
from datetime import datetime
from tmqrfeed.chains import FutureChain


class DataFeedTestCase(unittest.TestCase):
    def test_init_default(self):
        dfeed = DataFeed("Prepro", 'PostPro')
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.postprocessors, 'PostPro')
        self.assertEqual(dfeed.PreprocessorCls, 'Prepro')
        self.assertEqual(dfeed.data_engine_settings, {})
        self.assertEqual(dfeed.date_start, None)

    def test_init_kwargs(self):
        dfeed = DataFeed("Prepro",
                         'PostPro',
                         data_engine_settings={'test': 'ok'},
                         date_start=datetime(2011, 1, 1),
                         )
        self.assertEqual(True, isinstance(dfeed.data_engine, DataEngineMongo))
        self.assertEqual(dfeed.postprocessors, 'PostPro')
        self.assertEqual(dfeed.PreprocessorCls, 'Prepro')
        self.assertEqual(dfeed.data_engine_settings, {'test': 'ok'})
        self.assertEqual(dfeed.date_start, datetime(2011, 1, 1))

    def test_get_fut_chain(self):
        dfeed = DataFeed("Prepro",
                         'PostPro',
                         data_engine_settings={'test': 'ok'},
                         date_start=datetime(2011, 1, 1),
                         )
        chain = dfeed.get_fut_chain('US.CL')
        self.assertEqual(True, isinstance(chain, FutureChain))


