import itertools
from tmqr.errors import SettingsError, ArgumentError
import bisect
import math
import random
from deap import creator, base, tools, algorithms
import numpy as np


class OptimizerBase:
    """
    Simple brute-force optimization algorithm class
    """

    def __init__(self, strategy, opt_params, **kwargs):
        """
        Initialize optimizer base
        :param strategy: strategy instance
        :param opt_params: optimization params list
        :param kwargs:
            * nbest_count - number of best swarm members to store (None - store all)
            * nbest_fitness_method - how to select best members (default: 'max')
        """
        self.strategy = strategy
        self.opt_params = opt_params

        # Check strategy params settings
        self._check_params_integrity()

        self.nbest_count = kwargs.get('nbest_count', None)
        self.nbest_fitness_method = kwargs.get('nbest_fitness_method', 'max')

    def _check_params_integrity(self):
        if self.opt_params is None:
            raise SettingsError(f"Optimization params for {self.strategy} is None, check strategy settings")

        if not isinstance(self.opt_params, (list, tuple)):
            raise SettingsError(
                f"Optimization params for {self.strategy} must be list or tuple, check strategy settings")

        if len(self.opt_params) == 0:
            raise SettingsError(f"Optimization params for {self.strategy} have zero-length, check strategy settings")

        for p in self.opt_params:
            if not isinstance(p, (list, tuple)):
                raise SettingsError(
                    f"One of optimization params members for {self.strategy} must be list or tuple, check strategy settings")

            if len(p) != 2:
                raise SettingsError(
                    f"One of optimization params members for {self.strategy} must be a tuple of ('param_name', params_value_list)")

            if not isinstance(p[0], str):
                raise SettingsError(
                    f"One of optimization params members for {self.strategy}: parameter name must be a string")

            if not isinstance(p[1], (list, tuple)):
                raise SettingsError(
                    f"One of optimization params members for {self.strategy}: parameter '{p[0]}' values must be list or tuple")

    @staticmethod
    def _update_score_board(sb_scores, sb_params, new_score, new_params, n_max, fitness_direction):
        """
        Updates score board
        :param sb_scores: scoreboard list with scores
        :param sb_params: scoreboard list with alphas params
        :param new_score: candidate alpha score
        :param new_params: candidate alpha params
        :param n_max: if None - store all members
        :param fitness_direction: if 1 - maximizes the score, -1 - minimized the score
        :return: nothing, updates sb_scores and sc_params arguments in place
        """
        if n_max is not None and n_max <= 0:
            raise ArgumentError("n_max parameter must be > 0 or None")

        if fitness_direction not in (1, -1):
            raise ArgumentError("'fitness_direction' must be 1 or -1")

        if new_score is None or not math.isfinite(new_score):
            # Skip bad values of score function
            return

        idx = bisect.bisect_left(sb_scores, new_score)
        if n_max is None:
            sb_scores.insert(idx, new_score)
            sb_params.insert(idx, new_params)
        else:
            if len(sb_scores) < n_max or \
                    (fitness_direction == 1 and idx > 0) or \
                    (fitness_direction == -1 and idx < n_max):
                sb_scores.insert(idx, new_score)
                sb_params.insert(idx, new_params)

            if len(sb_scores) > n_max:
                if fitness_direction == 1:
                    del sb_scores[0]
                    del sb_params[0]
                else:
                    del sb_scores[-1]
                    del sb_params[-1]



    def optimize(self):
        """
        Pick best alphas params
        :return:
        """
        if self.nbest_fitness_method not in ('max', 'min'):
            raise SettingsError(f"Unknown 'nbest_fitness_method' kwarg value, "
                                f"expected ('max' or 'min') got {self.nbest_fitness_method}")
        # Create params universe
        params_universe = list(itertools.product(*[x[1] for x in self.opt_params]))

        scoreboard_scores = []
        scoreboard_params = []

        for param in params_universe:
            exposure_df = self.strategy.calculate(*param)
            score = self.strategy.score(exposure_df)

            # Insert score to scoreboard
            self._update_score_board(scoreboard_scores, scoreboard_params,
                                     score, param, n_max=self.nbest_count,
                                     fitness_direction=1 if self.nbest_fitness_method == 'max' else -1)

        return self.strategy.pick(scoreboard_params)


