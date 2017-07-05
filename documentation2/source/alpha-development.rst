.. _alpha-development:

=============================
Alpha development description
=============================

:ref:`index-page`

.. toctree::
:maxdepth: 2

Alpha development guidelines
++++++++++++++++++++++++++++

Alpha code structure
~~~~~~~~~~~~~~~~~~~~

Each alpha should implement 3 main methods:

* ``setup()`` In this method you should implement quotes fetching and commissions settings, and any preparations for alpha
  calculations. `

* ``calculate()`` This is main alpha calculation method, this method must return alpha exposure dataframe, you can use
  self.exposure() helper method to produce exposure from entry/exit rules, or make it by your own.

* ``calculate_position()`` This method used for position construction based on exposure information returned from
  calculate(), here you can initiate (replicate) EXO index position or setup any custom position you want.


Alpha development
~~~~~~~~~~~~~~~~~
In the development phase you will be able to run alphas inside notebooks, fine-tune parameters, once alpha has been saved (i.e. deployed),
all parameters be stored in the DB. You should set the context only once at the first time alpha is deployed, then the
context will be loaded automatically on each alpha.load() call.

So you need set all of the parameters only once, if you would like to change params of deployed alpha you should rerun
this alpha omitting alpha.load() call.

.. note::  Due to stochastic (random) nature of some algorithms (like ML or GeneticOptimizer), there is no guarantee that
 you will get same results. It's very dangerous to rewrite and rerun alphas which are already deployed and in the
 production, better to create new version of alpha and gracefully disengage old version.


Setting alpha context
~~~~~~~~~~~~~~~~~~~~~
**General settings** ::

    'name': 'ES_NewFramework_MACross_Genetic', # Global alpha name, which be used for load/save to DB

    'context': { # Strategy specific settings
            # These settings only applycable for alphas derived from StrategyAlpha strategy
            # StrategyAlpha - is a classic EXO/SmartEXO based alpha
            'index_name': 'US.ES_ContFutEOD',      # Name of EXO index to trade
            'costs_per_option': 3.0,
            'costs_per_contract': 3.0,
        },

**Walk-forward optimization parameters** ::

    'wfo_params': {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',             # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,          # Number of months is OOS period
            'iis_periods': 12,         # Number of months in IIS rolling window and minimal test period len
                                       # (only applicable for 'window_type' == 'rolling')
        },


**Optimizer class parameters**

By design alpha can use any optimization algorithm, OptimizerClass permutates 'opt_params' and calculate alphas using these params, then it select best alphas by alpha.score() method results, and finally call alpha.pick() to
select best performing alphas for each WFO step.

'optimizer_class_kwargs' - OptimizerClass parameters, refer to source code to get more info.

Example::

        'wfo_optimizer_class': OptimizerGenetic,
        'wfo_optimizer_class_kwargs': {
            'nbest_count': 3,
            'nbest_fitness_method': 'max',
            'population_size': 50,
            'number_generations': 30,
            # 'rand_seed': 1, # Uncomment this parameter to make genetic results repeatable
        },


**Alpha's optimization parameters**

The order of 'opt_params' list should be the same as arguments order in alpha.calculate() method for particular alpha::

        'wfo_opt_params': [
            ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
            ('period_fast', [1, 3, 10, 15, 20, 30])
        ],


**WFO Scoring functions params**
- 'wfo_members_count' - number of picked alphas at each out-of-sample WFO step
- 'wfo_costs_per_contract' - costs in USD per contract used in WFO scoring functions (used only for alphas picking!, you should set costs explicitly for each alpha in the alpha.setup() method)
- 'wfo_scoring_type' - type of scoring function to rank alphas on in-sample period of WFO

Example::

    'wfo_members_count': 1,
    'wfo_costs_per_contract': 0.0,
    'wfo_scoring_type': 'netprofit'



**ALL SETTINGS IN ONE**::

    ALPHA_CONTEXT = {
        'name': 'ES_NewFramework_MACross_Genetic', # Global alpha name, which be used for load/save from DB
        'context': { # Strategy specific settings
            # These settings only applycable for alphas derived from StrategyAlpha strategy
            # StrategyAlpha - is a classic EXO/SmartEXO based alpha
            'index_name': 'US.ES_ContFutEOD',      # Name of EXO index to trade
            'costs_per_option': 3.0,
            'costs_per_contract': 3.0,
        },
        'wfo_params': {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 12,
            # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        },
        'wfo_optimizer_class': OptimizerBase,
        'wfo_optimizer_class_kwargs': {
            'nbest_count': 3,
            'nbest_fitness_method': 'max'
        },
        'wfo_opt_params': [
            ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
            ('period_fast', [1, 3, 10, 15, 20, 30])
        ],
        'wfo_members_count': 1,
        'wfo_costs_per_contract': 0.0,
        'wfo_scoring_type': 'netprofit'
    }


How to run alphas
~~~~~~~~~~~~~~~~~
While you are in development phase you can run alpha without saving (i.e. deployment). On each call of ``alpha.run()``,
framework engine launches the WFO optimization from the beginning of the history.

Example::

    # DataManager is a core class of the framework
    dm = DataManager()

    # Init alpha class and run
    # SomeCustomAlphasStrategyClass - has to be defined in the notebook or imported from other location
    # ALPHA_CONTEXT - is a settings dictionary
    alpha = SomeCustomAlphasStrategyClass(dm, **ALPHA_CONTEXT)

    # Run alpha's WFO optimization from scratch
    alpha.run()

`Refer to alpha sample notebook <https://10.0.1.2:8889/notebooks/alphas/Alpha%20HOWTO.ipynb>`_

