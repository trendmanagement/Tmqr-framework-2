from tmqrstrategy import StrategyAlpha
from scipy import signal


class Strategy_DSP_BandPass(StrategyAlpha):
    def calc_entryexit_rules(self, filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index):
        try:
            px_ser = self.dm.quotes()['c']
        except KeyError:
            # In case of index based quotes
            px_ser = self.dm.quotes()['equity_decision']

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

    def calculate(self, *args):
        (direction, filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index) = args

        entry_rule, exit_rule = self.calc_entryexit_rules(filt_order, filt_start_f, filt_stop_f, filt_sigma, rule_index)
        return self.exposure(entry_rule, exit_rule, direction)
