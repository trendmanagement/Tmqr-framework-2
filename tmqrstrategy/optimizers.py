class OptimizerBase:
    """
    Simple brute-force optimization algorithm class
    """

    def __init__(self, strategy, opt_params, **kwargs):
        """

        :param strategy: strategy class instance
        :param kwargs:
        """
        self.strategy = strategy
        self.opt_params = opt_params

    def optimize(self):
        # Create params universe

        # for param in params_universe:
        # run self.strategy.calculate(*param)
        # calc self.strategy.score()

        # select best members by MAX score

        # return self.strategy.pick(best_members)



        pass