How to deploy alphas
~~~~~~~~~~~~~~~~~~~~
Once alpha has been deployed all context information and settings are stored inside the DB. To run and update deployed
alpha you have to save alpha module to the one of the framework packages (for example ``tmqralphas``) and then create
notebook which uses alpha class from imported package.  Saving alphas classes defined in the notebook source code is not
allowed and raise error.

**Deployment process**

 1. Once you have developed new alpha class, fine tuned parameters you have to commit alpha source code to the Git and
    make reference to this class via 'import' statement. This step only applicable to brand new alpha classes, if you are changing
    just optimization params or settings in the ALPHA_CONTEXT, you have not to do this deployment step!

 2. You should run imported alpha and do ``alpha.save()`` step
    Example::

        # Load deployed alpha module
        from tmqrstrategy.tests.debug_alpha_prototype import AlphaGeneric

        # DataManager is a core class of the framework
        dm = DataManager()

        # Init alpha class and run
        alpha = AlphaGeneric(dm, **ALPHA_CONTEXT)

        # Run alpha's WFO optimization from scratch
        alpha.run()

        # Do saving (i.e. deployment)
        alpha.save()

 3. That's it, alpha has been deployment, now you have to run updates of alphas


How to run alphas in online
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You just need to call ``alpha.load()`` then ``alpha.run()`` then ``alpha.save()``. Deployed alphas are updated by calling
``alpha.run()``.

Example code::

    # Load deployed alpha module
    from tmqrstrategy.tests.debug_alpha_prototype import AlphaGeneric

    # Or load Strategy base
    from tmqrstrategy import StrategyBase

    # Init the environment
    dm2 = DataManager()

    # Do first run
    alpha_name = ALPHA_CONTEXT['name']

    # Call <AlphaClass>.load(datamanager, alpha_name)
    saved_alpha = AlphaGeneric.load(dm2, alpha_name)

    # BOTH METHODS ARE EQUAL!

    # Call StrategyBase.load(datamanager, alpha_name)
    # StrategyBase - can be more usefun in online scripts
    saved_alpha = StrategyBase.load(dm2, alpha_name)

    # The alpha.run() - only calculate recent data, and do another WFO step if required
    saved_alpha.run()

    # Save it again!
    saved_alpha.save()


    #
    # Finally you are ready to process alpha's positions for campaings!
    #
