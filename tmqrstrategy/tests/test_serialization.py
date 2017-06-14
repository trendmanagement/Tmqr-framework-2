import unittest
from tmqrfeed import DataManager, Position
from tmqrstrategy.strategy_base import *
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tmqr.errors import *
from tmqrstrategy.optimizers import OptimizerBase
from tmqrstrategy.serialization import object_from_path, object_to_full_path


class ModuleClass:
    pass


class SerializationTestCase(unittest.TestCase):
    def test_object_to_path(self):
        dm = DataManager()
        opt = OptimizerBase

        self.assertEqual('tmqrfeed.manager.DataManager', object_to_full_path(dm))
        self.assertEqual('tmqrstrategy.optimizers.OptimizerBase', object_to_full_path(opt))
        self.assertEqual('tmqrstrategy.serialization.object_to_full_path', object_to_full_path(object_to_full_path))
        self.assertEqual('builtins.float', object_to_full_path(float))
        self.assertEqual('tmqrstrategy.tests.test_serialization.ModuleClass', object_to_full_path(ModuleClass))
        self.assertEqual('tmqrstrategy.tests.test_serialization.SerializationTestCase', object_to_full_path(self))

        # Serialization of classes from __main__ is not allowed
        ModuleClass.__module__ = '__main__'
        self.assertRaises(ArgumentError, object_to_full_path, ModuleClass)

    def test_object_from_path(self):
        self.assertEqual(DataManager, object_from_path('tmqrfeed.manager.DataManager'))
        self.assertEqual(OptimizerBase, object_from_path('tmqrstrategy.optimizers.OptimizerBase'))
        self.assertEqual(object_to_full_path, object_from_path('tmqrstrategy.serialization.object_to_full_path'))
        self.assertEqual(float, object_from_path('builtins.float'))
        self.assertEqual(ModuleClass, object_from_path('tmqrstrategy.tests.test_serialization.ModuleClass'))

        # Error handling
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed.manager.DataManager1')
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed.manager1.DataManager')
        self.assertRaises(ArgumentError, object_from_path, 'tmqrfeed1.manager.DataManager')
