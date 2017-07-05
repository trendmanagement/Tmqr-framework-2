.. _trading-custom-alphas:

========================
Custom alphas management
========================

.. toctree::
    :maxdepth: 2

Custom alphas files location and content
========================================
1. Custom alphas directory located at ``/var/data/tmqrengine/scripts/alphas``
2. Each subdirectory in this folder represents EXO name where custom alphas located. These subdirectories are python packages (i.e. each of them includes empty file ``__init__.py``)
3. Custom alpha files which is located in subdirectories have name started from ``alpha_`` prefix and have ``.py`` file extension
4. Each custom alpha file contains 3 constants inside: ``STRATEGY_NAME``, ``STRATEGY_SUFFIX``, ``STRATEGY_CONTEXT``


How custom alphas engine works
==============================
1. There are 2 scripts responsible for custom alpha management (both are located in ``scripts`` directory):
    * ``alpha_online_custom.py`` - this script is responsible for online trading and signal generation
    * ``alpha_rebalancer.py`` - this script is responsible for weekend rebalancing of the swarms
2. The script reads ``alphas`` directory sub-folders and compare the name of that sub-directory with EXO name
3. If the EXO name is matched, the script dynamically loads custom alpha Python code and run it. So literally these scripts are not configs, they are pure python modules.
4. Depending of type of the script the main *runner* script generates online signal or dumps information about current alphas state to the MongoDB.


How to add custom alpha using GUI
=================================
.. note:: This will be general way of custom alpha deployment, manual instructions below could be used for debugging or if something going wrong. GUI is based on ``flexx`` project this is in early alpha state, it's working but sill not ideal.

Launching GUI in notebook
-------------------------
1. Add 2 empty cells to the end of the notebook
2. Initialize the notebook GUI engine (you should wait after cell execution 3-5 secs for connection)::

    from flexx import app, ui, event
    app.init_notebook()

3. Launch deployment GUI::

    # Set the strategy suffix
    STRATEGY_SUFFIX = '-test'

    from backtester.apps.alpha_deployment import AlphaDeployer
    AlphaDeployer(strategy_context=STRATEGY_CONTEXT, strategy_suffix=STRATEGY_SUFFIX, flex=1)

Deployment process
------------------
1. Set the ``STRATEGY_SUFFIX`` variable to add unique suffix to custom alpha
2. Execute cell with AlphaDeployer() (you should re-execute it each time when you change ``STRATEGY_SUFFIX``)
3. Press the button
4. Run on the server ``cd /var/data/tmqrengine/scripts/`` and then ``python3.5 ./install.py``, this script will clear the logs and deploy new settings for online trading. Also ``supervisor service`` will be restarted.
5. Make sure that new custom alpha script is present in ``supervisorctl status`` command output, otherwise try to restart it manually one more time ``service supervisor restart``

What is happening
-----------------
1. Checks for file name duplicates
2. Checks for alpha name duplicates
3. Checks ``STRATEGY_CONTEXT`` syntax
4. Run ``alpha_rebalancer_single.py`` to make new custom alpha available in campaign notebook

Problems with flexx
-------------------
Unfortunately flexx is in early alpha state, the main problem with notebook initialization after it been closed. If you
faced with such kind of issues, you need to exec 'Kernel' -> 'Restart' and to rerun  the cells with ``STRATEGY_CONTEXT``
and flexx and Alpha deployment GUI. You don't need to rerun entire notebook to deploy the alpha.

How to add new custom alpha for **existing** EXO
================================================
.. note:: Alphas scripts can be uploaded using common git procedure described in :ref:`server-code-deployment`, all changes could be made on local machine
1. Switch to required EXO subdirectory for example: ``scripts/alphas/zw_callspread``

    .. note:: Subdirectory must exactly reflect EXO or SmartEXO name, if ``EXO_NAME = 'SmartEXO_Ichi_DeltaTargeting_Dec3_Bear_Bear_Spread'`` then the subdirectory name should be '<AssetSymbol>_smartEXO_ichi_deltatargeting_dec3_bear_bear_spread'

2. Create new python file using next naming pattern: ``alpha_<strategy_class>_<long-short>_<suffix>.py``
    For example: ``alpha_ichimoku_short_bearish.py``, if file exist you can add some suffix to it.

    .. warning:: File name must start from ``alpha_`` and have ``.py`` extension and be in **lower** case.
