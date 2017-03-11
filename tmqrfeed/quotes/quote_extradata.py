from tmqrfeed.quotes.quote_base import QuoteBase


class QuoteExtra(QuoteBase):
    """
    Special extra data building class. ExtraData is a special collection of data which is stored in MongoDB
    and this data could include:
    * EXO pre-calculated prices
    * Algorithmically pre-calculated values based on OHLC of the raw data analysis
    * Non-price data for asset (fundamental data values, news calendar, COT, IV indexes etc.)

    What this class should do:
    1. Fetch raw extradata from dataengine
    2. Align raw values to primary data source
    3. Do sanity checks of the extradata
    4. Create Extradata class instance
    """
    pass
