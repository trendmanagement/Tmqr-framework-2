import itertools
from tmqr.errors import SettingsError, ArgumentError
import bisect
import math


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