3. Add contents to file according alpha strategy settings in prototype notebook, and set the module constants:
    ``STRATEGY_NAME`` - it's good idea to use pre-built strategy name from strategy class, for example ``STRATEGY_NAME = StrategyIchimokuCloud.name``

    ``STRATEGY_SUFFIX`` - must be unique globally, if you have alphas with same names, results of one of them will be lost (overwritten)

    ``STRATEGY_CONTEXT`` - this dictionary could be copy/pasted from Jupyter notebook prototype

    Example code::

        from backtester.costs import CostsManagerEXOFixed
        from backtester.strategy import OptParam, OptParamArray
        from backtester.swarms.rankingclasses import *
        from backtester.swarms.rebalancing import SwarmRebalance
        from strategies.strategy_ichimokucloud import StrategyIchimokuCloud

        STRATEGY_NAME = StrategyIchimokuCloud.name

        STRATEGY_SUFFIX = 'bearish-'

        STRATEGY_CONTEXT = {
            'strategy': {
                'class': StrategyIchimokuCloud,
                'exo_name': 'ZW_CallSpread',        # <---- Select and paste EXO name from cell above
                'opt_params': [
                    # OptParam(name, default_value, min_value, max_value, step)
                    OptParamArray('Direction', [-1]),
                    OptParam('conversion_line_period', 9, 5, 5, 5),
                    OptParam('base_line_period', 26, 26, 26, 13),
                    OptParam('leading_spans_lookahead_period', 26, 13, 13, 1),
                    OptParam('leading_span_b_period', 52, 52, 52, 10),
                    # OptParamArray('RulesIndex', np.arange(17)),
                    OptParamArray('RulesIndex', [4, 5, 7]),
                    # OptParamArray('RulesIndex', [14,15,16]),
                    OptParam('MedianPeriod', 5, 5, 40, 10)
                ],
            },
            'swarm': {
                'members_count': 2,
                'ranking_class': RankerBestWithCorrel(window_size=-1, correl_threshold=0.5),
                'rebalance_time_function': SwarmRebalance.every_friday,
            },
            'costs': {
                'manager': CostsManagerEXOFixed,
                'context': {
                    'costs_options': 3.0,
                    'costs_futures': 3.0,
                }
            }
        }


File contents should reflect full ``STRATEGY_CONTEXT`` dictionary from prototype Jupyter notebook, also it must have all
``import`` statements to make the module functional.

How to add new custom alphas for **new** EXO
============================================
1. ``cd`` to custom alphas directory and create new folder with new EXO name (in lower case!), for example: ``mkdir zw_smart_exo_ichi_new``

.. note:: Subdirectory must exactly reflect EXO or SmartEXO name, if ``EXO_NAME = 'SmartEXO_Ichi_DeltaTargeting_Dec3_Bear_Bear_Spread'`` then the subdirectory name should be '<AssetSymbol>_smartEXO_ichi_deltatargeting_dec3_bear_bear_spread'

2. Change to new directory ``cd zw_smart_exo_ichi_new``
3. Create new empty __init__.py
4. Add new alpha module as described in section above, do sanity checks.
5. **DEPRECATED** Edit ``scripts/settings.py`` locate ``ALPHAS_CUSTOM`` constant, and add new EXO name to the list. Install script is automatically processing all folders in ``scripts/alphas`` directory without requirements of additional settings.
6. Run the ``python3.5 scripts/settings.py`` for syntax errors checks (empty output means - **no** syntax errors)
7. Commit and push changes to GitHub and log in to the server
8. Run deployment process as described at :ref:`server-code-deployment` but without **service supervisor restart** step
9. Run on the server ``cd /var/data/tmqrengine/scripts/`` and then ``python3.5 ./install.py``, this script will clear the logs and deploy new settings for online trading. Also ``supervisor service`` will be restarted.
10. Make sure that new custom alpha script is present in ``supervisorctl status`` command output, otherwise try to restart it manually one more time ``service supervisor restart``


Custom alpha files sanity checks
================================
.. note:: Alphas scripts can be uploaded using common git procedure described in :ref:`server-code-deployment`, all changes could be made on local machine

1. Check the python file syntax. `cd` to custom alphas directory for specified EXO, and run the command ``python3.5 ./<custom_alpha_script>.py``. If the command ended without any messages then the syntax is correct.
2. Check if the specified strategy class is correct, look for import statement like ``from strategies.strategy_ichimokucloud import StrategyIchimokuCloud``
3. Check if the EXO name value in STRATEGY_CONTEXT -> 'strategy' -> 'exo_name' reflects requirements and is equal to subdirectory name.
4. Check if alpha composite name EXO_Name+StrategyName+Long/short+STRATEGY_SUFFIX is unique, otherwise append alternative value to the suffix like ``STRATEGY_SUFFIX = 'alt2-bullish-'```


Indices and tables
==================

* :ref:`index-page`