class OptimizerGenetic(OptimizerBase):
    """
    Simple genetic optimized based on DEAP genetic library
    """

    def __init__(self, strategy, opt_params, **kwargs):
        """
        Initialize optimizer base
        :param strategy: strategy instance
        :param opt_params: optimization params list
        :param kwargs:
            # Parent class kwargs
            * nbest_count - number of best swarm members to store (default: 30)
            * nbest_fitness_method - how to select best members (default: 'max')

            # Genetic specific params
            * rand_seed - set random seed to fix genetic algorithm repeatability (default: None - i.e. no fixation)
            * population_size - size of initial population of genetic (default: 200)
            * cross_prob - cross-over probability (default: 0.5)
            * mut_prob - mutation probability (default: 0.1)
            * number_generations - number of generations (default: 30)
        """
        super().__init__(strategy, opt_params, **kwargs)

        if self.nbest_count is None:
            # Overwrite default value
            self.nbest_count = 30

        # Fixing random sequences
        random.seed(kwargs.get('rand_seed', None))

        # Creating params universe
        self.params_universe = list(itertools.product(*[x[1] for x in self.opt_params]))

        # Genetic algo settings
        self.population_size = kwargs.get('population_size', 200)
        self.cross_prob = kwargs.get('cross_prob', 0.5)
        self.mut_prob = kwargs.get('mut_prob', 0.1)
        self.number_generations = kwargs.get('number_generations', 30)

    @staticmethod
    def mutate(individual, params_uni):
        """
        Mutation of alpha member. Randomly select opt params set from params universe and replace one randomly
        chosen parameter of the individual
        :param individual: individual alpha strategy params
        :param params_uni: parameters universe
        :return:
        """
        rnd_gene_idx = random.randint(0, len(individual) - 1)
        new_gene = random.choice(params_uni)
        individual[rnd_gene_idx] = new_gene[rnd_gene_idx]
        return individual,

    @staticmethod
    def mate(ind1, ind2):
        """
        Alpha strategies cross-over, change opt params of ind1 by randomly set of params of the ind2
        :param ind1: individual alpha strategy params 1
        :param ind2: individual alpha strategy params 2
        :return: crossed-over alpha strategy params
        """
        return tools.cxOnePoint(ind1, ind2)

    def evaluate(self, individual):
        """
        Alpha strategy score function evaluation
        :param individual:
        :return:
        """
        strategy_exposure = self.strategy.calculate(*individual)
        score = self.strategy.score(strategy_exposure)
        return (score,)

    def optimize(self):
        """
        Main optimization routine
        :return:
        """
        if self.nbest_fitness_method == 'max':
            fitness_direction = 1.0
        elif self.nbest_fitness_method == 'min':
            fitness_direction = -1.0
        else:
            raise SettingsError(f"Unknown 'nbest_fitness_method' expected 'max' or 'min',"
                                f" got {self.nbest_fitness_method}")

        # Init DEAP genetic library
        creator.create("Fitness", base.Fitness, weights=(fitness_direction,))
        creator.create("Individual", list, fitness=creator.Fitness)

        toolbox = base.Toolbox()
        toolbox.register("rules", random.choice, self.params_universe)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.rules)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        toolbox.register("evaluate", self.evaluate)
        toolbox.register("mate", self.mate)
        toolbox.register("mutate", self.mutate, params_uni=self.params_universe)
        toolbox.register("select", tools.selTournament, tournsize=5)

        pop = toolbox.population(n=self.population_size)

        stats = tools.Statistics(key=lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)

        self.hof = tools.HallOfFame(self.nbest_count)
        self.pop, self.logbook = algorithms.eaSimple(pop, toolbox,
                                                     cxpb=self.cross_prob, mutpb=self.mut_prob,
                                                     ngen=self.number_generations, verbose=False,
                                                     stats=stats, halloffame=self.hof)
        return list(self.hof)
