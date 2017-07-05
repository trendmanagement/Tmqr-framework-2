.. _trading-exo-management:

==============
EXO management
==============

.. toctree::
    :maxdepth: 2


How EXO scripts work
====================
.. automodule:: scripts.exo_builder


How to add new product or EXO
=============================
All setting for EXO generation and product list are stored in ``scripts/settings.py``

Main options:

* ``INSTRUMENTS_LIST`` - list of products used for calculations (this list used by ``install.py`` script for ``supervisor`` configuration files generation)

* ``EXO_LIST`` - list of EXO algorithms and names

To add new product
------------------
1. Type in new ``exchangesymbol`` name to the ``INSTRUMENTS_LIST``
2. Run the ``python3.5 scripts/settings_exo.py`` for syntax errors checks (empty output means - **no** syntax errors)
3. Check or add new rollover regime for new asset if it is necessary in ``exobuilder/algorithms/rollover_helper.py`` (default regime is rollover each month)
4. Commit and push changes to GitHub and log in to the server
5. Run deployment process as described at :ref:`server-code-deployment` but without **service supervisor restart** step
6. Run EXO batch backfill ``python3.5 ./exo_batch_update.py`` (**important** you need to wait until backfill process is finished)
7. Run on the server ``cd /var/data/tmqrengine/scripts/`` and then ``python3.5 ./install.py``, this script will clear the logs and deploy new settings for online trading. Also ``supervisor service`` will be restarted.
8. Make sure that new product is present in ``supervisorctl status`` command output, otherwise try to restart it manually one more time ``service supervisor restart``
9. Plot EXO graphs in https://10.0.1.2:8888/notebooks/tools/EXO%20viewer.ipynb notebook to make sure that all EXOs have enough historical data and backfilled properly.

.. note:: Name of the product **must** reflect ``exchangesymbol`` field of ``instruments`` MongoDB collection

.. note:: If you've forgot to run ``python3.5 ./exo_batch_update.py``, and EXO series already filled by online data, first of all you need manually remove EXO series from DB and then restart ``exo_batch_update.py`` script.

To add new EXO
--------------
1. Add new tested EXO python file to ``exobuilder/algorithms``
2. Edit ``scripts/settings_exo.py`` file
    * Add new import statement to the header of the file
        For example::

            from exobuilder.algorithms.exo_continous_fut import EXOContinuousFut
            from exobuilder.algorithms.new_exo_module import NewEXOClassName

    * Add new EXO item to ``EXO_LIST``
        For example::

            EXO_LIST = [
            {
                'name': 'CollarBW',
                'class': EXOBrokenwingCollar,
            },
            ....
            {
                'name': 'NewExoName',
                'class': NewEXOClassName,   # As in import statement above
            }
            ]

3. Run the ``python3.5 scripts/settings_exo.py`` for syntax errors checks (empty output means - **no** syntax errors)
4. Commit and push changes to GitHub and log in to the server
5. Run deployment process as described at :ref:`server-code-deployment`, don't forget to run ``service supervisor restart`` to refresh changes
6. Run EXO batch backfill ``python3.5 ./exo_batch_update.py``

To add new SmartEXO
-------------------
.. note:: This section related to new class based SmartEXOs implemented in 2016-12-08

1. Make sure that class based SmartEXO is working properly from the notebook
2. Delete all temporary generated history running ``smart_utils.clear_smartexo()`` in SmartEXO notebook from *Deployment* section
3. Copy 'import' statements from the header of the notebook and class source code from cell
4. Add copied text to new EXO python file to ``exobuilder/algorithms``
5. Rename SmartEXO class from SmartEXOGeneric to another name, it should be unique
6. Define ``ASSET_LIST`` value to set required list of products for this SmartEXO or set it to ``None`` if you need to run this SmartEXO on all assets.
7. Run steps 2 and 3 from EXO deployment manual above
8. Commit and push changes to GitHub and log in to the server
9. Run EXO batch backfill ``python3.5 ./exo_batch_update.py``. Refer to :ref:`server-code-deployment` to get information how to execute long-running tasks.
10. Run ``python3.5 ./install.py`` to add new SmartEXO to online setup
11. Run ``python3.5 ./alpha_rebalancer.py`` if you need to get generic alphas for this EXO (for example *Buy and hold EXO*) ASAP, or wait until scheduled launch of the alpha_rebalancer occurred.

.. warning:: ``python3.5 ./exo_batch_update.py`` is an long running task it's better to run it overnight or over weekend using

How to migrate from old version of SmartEXO notebook
++++++++++++++++++++++++++++++++++++++++++++++++++++
1. SmartEXOGeneric class defined in new version of the notebook has similar methods new_position_bullish_zone() / new_position_bearish_zone() / new_position_neutral_zone / manage_opened_position()
2. Copy&Paste the ``trans_list = []`` contents from the old notebook to particular methods inside the class. New method should only contains trans_list and return statements.
3. Change Ichimoku regime algorithm parameters if required in the __init__ method of the class
    For example::

         def __init__(self, symbol, direction, date, datasource, **kwargs):
            super().__init__(symbol, direction, date, datasource,
                             #
                             # Change following values if you need to customize Ichimoku settings
                             #
                             conversion_line_period = 9,
                             base_line_period=26,
                             leading_spans_lookahead_period=52,
                             leading_span_b_period=52
                            )

4. Run new class based notebook to compare results
5. Follow SmartEXO deployment instructions if necessary


Indices and tables
==================

* :ref:`index-page`
