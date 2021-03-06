#Future highlights of new framework

- **DataFeed / DataManagement** – we need to get ability to analyze and build price series for every asset we want on the fly. It could be continuous futures, spreads, multilegged spreads, seasonal spreads, etc.
 
- **Data analysis** – during daily bar building we could do some sophisticated postprocessing. For example, if we will have 1-min bar in the DB we can build daily OHLC based on them, beside this we can make a renko graphs instead of OHLC, also calculate some metrics based on intraday price path behavior. For example, we can classify each day by price behavior in intraday for classes 'strong bull', 'medium bull', 'neutral', 'medium bear', 'strong bear', or by volatility in intraday. There is many options, most important all these metrics could be the input features of Machine Learning algorithms.

- **New optimization approach** – I've chased wild goose many time before, when I've developed trading system which looks good on the history, but after couple of months of trading this model performance degrading or even worse going to drawdown. I was thinking a lot how to overcome this obstacle and I think I have a clue. Fair backtester concept – the backtesting process that emulates simple approach, it's very correlated with Swarm backtesting/optimization, but also compatible with Machine learning modelling. And the most important, fair backtesting produces equity composed of chain of out-of-sample results (after rebalancing in terms of Swarms). This approach will help us avoid look forward issues, and most important hidden look-forward of Machine learning and similar.
 
- **New strategy design** – as I said before we tend to do extra work by building EXO and then alphas on it, but most important we are loosing much information when analyzing EXO produced graphs. SmartEXO is a good way, but have issues in calculation speed and lack of optimization. My idea to make a fusion of SmartEXO and Swarm concept, so we could analyze underlying asset and compose options positions on it, including optimization. 
   So we could separate backtesting process on 2 phases: 
    - Fast and quick – optimization using metrics of underlying data (could be continuous future or spread or some synthetic series), it will not be necessary to use PnL of underlying data also we could use for example IV series or some price behavior characteristics to estimate future performance of option position. But we can pick swarm members which behaves best using this metric.
    - Slow and precise position building – on this phase we could compose and manage position as we want using best alpha parameters (like picked swarm members in old Swarms)

    This approach gives us very flexible ability to optimize regime switching (or decision 	making) logic and position building logic separately and do this on the fly. Option position 	building should go much faster than in original SmartEXO because we only need to use 	options while we are in position, but not every day as in old case.
    Also good news that we can avoid some calculations errors in online trading, because the 	strategy will return positions list expressed in contracts.


## Examples of strategies
1. **Simple continuous futures strategy** – we can compose continuous future contract on the fly, then apply sophisticated intraday data postprocessing (to extract additional data of price behavior intraday), use some collected non-price data (for example for NG: storage amounts, temperature, rigs count, etc.), input this data to the Machine learning algorithm and execute future contract as is.
2. **Seasonal spread strategy** – we can build seasonal spread asset on the fly (for example butterfly on the futures), analyze it as composite or each leg separately and backtest it. Executing every contract in the spread as is, i.e. PnL calculations will be based on price changes of each contract, but not spread changes itself.
3. **Options volatility trading** – we can build IV graph of underlying, create model which predicts IV moves (or use VIX for ES), and execute option position and delta hedging using real options contracts (for example building straddles or ratio spread positions)
4. **Making decisions and trade different assets** – when we have 2 similar assets traded on different exchanges we can use first asset for decision making and second for execution. For example Russian ruble, we can use quotes on Russian market to make decisions and trade Ruble on the CME (it has lower liquidity and reversed FX quote)
5. **Hedging** – we can create custom hedge portfolios making decisions on underlying continuous futures, but opening different kinds of spreads or options positions.