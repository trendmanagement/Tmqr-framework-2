from backtester.strategy import StrategyBase
from scipy import signal


class Strategy_DSP_BandPass(StrategyBase):
    def calc_entryexit_rules(self, filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index):
        px_ser = self.data.exo

        b, a = signal.butter(filt_order, [filt_start_f, filt_stop_f], btype='bandpass')

        filt = px_ser.copy()
        filt.values[:] = signal.lfilter(b, a, filt)

        if rule_index == 0:
            entry_rule = filt.shift(1) > filt
            exit_rule = filt.shift(1) < filt

            return entry_rule, exit_rule

        elif rule_index == 1:
            entry_rule = filt.shift(1) < filt
            exit_rule = filt.shift(1) > filt

            return entry_rule, exit_rule

        elif rule_index == 2:
            filt_ma = filt.expanding().mean()
            filt_std = filt.expanding().std()

            entry_rule = filt > (filt_ma + filt_std * filt_sigma)
            exit_rule = filt < 0

            return entry_rule, exit_rule

        elif rule_index == 3:
            filt_ma = filt.expanding().mean()
            filt_std = filt.expanding().std()

            entry_rule = filt < (filt_ma - filt_std * filt_sigma)
            exit_rule = filt > 0

            return entry_rule, exit_rule

    def calculate(self, params=None, save_info=False):
        #
        #
        #  Params is a tripple like (50, 10, 15), where:
        #   50 - slow MA period
        #   10 - fast MA period
        #   15 - median period
        #
        #  On every iteration of swarming algorithm, parameter set will be different.
        #  For more information look inside: /notebooks/tmp/Swarming engine research.ipynb
        #

        if params is None:
            # Return default parameters
            (direction, filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index) = self.default_opts()
        else:
            # Unpacking optimization params
            #  in order in self.opts definition
            (direction, filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index) = params

        entry_rule, exit_rule = self.calc_entryexit_rules(filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index)

        # Swarm_member_name must be *unique* for every swarm member
        # We use params values for uniqueness
        swarm_member_name = self.get_member_name(params)

        #
        # Calculation info
        #
        calc_info = None

        return swarm_member_name, entry_rule, exit_rule, calc_info
