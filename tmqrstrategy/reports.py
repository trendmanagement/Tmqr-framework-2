import warnings
from tmqr.errors import QuoteNotFoundError, ArgumentError
from tmqrstrategy.optimizers import OptimizerGenetic
import matplotlib.pyplot as plt
import pandas as pd
from tmqrstrategy.strategy_base import StrategyBase

from ipywidgets import interact
from bokeh.io import push_notebook, show, output_notebook
from bokeh.plotting import figure


class WFOViewer:
    def __init__(self, alpha: StrategyBase):
        if not alpha.wfo_store_stats:
            raise ArgumentError(f"You must set 'wfo_store_stats': True in ALPHA_CONTEXT")

        if not alpha.wfo_stats:
            raise ArgumentError(f"You must call alpha.run() before WFO viewer report")

        self.alpha = alpha

        # Setting up bokeh lib
        output_notebook()

        # Setting WFO periods list
        self.wfo_periods_list = list(self.alpha.wfo_stats.keys())

        # Graphs series
        self.graph_series_iis = []
        self.graph_series_oos = []
        self.graph_series_handle = None
        self.graph_series = None

    def run(self):
        stats = self.alpha.wfo_stats[self.wfo_periods_list[0]]

        p = figure(title=f"WFO Period: {self.wfo_periods_list[0]}", plot_height=300, plot_width=600,
                   x_axis_type="datetime")

        iis_eq = [v['equity'] for k, v in stats['iis_stats'].items()]
        oos_eq = [v['equity'] for k, v in stats['oos_stats'].items()]
        for i in range(self.alpha.wfo_optimizer_class_kwargs['nbest_count']):
            if i < len(iis_eq):
                eq = iis_eq[i]
                self.graph_series_iis.append(p.line(eq.index, eq, color="#2222aa", line_width=1))
            elif len(iis_eq) > 0:
                eq = pd.Series(float('nan'), index=iis_eq[0].index)
                self.graph_series_iis.append(p.line(eq.index, eq, color="#2222aa", line_width=1))

        for i in range(self.alpha.wfo_members_count):
            if i < len(oos_eq):
                eq = oos_eq[i]
                self.graph_series_oos.append(p.line(eq.index, eq, color="#000000", line_width=3))
            elif len(oos_eq) > 0:
                eq = pd.Series(float('nan'), index=oos_eq[0].index)
                self.graph_series_oos.append(p.line(eq.index, eq, color="#000000", line_width=3))

        self.graph_series_handle = show(p, notebook_handle=True)
        self.graph_series = p

    def update(self, wfo_index):
        stats = self.alpha.wfo_stats[self.wfo_periods_list[wfo_index]]

        iis_eq = [v['equity'] for k, v in stats['iis_stats'].items()]
        oos_eq = [v['equity'] for k, v in stats['oos_stats'].items()]

        for i in range(self.alpha.wfo_optimizer_class_kwargs['nbest_count']):
            if i < len(iis_eq):
                eq = iis_eq[i]
            elif len(iis_eq) > 0:
                eq = pd.Series(float('nan'), index=iis_eq[0].index)

            self.graph_series_iis[i].data_source.data = {
                'x': eq.index,
                'y': eq}

        for i in range(self.alpha.wfo_members_count):
            if i < len(oos_eq):
                eq = oos_eq[i]
            elif len(oos_eq) > 0:
                eq = pd.Series(float('nan'), index=oos_eq[0].index)

            self.graph_series_oos[i].data_source.data = {
                'x': eq.index,
                'y': eq}

        self.graph_series.title.text = f"WFO Period: {self.wfo_periods_list[wfo_index]}"
        push_notebook(handle=self.graph_series_handle)

    def interact(self):
        interact(self.update, wfo_index=(0, len(self.wfo_periods_list) - 1))


class GeneticSwarmViewer:
    def __init__(self, alpha, opt_params, oos_period_ratio, nbest_count, population_size=50, number_generations=50):
        self.alpha = alpha
        self.opt_params = opt_params
        self.oos_period_ratio = oos_period_ratio

        if self.alpha.exposure_series is None:
            warnings.warn(
                'Alpha has not been run, this is OK, but you will not be able to compare alpha original(picked) equity with average.')
            # Do setup to prevent initialization errors
            try:
                self.alpha.dm.quotes()
            except QuoteNotFoundError:
                self.alpha.setup()

        self.optimizer = OptimizerGenetic(alpha, opt_params, nbest_count=nbest_count,
                                          population_size=population_size,
                                          number_generations=number_generations,
                                          store_stats=True)
        self.best_params = []
        self.iis_range_end = None
        self.picked_stats = {}
        self.picked_equity = None

    def run(self):
        date_index = self.alpha.dm.quotes()
        self.iis_range_end = date_index.index[-int(len(date_index.index) * self.oos_period_ratio)]

        # Run strategy only at IIS period
        self.alpha.dm.quotes_range_set(range_end=self.iis_range_end)
        self.optimizer.optimize()
        self.best_params = self.optimizer.hof.items

        # Reset quotes range
        self.alpha.dm.quotes_range_set()

        # Create swarm stats
        stats_list = []
        equity_list = {}

        for param in self.best_params:
            exposure_df = self.alpha.calculate(*param)
            score_stats, equity = self.alpha.score_stats(exposure_df)

            score_stats['strategy'] = str(param)
            stats_list.append(score_stats)
            equity_list[score_stats['strategy']] = equity

        self.df_stats = pd.DataFrame(stats_list).set_index('strategy').sort_values('netprofit', ascending=False)
        self.df_full_swarm = pd.DataFrame(equity_list)
        self.df_avg_swarm = self.df_full_swarm.mean(axis=1)

        if self.alpha.exposure_series is not None:
            picked_exposure = self.alpha.exposure_series.reindex(self.alpha.dm.quotes().index, fill_value=0.0)
            self.picked_score_stats, self.picked_equity = self.alpha.score_stats(picked_exposure)
        else:
            self.picked_score_stats = {}
            self.picked_equity = pd.Series(0, index=self.df_full_swarm.index)

    def report(self):
        plt.figure();
        self.df_full_swarm.plot(legend=False);
        plt.axvline(self.iis_range_end);
        plt.title('Best swarm members picked by genetic')

        plt.figure();
        self.df_full_swarm.mean(axis=1).plot(label='Average swarm equity');
        self.picked_equity.plot(label='Picked equity');
        plt.axvline(self.iis_range_end);
        plt.legend(loc=2);
        plt.title('Real strategy equity can be diffent due to position management!!!');
        #
        # Calculate best opt params set ready for copy / paste
        #
        params_buffer = [set() for p in self.opt_params]

        for param in self.best_params:
            for i, p in enumerate(param):
                params_buffer[i].add(p)

        params_str = ''
        for i, param in enumerate(self.opt_params):
            params_str += f"            ('{param[0]}', {list(sorted(params_buffer[i]))}),\n"

        print('List of best params')
        print(params_str)
