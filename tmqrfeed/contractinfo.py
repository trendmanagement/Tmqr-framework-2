from tmqr.errors import ContractInfoIntegrityError, ContractInfoNotApplicable, ContractInfoNotFound

class ContractInfo:
    """
    Contract information container class
    """

    def __init__(self, contract_info_dic):
        if contract_info_dic is None or len(contract_info_dic) == 0:
            raise ValueError("Contract info dictionary is empty")

        self._info_dic = contract_info_dic

    @property
    def ticker(self):
        """
        Full qualified ticker of the contract
        :return:
        """
        return self._info_dic['tckr']

    @property
    def ctype(self):
        """
        Contract type
        :return:
        """
        return self._info_dic['type']

    @property
    def instrument(self):
        """
        Instrument of the contract
        :return:
        """
        return self._info_dic['instr']

    @property
    def underlying(self):
        """
        Underlying asset of the contracts
        :return:
        """
        return self._info_dic['underlying']

    @property
    def market(self):
        """
        Contract's market
        :return:
        """
        return self._info_dic['mkt']

    @property
    def exp_date(self):
        """
        Date of the expiration
        :return:
        """
        return self._info_dic['exp']

    @property
    def strike(self):
        """
        Strike of the option contract
        :return:
        """
        if self.ctype == "C" or self.ctype == 'P':
            return self._info_dic['strike']
        else:
            raise ContractInfoNotApplicable("'strike' field of contract info only applicable to options contracts")

    @property
    def opt_type(self):
        """
        Type of option contract
        :return:
        """
        if self.ctype == "C" or self.ctype == 'P':
            return self._info_dic['opttype']
        else:
            raise ContractInfoNotApplicable("'opttype' field of contract info only applicable to options contracts")

    def extra(self, item, default=ContractInfoNotFound):
        """
        Extra data accessor
        :param item: keyname of extra data item
        :param default: default value to return if not found, default=ContractInfoNotFound raises exception
        :return:
        """
        if 'extra_data' in self._info_dic:
            if item not in self._info_dic['extra_data']:
                if default == ContractInfoNotFound:
                    raise ContractInfoNotFound("Extra data for '{0}' doesn't contain {1}".format(self.ticker, item))
                else:
                    return default
            else:
                return self._info_dic['extra_data'][item]
        else:
            if default == ContractInfoNotFound:
                raise ContractInfoNotFound("Extra data for '{0}' doesn't exist.".format(self.ticker))
            else:
                return default

    def check_integrity(self, contract):
        """
        Check the integrity of the contract and contract info.
        :param contract:
        :return:
        """
        if contract.ticker != self.ticker:
            raise ContractInfoIntegrityError(str(contract) + " Ticker full qualified names mismatch")

        if self.ctype != contract.ctype:
            raise ContractInfoIntegrityError(str(contract) + " Contract type mismatch")

        if contract.instrument != self.instrument:
            raise ContractInfoIntegrityError(str(contract) + " Instrument names mismatch")

        if self.ctype == 'F':
            if contract.exp_date != self.exp_date:
                raise ContractInfoIntegrityError(str(contract) + " Expiration dates mismatch")
        elif self.ctype in ["C", "P"]:
            if contract.exp_date != self.exp_date:
                raise ContractInfoIntegrityError(str(contract) + " Expiration dates mismatch")
            if contract.strike != self.strike:
                raise ContractInfoIntegrityError(str(contract) + " Strike mismatch")

        return True
