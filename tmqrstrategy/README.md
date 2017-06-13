# FUTURE TODO


To monitor and estimate alpha performance we need to get information about
alpha calculation process at IIS/OOS steps.

## How implement
Good point of statistics collection could be the `Optimizer` classes, 
they have access to all alphas optimization steps and scores. Good example of this
behaviour is an `OptimizerGeneric` logbook, based on DEAP library.

### What to collect
We have ability to collect following data from `Optimizer` classes:
* Alpha member parameters
* Score value
* Hall-of-fame (Best members table)

### What to calculate
 * Scores values distribution for IIS period of test could help us to estimate full swarm 
 behaviour. For example we could calculate % of alphas members with scores under water-line, 
 this metric could help us estimate quality of the alpha algorithm.

 * Another useful application of scores distribution could be **range analysis**. We
can estimate Highest-Lowest score range and analyse how top 10% quantile alpha members scores
 relate to this range. This could help to decide the quality of the full swarms members.
 
    `RangeRankFormula = (HighestScore - Quantile(Score, 90%)) / (HighestScore - LowestScore)`
    
    Note: this formula is negative score values aware 
 
 * Full swarms equity lines - this is a special case of the alpha development stages, the best
 option is to calculate full swarm equities using special `Optimizer` class, because the full
 swarm calculation only used on the early development stage.
 
 * EdgeTest™ - fully applicable at the OOS exposure based backtest, the EdgeTest could be very
  robust quality metric especially for OOS-based exposures. In the future EdgeTest could be used 
   as on/off switch for running alphas at the campaign management stage.
   
 * Quality IIS/OOS metric - compare best picked IIS alphas and the historical OOS (all OOS periods)
   from the beginning to the end of the current OOS period. This metric could show how effectively 
   the alpha matches the market. Is we have performance of OOS at 80% and above - this could be good,
   50-70% - moderate, less than 50% - could be the sign of unstable alpha and curve-fitting nature 
   of the alpha itself.
 

 
 

