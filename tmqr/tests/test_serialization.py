import unittest

from tmqr.errors import *
from tmqr.serialization import object_from_path, object_to_full_path
from tmqrstrategy.optimizers import OptimizerBase
from tmqrstrategy.strategy_base import *


class ModuleClass:
    pass


class SerializationTestCase(unittest.TestCase):
    def test_object_to_path(self):
        dm = DataManager()
        opt = OptimizerBase

        self.assertEqual('tmqrfeed.manager.DataManager', object_to_full_path(dm))
        self.assertEqual('tmqrstrategy.optimizers.OptimizerBase', object_to_full_path(opt))
        self.assertEqual('tmqr.serialization.object_to_full_path', object_to_full_path(object_to_full_path))
        self.assertEqual('builtins.float', object_to_full_path(float))
        self.assertEqual('tmqr.tests.test_serialization.ModuleClass', object_to_full_path(ModuleClass))
        self.assertEqual('tmqr.tests.test_serialization.SerializationTestCase', object_to_full_path(self))

        # Serialization of classes from __main__ is not allowed
        ModuleClass.__module__ = '__main__'
        self.assertRaises(ArgumentError, object_to_full_path, ModuleClass)

    def test_object_from_path(self):
        self.assertEqual(DataManager, object_from_path('tmqrfeed.manager.DataManager'))
        self.assertEqual(OptimizerBase, object_from_path('tmqrstrategy.optimizers.OptimizerBase'))
        self.assertEqual(object_to_full_path, object_from_path('tmqr.serialization.object_to_full_path'))
        self.assertEqual(float, object_from_path('builtins.float'))
        self.assertEqual(ModuleClass, object_from_path('tmqr.tests.test_serialization.ModuleClass'))

        # Error handling
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed.manager.DataManager1')
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed.manager1.DataManager')
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed1.manager.DataManager')

    def test_object_load_decompress(self):
        pass

    def test_object_save_compress(self):
        pass
