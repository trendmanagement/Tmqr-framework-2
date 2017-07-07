from tmqrstrategy import StrategyAlpha
import tmqrstrategy.analysis as a
from scipy import signal


class Strategy_DSP_LPBP_Combination(StrategyAlpha):
    def calc_entryexit_rules(self, lp_order, lp_freq, bp_order, bp_startfreq, bp_stopfreq, bp_multiplier, rule_index):
        px_ser = self.dm.quotes()['c']

        b, a = signal.butter(lp_order, lp_freq, btype='lowpass')

        lpfilt = px_ser.copy()
        lpfilt.values[:] = signal.lfilter(b, a, lpfilt)

        b, a = signal.butter(bp_order, [bp_startfreq, bp_stopfreq], btype='bandpass')

        bpfilt = px_ser.copy()
        bpfilt.values[:] = signal.lfilter(b, a, bpfilt)

        lpbp = lpfilt - bpfilt * bp_multiplier

        if rule_index == 0:
            entry_rule = a.CrossDown(lpbp, px_ser)
            exit_rule = a.CrossUp(lpbp, px_ser)

            return entry_rule, exit_rule

        elif rule_index == 1:
            entry_rule = a.CrossUp(lpbp, px_ser)
            exit_rule = a.CrossDown(lpbp, px_ser)

            return entry_rule, exit_rule

        elif rule_index == 2:
            entry_rule = lpbp > lpfilt
            exit_rule = lpbp < lpfilt

            return entry_rule, exit_rule

        elif rule_index == 3:
            entry_rule = lpbp < lpfilt
            exit_rule = lpbp > lpfilt

            return entry_rule, exit_rule

    def calculate(self, *args):
        (direction, lp_order, lp_freq, bp_order, bp_startfreq, bp_stopfreq, bp_multiplier, rule_index) = args

        entry_rule, exit_rule = self.calc_entryexit_rules(lp_order, lp_freq, bp_order, bp_startfreq,
                                                          bp_stopfreq, bp_multiplier, rule_index)
        return self.exposure(entry_rule, exit_rule, direction)
