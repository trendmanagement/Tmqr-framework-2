class TMQRError(Exception):
    """
    Generic TMQR framework error
    """
    pass


class ArgumentError(TMQRError):
    """
    Raised when some argument is wrong
    """
    pass


class SettingsError(TMQRError):
    """
    Raised when settings contains wrong values
    """
    pass


class NotFoundError(TMQRError):
    """
    Raised then something is not found
    """
    pass



class ContractInfoNotFound(NotFoundError):
    pass


class InstrumentInfoNotFound(NotFoundError):
    pass


class ContractInfoNotApplicable(TMQRError):
    pass


class ContractInfoIntegrityError(TMQRError):
    pass


class DataEngineNotFoundError(NotFoundError):
    pass


class DataSourceNotFoundError(NotFoundError):
    """
    Raised when datasource type is not found
    """
    pass


class IntradayQuotesNotFoundError(NotFoundError):
    """
    Raised when quotes not found in intraday source
    """
    pass
