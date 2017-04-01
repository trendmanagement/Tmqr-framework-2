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
    Raised when something is not found
    """
    pass


class DBDataCorruptionError(TMQRError):
    """
    Raised when data in the DB has different type than expected
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


class QuoteEngineEmptyQuotes(NotFoundError):
    """
    Raised when quotes algo unable to create quote series
    """
    pass


class IntradayQuotesNotFoundError(NotFoundError):
    """
    Raised when quotes not found in intraday source
    """
    pass


class OptionsEODQuotesNotFoundError(NotFoundError):
    """
    Raised when quotes not found in EOD options source
    """
    pass

class ChainNotFoundError(NotFoundError):
    """
    Raised when futures or options chains data not found
    """
    pass


class DataManagerError(TMQRError):
    """
    Raised when generic DataManager error occurred
    """
    pass
