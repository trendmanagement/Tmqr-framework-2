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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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


class QuoteNotFoundError(NotFoundError):
    """
    Raised when quote is not found
    """
    pass


class IntradayQuotesNotFoundError(QuoteNotFoundError):
    """
    Raised when quotes not found in intraday source
    """
    pass


class OptionsEODQuotesNotFoundError(QuoteNotFoundError):
    """
    Raised when quotes not found in EOD options source
    """
    pass

class ChainNotFoundError(NotFoundError):
    """
    Raised when futures or options chains data not found
    """

    def __init__(self, *args, **kwargs):
        self.option_offset_skipped = kwargs.get('option_offset_skipped', 0)


class DataManagerError(TMQRError):
    """
    Raised when generic DataManager error occurred
    """
    pass


class PositionNotFoundError(NotFoundError):
    """
    Raised when position is not found for particular date
    """
    pass


class PositionQuoteNotFoundError(QuoteNotFoundError):
    """
    Raised when cached quote is not found in position records
    """
    pass


class AssetExpiredError(TMQRError):
    """
    Raised when trying to get price for expired asset
    """
    pass

class PositionReadOnlyError(TMQRError):
    """
    Raised for PositionReadOnlyView not allowed position operations
    """

class CostsNotFoundError(NotFoundError):
    """
    Raised when costs class is not initiated for particular market
    """
    pass


class StrategyError(TMQRError):
    """
    Raised when strategy has errors
    """
    pass


class WalkForwardOptimizationError(StrategyError):
    """
    Raised when walk-forward optimization routine has error
    """
    pass
