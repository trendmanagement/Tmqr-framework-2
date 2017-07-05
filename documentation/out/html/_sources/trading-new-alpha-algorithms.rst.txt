.. _trading-new-alpha-algorithms:

==============================
Deploying new alpha algorithms
==============================

.. toctree::
    :maxdepth: 2


How to deploy new alpha strategy algorithm
==========================================
1. Create new file inside ``strategies`` folder with name pattern ``strategy_<new_strategy_name>.py`` in lower case
2. Copy/paste required ``import`` statements for new strategy
3. Copy paste new alpha strategy class source code from Jupyter notebook to new created file inside ``strategies`` folder of the framework
4. Replace cell contents of new strategy file by import statement, for example: ``from strategies.strategy_macross_with_trail import StrategyMACrossTrail``

.. note:: Previous step is required to keep code base granularity after deployment, all changes after deployment should be made in file stored inside `strategies` folder to avoid code duplication and logic errors.

5. Now you will be able to run custom alpha deployment process as usual.


New alpha algorithm sanity checks
=================================
Future reference errors are most common and disappointing in system development, they could be result of coding mistakes or be hidden inside 3rd party packages like Pandas or Numpy.

To avoid these mistakes in the future, it's recommended to run automatic sanity checks while development process and **before new alpha deployment**.

AlphaSanityChecker automatic test
---------------------------------
To run automatic sanity check, just copy/paste following code snippet to the new cell after initialized swarm:

    AlphaSanityChecker snippet::

        from backtester.reports.alpha_sanity_checks import AlphaSanityChecker
        asc = AlphaSanityChecker(smgr)
        asc.run()

.. note:: AlphaSanityChecker should take place after swarm initialization and picking cell, like ``smgr = Swarm(STRATEGY_CONTEXT)``. ``smgr`` variable name in  AlphaSanityChecker(**smgr**) must be the same as ``smgr = Swarm(STRATEGY_CONTEXT)`` line.


How AlphaSanityChecker works
----------------------------
**Brief concept**

The main idea: all trading signals should take same place in history regardless of the window of calculation, and position of the signals shouldn't be changed when the new data arrives.

**Explanation of algorithm**

Let we have MACross alpha, and to check it for future reference we need to compare alpha signals:

1. Calculate alpha's signals on full history (this will be reference set of data)
2. Remove last year of the history and calculate alpha's signals on this sample.
3. If all signals on particular dates are equal to full history signals set, this is ok
4. Grow historical subset adding few days of history, compare signals to full historical data set
5. Do step #4 until we pass all of the historical data.
6. If we've faced with signals inequality this is the evidence of future reference issues.


