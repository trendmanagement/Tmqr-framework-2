import warnings
from tmqr.errors import QuoteNotFoundError
from tmqrstrategy.optimizers import OptimizerGenetic
import matplotlib.pyplot as plt
import pandas as pd


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
                                          number_generations=number_generations)
        self.best_params = []
        self.iis_range_end = None
        self.picked_stats = {}
        self.picked_equity = None

    def run(self):
        date_index = self.alpha.dm.quotes()
        self.iis_range_end = date_index.index[-int(len(date_index.index) * self.oos_period_ratio)]

        # Run strategy only at IIS period
        self.alpha.dm.quotes_range_set(range_end=self.iis_range_end)
        self.best_params = self.optimizer.optimize()

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
