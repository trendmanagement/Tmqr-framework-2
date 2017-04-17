class Costs:
    """
    Generic fixed costs calculation class
    """

    def __init__(self, per_contract=0.0, per_option=0.0):
        self.per_contract = per_contract
        self.per_option = per_option

    def calc_costs(self, asset, qty):
        """
        Calculate costs based on asset and qty
        :param asset: ContractBase instance
        :param qty: transaction qty
        :return: costs USD value
        """
        if asset.ctype in ('P', 'C'):
            # Make sure that costs are always negative
            return -abs(self.per_option) * abs(qty)
        else:
            return -abs(self.per_contract) * abs(qty)