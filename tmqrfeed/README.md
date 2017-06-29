# DataFeed TODO
The short list what to do to finish full datafeed functionality

1. AssetSession intraday mode - it's required to create special case 
of AssetSession settings to support intraday. 
 It should contain following settings:
    
       {            
            'dt': datetime(1900, 1, 1),  # Start date of AssetSession
            'decision': 1,               # Decision offset (minutes before
                                         # interval ends)
            
            'start': '00:32'             # Start time of trading session
            'end': '10:45',              # End time of trading session            
       },
    
    * `AssetSession.get()` method should correctly handle intraday session settings
    * `AssetSession.get()` method should produce valid intraday interval based on raw datetime
    * add custom DB record for intraday AssetSession, this allow us
      to use both EOD and intraday quotes.
  
2. Add support of intraday compression for QuoteContFut algorithm.

3. Positions are intraday ready, so the main part of work related to the DataFeed engine