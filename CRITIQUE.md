# Iron Condor Screener - Senior Quant Developer Code Review

**Reviewer**: Senior Quantitative Developer
**Date**: December 2025
**Overall Assessment**: **Good foundation, production-ready with notable gaps**

---

## Executive Summary

This is a well-structured options screening tool with clean code, good test coverage, and sensible architectural decisions. However, it lacks several critical components expected in a production quantitative trading system. The code demonstrates solid software engineering practices but needs significant enhancements in quantitative rigor, risk management, and data validation.

**Strengths:**
- Clean, type-hinted code with immutable dataclasses
- Excellent test coverage (~81%)
- Transparent scoring methodology
- Generator pattern for memory efficiency
- Good documentation

**Critical Gaps:**
- No real-time data validation or staleness checks
- Missing Greeks calculations (relies entirely on broker data)
- No portfolio-level risk management
- Insufficient statistical rigor for implied volatility analysis
- No backtesting framework
- Limited error handling for market edge cases

---

## Section 1: Data Quality & Validation

### Issues

**1.1 No Quote Staleness Detection**
- CSV loader has no timestamp validation
- No detection of stale or indicative quotes
- No market hours awareness (could be screening during closed hours)

**1.2 Bid-Ask Spread Validation Insufficient**
- Only checks percentage spread, not absolute width
- No detection of locked/crossed markets
- No validation against historical spread norms

**1.3 Missing Last Trade Validation**
- `last` price field is loaded but never validated
- No comparison between mid price and last trade
- Could miss mispriced options

**1.4 No Data Completeness Checks**
- Doesn't verify all expirations are present
- No check for missing strikes in chain
- Could miss obvious arbitrage opportunities

### Recommendations

```python
# Add to data/validators.py
class QuoteQuality:
    """Validate quote quality and freshness."""

    @staticmethod
    def is_quote_fresh(timestamp: datetime, max_age_seconds: int = 300) -> bool:
        """Check if quote is recent enough."""
        pass

    @staticmethod
    def is_market_open(timestamp: datetime, exchange: str = "NYSE") -> bool:
        """Verify quote is from market hours."""
        pass

    @staticmethod
    def detect_locked_market(bid: float, ask: float) -> bool:
        """Detect locked (bid == ask) or crossed (bid > ask) markets."""
        return bid >= ask

    @staticmethod
    def validate_last_price(last: float, bid: float, ask: float, tolerance: float = 0.5) -> bool:
        """Ensure last trade is within reasonable range of current market."""
        return abs(last - (bid + ask) / 2) <= tolerance
```

**Priority**: High
**Effort**: Medium
**Impact**: Prevents trading on stale/bad data

---

## Section 2: Greeks Calculation & Validation

### Issues

**2.1 Greeks Are Optional**
- Delta, gamma, theta, vega are `None | float`
- No fallback calculation using Black-Scholes
- Screening fails silently if broker doesn't provide Greeks

**2.2 No Greeks Validation**
- Delta values aren't validated against put/call type
- No range checks (delta should be -1 to 1)
- No consistency checks between Greeks

**2.3 No Greeks Projection**
- Uses snapshot Greeks only
- Doesn't project how delta/gamma change over time
- Can't estimate P&L paths

**2.4 Missing Implied Volatility Surface**
- Each option has single IV point
- No skew analysis (put skew vs call skew)
- No term structure modeling

### Recommendations

```python
# Add condor_screener/analytics/greeks.py
from scipy.stats import norm
import numpy as np

class BlackScholesGreeks:
    """Calculate Greeks using Black-Scholes-Merton model."""

    @staticmethod
    def calculate_delta(
        spot: float, strike: float, time_to_expiry: float,
        rate: float, vol: float, option_type: str
    ) -> float:
        """Calculate delta. Returns value between -1 and 1."""
        pass

    @staticmethod
    def validate_greeks(option: Option) -> bool:
        """Validate Greeks are consistent with option type and market."""
        if option.delta is None:
            return False

        # Calls should have positive delta, puts negative
        if option.option_type == "call" and option.delta < 0:
            return False
        if option.option_type == "put" and option.delta > 0:
            return False

        # Delta should be in [-1, 1]
        if abs(option.delta) > 1:
            return False

        return True

class VolatilitySurface:
    """Model IV surface for skew and term structure analysis."""

    def __init__(self, options: List[Option]):
        """Build surface from option chain."""
        pass

    def get_skew(self, expiration: date, atm_strike: float) -> float:
        """Calculate put-call skew at given expiration."""
        pass

    def get_term_structure(self, strike: float) -> Dict[date, float]:
        """Get IV term structure for a given strike."""
        pass
```

**Priority**: Critical
**Effort**: High
**Impact**: Essential for accurate risk assessment

---

## Section 3: Risk Management & Position Sizing

### Issues

**3.1 No Portfolio-Level Risk**
- Each IC evaluated in isolation
- No aggregate exposure calculation
- Can't assess correlation risk

**3.2 Missing Position Sizing**
- No Kelly Criterion or similar
- No account size consideration
- No max loss per position guidance

**3.3 No Margin Calculations**
- Iron condors require margin
- No calculation of required capital
- Can't assess capital efficiency

**3.4 No Greeks Aggregation**
- Portfolio delta not calculated
- No gamma exposure limits
- Can't assess vega risk across positions

**3.5 Missing Risk Limits**
- No max delta exposure
- No concentration limits
- No drawdown controls

### Recommendations

```python
# Add condor_screener/risk/portfolio.py
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Position:
    """Represents an open position."""
    iron_condor: IronCondor
    quantity: int
    entry_date: date
    cost_basis: float

class PortfolioRiskManager:
    """Manage portfolio-level risk metrics."""

    def __init__(self, positions: List[Position], account_value: float):
        self.positions = positions
        self.account_value = account_value

    def total_delta(self) -> float:
        """Calculate aggregate portfolio delta."""
        pass

    def total_gamma(self) -> float:
        """Calculate aggregate gamma exposure."""
        pass

    def total_theta(self) -> float:
        """Calculate daily theta decay."""
        pass

    def total_vega(self) -> float:
        """Calculate IV sensitivity."""
        pass

    def margin_required(self) -> float:
        """Calculate total margin requirement."""
        # For iron condor: max(put width, call width) per contract
        pass

    def position_size_kelly(self, ic: IronCondor, win_rate: float) -> int:
        """Calculate optimal position size using Kelly Criterion."""
        # Kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        pass

    def check_risk_limits(self) -> List[str]:
        """Check if portfolio violates risk limits."""
        violations = []

        if abs(self.total_delta()) > 100:
            violations.append(f"Delta exposure {self.total_delta()} exceeds limit")

        # Add more checks...
        return violations

# Add condor_screener/risk/margin.py
class MarginCalculator:
    """Calculate margin requirements for option positions."""

    @staticmethod
    def iron_condor_margin(ic: IronCondor, quantity: int) -> float:
        """Calculate margin for iron condor position.

        Margin = max(put_width, call_width) * 100 * quantity - net_credit
        """
        wing_width = max(ic.put_side_width, ic.call_side_width)
        credit_received = ic.net_credit * 100 * quantity
        return (wing_width * 100 * quantity) - credit_received
```

**Priority**: Critical
**Effort**: High
**Impact**: Essential for real money trading

---

## Section 4: Statistical & Quantitative Rigor

### Issues

**4.1 IV Rank/Percentile Too Simple**
- Uses only percentile rank, no statistical significance
- No confidence intervals
- No regime detection (high vol vs low vol periods)

**4.2 Expected Move Calculation Issues**
- Straddle-based method assumes liquid ATM options
- No adjustment for skew
- Discount factor (0.85) is magic number with no justification

**4.3 Realized Volatility Limitations**
- Only 20-day lookback
- No comparison across multiple timeframes
- Garman-Klass estimator good but no Yang-Zhang alternative

**4.4 No Statistical Testing**
- IV vs RV ratio not tested for significance
- No p-values for screening criteria
- Could be selecting based on noise

**4.5 Missing Quantitative Metrics**
- No Sharpe ratio projection
- No maximum adverse excursion
- No profit factor estimation

### Recommendations

```python
# Add condor_screener/analytics/statistics.py
import numpy as np
from scipy import stats
from typing import Tuple

class VolatilityStatistics:
    """Advanced statistical analysis for volatility."""

    @staticmethod
    def iv_rank_with_confidence(
        current_iv: float,
        historical_ivs: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float, float]:
        """Calculate IV rank with confidence intervals.

        Returns:
            (iv_rank, lower_bound, upper_bound)
        """
        rank = calculate_iv_rank(current_iv, historical_ivs)

        # Bootstrap confidence interval
        n_bootstrap = 1000
        bootstrap_ranks = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(historical_ivs, len(historical_ivs), replace=True)
            bootstrap_ranks.append(calculate_iv_rank(current_iv, sample))

        lower = np.percentile(bootstrap_ranks, (1 - confidence) / 2 * 100)
        upper = np.percentile(bootstrap_ranks, (1 + confidence) / 2 * 100)

        return rank, lower, upper

    @staticmethod
    def detect_vol_regime(historical_ivs: List[float]) -> str:
        """Detect volatility regime using HMM or similar.

        Returns:
            'low' | 'normal' | 'high' | 'crisis'
        """
        current = historical_ivs[-1]
        mean = np.mean(historical_ivs)
        std = np.std(historical_ivs)

        z_score = (current - mean) / std

        if z_score > 2:
            return 'crisis'
        elif z_score > 1:
            return 'high'
        elif z_score < -1:
            return 'low'
        else:
            return 'normal'

    @staticmethod
    def test_iv_rv_significance(iv: float, rv: float, n_samples: int) -> float:
        """Test if IV > RV is statistically significant.

        Returns:
            p-value
        """
        # Use t-test or similar
        pass

class PerformanceMetrics:
    """Calculate quantitative performance metrics."""

    @staticmethod
    def expected_sharpe(
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        trade_frequency: int
    ) -> float:
        """Estimate Sharpe ratio for strategy."""
        expected_return = win_rate * avg_win - (1 - win_rate) * avg_loss
        # Calculate std dev from win/loss distribution
        pass

    @staticmethod
    def profit_factor(wins: List[float], losses: List[float]) -> float:
        """Calculate profit factor: gross_profit / gross_loss."""
        return sum(wins) / abs(sum(losses)) if losses else float('inf')
```

**Priority**: High
**Effort**: High
**Impact**: Improves signal quality, reduces false positives

---

## Section 5: Pricing Models & Valuation

### Issues

**5.1 No Pricing Model**
- Relies entirely on market quotes
- Can't value when markets are closed
- No theoretical value calculation

**5.2 No Arbitrage Detection**
- Basic check (max profit < wing width) is insufficient
- No put-call parity validation
- Could miss complex arbitrage opportunities

**5.3 No Early Exercise Check**
- American options can be exercised early
- No check for deep ITM options near ex-dividend
- Assignment risk not assessed

**5.4 Missing Fair Value Comparison**
- No comparison between market price and theoretical value
- Can't identify mispriced options
- Missing edge calculation

### Recommendations

```python
# Add condor_screener/pricing/black_scholes.py
from scipy.stats import norm
import numpy as np

class BlackScholesPricer:
    """Black-Scholes-Merton option pricing model."""

    @staticmethod
    def price(
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        vol: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> float:
        """Calculate theoretical option price."""
        # Implement BS formula with dividends
        pass

    @staticmethod
    def implied_vol(
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        rate: float,
        option_type: str
    ) -> float:
        """Calculate implied volatility using Newton-Raphson."""
        pass

class ArbitrageDetector:
    """Detect arbitrage opportunities in option chains."""

    @staticmethod
    def check_put_call_parity(
        call: Option,
        put: Option,
        spot: float,
        rate: float
    ) -> Tuple[bool, float]:
        """Check put-call parity: C - P = S - K*exp(-rT).

        Returns:
            (is_violated, profit_if_violated)
        """
        pass

    @staticmethod
    def check_vertical_spread_arbitrage(
        lower_strike_option: Option,
        higher_strike_option: Option
    ) -> bool:
        """Check if vertical spread violates no-arbitrage bounds."""
        # For calls: C(K1) >= C(K2) if K1 < K2
        # For puts: P(K1) <= P(K2) if K1 < K2
        pass

    @staticmethod
    def check_calendar_spread_arbitrage(
        near_expiry: Option,
        far_expiry: Option
    ) -> bool:
        """Check if calendar spread violates no-arbitrage bounds."""
        # Far dated option should be worth more than near dated
        pass

class EarlyExerciseRisk:
    """Assess American option early exercise risk."""

    @staticmethod
    def should_exercise_early(
        option: Option,
        spot: float,
        dividend_date: date | None,
        dividend_amount: float
    ) -> bool:
        """Determine if early exercise is optimal."""
        # For calls: exercise early before ex-dividend if dividend > time value
        # For puts: exercise early if deep ITM and interest benefit > time value
        pass
```

**Priority**: Medium
**Effort**: High
**Impact**: Enables offline analysis, improves edge detection

---

## Section 6: Backtesting & Simulation

### Issues

**6.1 No Backtesting Framework**
- Mentioned in roadmap but critical for validation
- Can't verify strategy performance
- No way to optimize parameters

**6.2 Missing Trade Simulator**
- Can't model P&L paths
- No Monte Carlo simulation
- Can't assess worst-case scenarios

**6.3 No Parameter Optimization**
- Delta range, wing width, etc. are hardcoded defaults
- No walk-forward optimization
- Could be using suboptimal parameters

**6.4 No Performance Attribution**
- Can't identify what drives returns
- No factor decomposition
- Can't separate skill from luck

### Recommendations

```python
# Add condor_screener/backtest/engine.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

@dataclass
class Trade:
    """Represents a historical trade."""
    entry_date: date
    exit_date: date
    iron_condor: IronCondor
    entry_price: float
    exit_price: float
    pnl: float
    max_adverse_excursion: float

class BacktestEngine:
    """Backtest iron condor strategies on historical data."""

    def __init__(
        self,
        historical_chains: Dict[date, List[Option]],
        strategy_config: StrategyConfig,
        filter_config: FilterConfig,
        scoring_config: ScoringConfig
    ):
        self.historical_chains = historical_chains
        self.strategy_config = strategy_config
        self.filter_config = filter_config
        self.scoring_config = scoring_config
        self.trades: List[Trade] = []

    def run(self, start_date: date, end_date: date) -> List[Trade]:
        """Run backtest over date range."""
        pass

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        return {
            'total_return': sum(t.pnl for t in self.trades),
            'win_rate': len([t for t in self.trades if t.pnl > 0]) / len(self.trades),
            'avg_win': np.mean([t.pnl for t in self.trades if t.pnl > 0]),
            'avg_loss': np.mean([t.pnl for t in self.trades if t.pnl < 0]),
            'max_drawdown': self._calculate_max_drawdown(),
            'sharpe_ratio': self._calculate_sharpe(),
            'profit_factor': self._calculate_profit_factor(),
        }

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        pass

    def _calculate_sharpe(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        pass

class MonteCarloSimulator:
    """Monte Carlo simulation for P&L paths."""

    def simulate_pnl_paths(
        self,
        ic: IronCondor,
        spot: float,
        vol: float,
        days_to_expiry: int,
        n_simulations: int = 10000
    ) -> np.ndarray:
        """Simulate price paths and calculate P&L distribution."""
        # Use GBM or similar to simulate underlying paths
        # Calculate P&L at each step
        pass

    def calculate_var(self, pnl_paths: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        return np.percentile(pnl_paths, (1 - confidence) * 100)

    def calculate_cvar(self, pnl_paths: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        var = self.calculate_var(pnl_paths, confidence)
        return np.mean(pnl_paths[pnl_paths <= var])
```

**Priority**: High (for strategy validation)
**Effort**: Very High
**Impact**: Critical for production use, enables optimization

---

## Section 7: Production Readiness & Operational Concerns

### Issues

**7.1 No Logging**
- Uses `print()` statements instead of proper logging
- No log levels (debug, info, warning, error)
- Can't troubleshoot production issues

**7.2 Insufficient Error Handling**
- Try/except blocks are minimal
- No graceful degradation
- CSV parse errors kill entire program

**7.3 No Monitoring/Alerting**
- No health checks
- No performance metrics
- Can't detect degradation

**7.4 Missing Configuration Management**
- YAML configs good but no validation
- No environment-specific configs (dev/prod)
- Secrets in plain text (API keys would be exposed)

**7.5 No Rate Limiting**
- Future API integration will need rate limiting
- No retry logic for failed requests
- Could get banned from data provider

**7.6 No Caching**
- Recalculates same metrics repeatedly
- No memoization
- Performance issue for large chains

### Recommendations

```python
# Add condor_screener/utils/logging_config.py
import logging
from typing import Optional

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger("condor_screener")
    logger.setLevel(getattr(logging, log_level.upper()))

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Replace print() statements with:
# logger.info("Filter results: {}/{} options passed", len(filtered), len(options))
# logger.warning("IV Rank {} below minimum {}", iv_rank, config.min_iv_rank)
# logger.error("Failed to load CSV: {}", e)

# Add condor_screener/utils/error_handling.py
from typing import TypeVar, Callable
from functools import wraps

T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator to retry function with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    wait = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait}s: {e}")
                    time.sleep(wait)
        return wrapper
    return decorator

# Add condor_screener/utils/cache.py
from functools import lru_cache
from typing import List, Tuple

class AnalyticsCache:
    """Cache expensive analytics calculations."""

    def __init__(self, maxsize: int = 1000):
        self._cache: Dict[Tuple, Analytics] = {}
        self.maxsize = maxsize

    def get_or_compute(
        self,
        ic: IronCondor,
        spot: float,
        compute_func: Callable
    ) -> Analytics:
        """Get cached analytics or compute if not cached."""
        key = (ic, spot)  # IronCondor is frozen/hashable

        if key not in self._cache:
            if len(self._cache) >= self.maxsize:
                # Evict oldest entry (FIFO)
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = compute_func()

        return self._cache[key]

# Add condor_screener/config/env_config.py
from enum import Enum
from dataclasses import dataclass
import os

class Environment(Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

@dataclass
class EnvConfig:
    """Environment-specific configuration."""
    env: Environment
    api_key: str  # Load from env var, not hardcode
    api_url: str
    max_requests_per_minute: int
    cache_ttl_seconds: int

    @classmethod
    def from_env(cls) -> "EnvConfig":
        env_name = os.getenv("CONDOR_ENV", "dev")
        env = Environment(env_name)

        return cls(
            env=env,
            api_key=os.getenv("API_KEY", ""),  # Fail if not set in prod
            api_url=cls._get_api_url(env),
            max_requests_per_minute=cls._get_rate_limit(env),
            cache_ttl_seconds=300 if env == Environment.PROD else 60,
        )

    @staticmethod
    def _get_api_url(env: Environment) -> str:
        urls = {
            Environment.DEV: "https://dev-api.example.com",
            Environment.STAGING: "https://staging-api.example.com",
            Environment.PROD: "https://api.example.com",
        }
        return urls[env]

    @staticmethod
    def _get_rate_limit(env: Environment) -> int:
        limits = {
            Environment.DEV: 5,
            Environment.STAGING: 10,
            Environment.PROD: 60,
        }
        return limits[env]
```

**Priority**: High (for production deployment)
**Effort**: Medium
**Impact**: Essential for reliability and debugging

---

## Section 8: Code Architecture & Design Patterns

### Issues

**8.1 Tight Coupling in Analytics**
- `analyze_iron_condor()` does too much
- Hard to test individual components
- Difficult to extend

**8.2 Missing Dependency Injection**
- Hard-coded dependencies make testing difficult
- Can't easily swap data sources
- Not following SOLID principles

**8.3 No Strategy Pattern**
- Scoring is hardcoded
- Can't easily A/B test different scoring algorithms
- Violates Open/Closed Principle

**8.4 Global State in Examples**
- Example scripts use global variables
- Not reusable as library
- Hard to parallelize

**8.5 Missing Abstract Interfaces**
- No interface for data loaders
- Can't easily add Polygon/IBKR/TD Ameritrade
- Tight coupling to CSV format

### Recommendations

```python
# Add condor_screener/data/interfaces.py
from abc import ABC, abstractmethod
from typing import List
from datetime import date

class OptionDataProvider(ABC):
    """Abstract interface for option data providers."""

    @abstractmethod
    def fetch_option_chain(
        self,
        symbol: str,
        expiration: date | None = None
    ) -> List[Option]:
        """Fetch option chain for symbol."""
        pass

    @abstractmethod
    def fetch_spot_price(self, symbol: str) -> float:
        """Fetch current spot price."""
        pass

    @abstractmethod
    def fetch_historical_iv(
        self,
        symbol: str,
        days: int = 252
    ) -> List[float]:
        """Fetch historical implied volatilities."""
        pass

# Then implement:
class CSVDataProvider(OptionDataProvider):
    """CSV file data provider."""
    pass

class PolygonDataProvider(OptionDataProvider):
    """Polygon.io API provider."""
    pass

class InteractiveBrokersProvider(OptionDataProvider):
    """Interactive Brokers TWS API provider."""
    pass

# Add condor_screener/scoring/interfaces.py
from abc import ABC, abstractmethod

class ScoringStrategy(ABC):
    """Abstract strategy for scoring iron condors."""

    @abstractmethod
    def score(self, analytics: Analytics) -> float:
        """Score an analytics object. Returns 0.0 to 1.0."""
        pass

class WeightedScoring(ScoringStrategy):
    """Current weighted scoring implementation."""
    pass

class MachineLearningScoring(ScoringStrategy):
    """ML-based scoring (future)."""
    pass

class KellyCriterionScoring(ScoringStrategy):
    """Kelly Criterion-based scoring."""
    pass

# Use dependency injection:
class Screener:
    """Main screening orchestrator."""

    def __init__(
        self,
        data_provider: OptionDataProvider,
        scoring_strategy: ScoringStrategy,
        filter_config: FilterConfig,
        strategy_config: StrategyConfig
    ):
        self.data_provider = data_provider
        self.scoring_strategy = scoring_strategy
        self.filter_config = filter_config
        self.strategy_config = strategy_config

    def screen(self, symbol: str) -> List[Analytics]:
        """Screen symbol and return ranked results."""
        # Load data
        options = self.data_provider.fetch_option_chain(symbol)
        spot = self.data_provider.fetch_spot_price(symbol)

        # Apply filters
        # Generate candidates
        # Score
        # Rank
        pass
```

**Priority**: Medium
**Effort**: Medium
**Impact**: Improves testability, extensibility, maintainability

---

## Section 9: Testing Gaps

### Issues

**9.1 No Property-Based Testing**
- Only example-based tests
- Missing edge cases that property tests would catch
- No fuzzing

**9.2 No Stress Testing**
- Tests use small option chains (8 options)
- Doesn't test with 1000+ options (SPX)
- No performance benchmarks

**9.3 Missing Integration with Real Data**
- All tests use synthetic data
- No validation against known-good real chains
- Could have systematic biases

**9.4 No Regression Tests**
- If a bug is found in production, no test added
- No golden file testing
- Results could drift over time

**9.5 Limited Parameterized Testing**
- Many similar tests could be parameterized
- Reduces test code volume
- Makes test intent clearer

### Recommendations

```python
# Add tests using Hypothesis
from hypothesis import given, strategies as st
import hypothesis.extra.numpy as npst

class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        bid=st.floats(min_value=0.01, max_value=100.0),
        ask=st.floats(min_value=0.01, max_value=100.0)
    )
    def test_mid_price_always_between_bid_ask(self, bid: float, ask: float):
        """Property: mid price should always be between bid and ask."""
        # Ensure bid <= ask
        if bid > ask:
            bid, ask = ask, bid

        option = Option(
            ticker="SPY", strike=100.0, expiration=date.today() + timedelta(days=30),
            option_type="call", bid=bid, ask=ask, volume=100, open_interest=1000,
            delta=0.5, implied_vol=0.2
        )

        assert bid <= option.mid <= ask

    @given(
        spot=st.floats(min_value=10.0, max_value=1000.0),
        strikes=st.lists(
            st.floats(min_value=10.0, max_value=1000.0),
            min_size=4,
            max_size=100
        )
    )
    def test_iron_condor_max_loss_properties(self, spot: float, strikes: List[float]):
        """Property: max loss should equal wing width minus credit."""
        # Generate IC from strikes
        # Verify max_loss = wing_width - net_credit
        pass

# Add stress tests
class TestStressScenarios:
    """Stress tests with large data sets."""

    def test_screen_large_option_chain(self):
        """Test with SPX-sized chain (2000+ options)."""
        options = self._generate_large_chain(n_strikes=500, n_expirations=4)

        # Should complete in reasonable time
        start = time.time()
        result = screen_workflow(options)
        elapsed = time.time() - start

        assert elapsed < 10.0  # Should complete in under 10 seconds

    def test_memory_usage_large_chain(self):
        """Ensure generator pattern prevents memory explosion."""
        import tracemalloc

        tracemalloc.start()
        options = self._generate_large_chain(n_strikes=1000, n_expirations=10)

        # Generate condors (should use iterator, not materialize all)
        gen = generate_iron_condors(options, StrategyConfig())
        first_100 = list(itertools.islice(gen, 100))

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable (< 100 MB for generator)
        assert peak < 100 * 1024 * 1024

# Add regression tests
class TestRegressions:
    """Regression tests for previously found bugs."""

    def test_regression_zero_credit_condor(self):
        """Regression: ensure zero-credit condors are rejected.

        Bug found: 2025-12-21
        Issue: Flat price curve generated zero-credit condors
        Fix: Updated validation in _is_valid_condor()
        """
        # Test case that previously failed
        pass
```

**Priority**: Medium
**Effort**: Medium
**Impact**: Catches more bugs, prevents regressions

---

## Section 10: Documentation Gaps

### Issues

**10.1 Missing Quantitative Methodology**
- No mathematical definitions
- Expected move calculation not fully explained
- Garman-Klass formula not documented

**10.2 No API Documentation**
- Functions lack comprehensive docstrings
- No examples in docstrings
- No auto-generated API docs (Sphinx)

**10.3 Missing Usage Examples**
- Only one example (screen_spy.py)
- No example for custom scoring
- No example for batch processing

**10.4 No Performance Tuning Guide**
- Users don't know how to optimize for large chains
- No guidance on parameter selection
- No tips for production deployment

**10.5 Insufficient Assumptions Documentation**
- Mid-price execution assumption buried in comments
- No discussion of slippage
- Commission assumptions not stated

### Recommendations

Create these documentation files:

```markdown
# docs/methodology.md
## Quantitative Methodology

### Expected Move Calculation

#### Straddle-Based Method
The expected move is estimated from the ATM straddle price using:

$$
EM_{straddle} = (C_{ATM} + P_{ATM}) \times discount
$$

Where:
- $C_{ATM}$ = ATM call mid price
- $P_{ATM}$ = ATM put mid price
- $discount$ = 0.85 (historical average of actual move / straddle)

**Rationale**: Market makers price the ATM straddle to reflect expected
movement, incorporating skew and supply/demand. The 0.85 discount factor
accounts for time decay and statistical properties of returns.

**Reference**: McMillan, L. (2012). "Options as a Strategic Investment"

#### IV-Based Method
Alternatively, expected move can be estimated from implied volatility:

$$
EM_{IV} = S \times IV \times \sqrt{\frac{DTE}{365}}
$$

Where:
- $S$ = spot price
- $IV$ = implied volatility (annualized)
- $DTE$ = days to expiration

### Realized Volatility: Garman-Klass Estimator

The Garman-Klass estimator uses intraday high-low range for improved accuracy:

$$
\sigma_{GK}^2 = \frac{1}{n} \sum_{i=1}^{n} \left[ 0.5(H_i - L_i)^2 - (2\ln 2 - 1)(C_i - O_i)^2 \right]
$$

Where:
- $H_i$ = log(high/close_{i-1})
- $L_i$ = log(low/close_{i-1})
- $C_i$ = log(close/close_{i-1})
- $O_i$ = log(open/close_{i-1})

**Reference**: Garman, M.B. and Klass, M.J. (1980). "On the Estimation of
Security Price Volatilities from Historical Data"
```

```markdown
# docs/api_reference.md
# API Reference

Auto-generated from docstrings using Sphinx:

\`\`\`bash
pip install sphinx sphinx-rtd-theme
cd docs
sphinx-quickstart
sphinx-apidoc -o source/ ../condor_screener/
make html
\`\`\`
```

```python
# condor_screener/examples/custom_scoring.py
"""
Example: Custom Scoring Strategy

This example shows how to implement and use a custom scoring strategy.
"""

from condor_screener.scoring.interfaces import ScoringStrategy
from condor_screener.models.analytics import Analytics

class ConservativeScoring(ScoringStrategy):
    """Conservative scoring that heavily weights distance from expected move."""

    def score(self, analytics: Analytics) -> float:
        """Score based primarily on safety (distance) rather than ROR."""
        # 60% weight on distance, 30% on liquidity, 10% on IV edge
        distance_score = analytics.avg_distance_pct / 10.0  # Normalize
        liquidity_score = analytics.liquidity_score
        iv_score = min(1.0, analytics.iv_to_rv_ratio / 2.0)

        return 0.6 * distance_score + 0.3 * liquidity_score + 0.1 * iv_score

# Usage:
screener = Screener(
    data_provider=CSVDataProvider(),
    scoring_strategy=ConservativeScoring(),
    filter_config=FilterConfig(),
    strategy_config=StrategyConfig()
)

results = screener.screen("SPY")
```

**Priority**: Medium
**Effort**: Low-Medium
**Impact**: Improves usability, reduces support burden

---

## Section 11: Performance & Scalability

### Issues

**11.1 No Parallelization**
- Screening multiple tickers is sequential
- Analytics calculations not parallelized
- Missing multiprocessing/async support

**11.2 Inefficient Data Structures**
- Linear search in some places
- No indexing of options by strike/expiration
- Repeated calculations

**11.3 No Database Support**
- Everything in memory
- Can't handle historical data at scale
- No persistent storage

**11.4 Missing Incremental Updates**
- Recalculates everything on each run
- No delta updates for changed data
- Inefficient for real-time screening

### Recommendations

```python
# Add condor_screener/utils/parallel.py
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Callable, TypeVar
import multiprocessing

T = TypeVar('T')
R = TypeVar('R')

class ParallelScreener:
    """Parallel screening for multiple tickers."""

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers or multiprocessing.cpu_count()

    def screen_multiple(
        self,
        tickers: List[str],
        screen_func: Callable[[str], List[Analytics]]
    ) -> Dict[str, List[Analytics]]:
        """Screen multiple tickers in parallel."""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(screen_func, ticker): ticker
                for ticker in tickers
            }

            results = {}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    logger.error(f"Failed to screen {ticker}: {e}")
                    results[ticker] = []

            return results

# Add condor_screener/data/database.py
import sqlite3
from typing import List, Optional

class OptionDatabase:
    """SQLite database for option chain storage."""

    def __init__(self, db_path: str = "options.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        """Create database schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS option_chains (
                id INTEGER PRIMARY KEY,
                ticker TEXT,
                strike REAL,
                expiration DATE,
                option_type TEXT,
                timestamp DATETIME,
                bid REAL,
                ask REAL,
                last REAL,
                volume INTEGER,
                open_interest INTEGER,
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                implied_vol REAL,
                UNIQUE(ticker, strike, expiration, option_type, timestamp)
            )
        """)

        # Create indices for fast lookups
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker_exp
            ON option_chains(ticker, expiration)
        """)

    def insert_chain(self, options: List[Option], timestamp: datetime):
        """Insert option chain snapshot."""
        pass

    def fetch_latest_chain(self, ticker: str, expiration: Optional[date] = None) -> List[Option]:
        """Fetch most recent option chain."""
        pass

    def fetch_historical_iv(self, ticker: str, days: int = 252) -> List[float]:
        """Fetch historical IV data."""
        pass
```

**Priority**: Low (unless scaling issues occur)
**Effort**: Medium
**Impact**: Enables real-time screening, larger data sets

---

## Priority Matrix

### Critical (Do First)
1. **Greeks Calculation & Validation** (Section 2)
2. **Risk Management & Position Sizing** (Section 3)
3. **Production Logging & Error Handling** (Section 7)

### High Priority (Do Soon)
4. **Statistical Rigor** (Section 4)
5. **Data Quality & Validation** (Section 1)
6. **Backtesting Framework** (Section 6)
7. **Documentation** (Section 10)

### Medium Priority (Plan For)
8. **Code Architecture Improvements** (Section 8)
9. **Pricing Models** (Section 5)
10. **Testing Enhancements** (Section 9)

### Low Priority (Nice to Have)
11. **Performance & Scalability** (Section 11)

---

## Estimated Effort

| Section | Effort (Person-Days) | Complexity |
|---------|---------------------|------------|
| 1. Data Quality | 3-5 | Medium |
| 2. Greeks | 8-10 | High |
| 3. Risk Management | 10-15 | High |
| 4. Statistical Rigor | 5-8 | High |
| 5. Pricing Models | 8-12 | High |
| 6. Backtesting | 15-20 | Very High |
| 7. Production Ops | 3-5 | Medium |
| 8. Architecture | 5-8 | Medium |
| 9. Testing | 3-5 | Medium |
| 10. Documentation | 2-3 | Low |
| 11. Performance | 5-8 | Medium |
| **Total** | **67-99 days** | **~3-5 months** |

---

## Conclusion

This is a **well-crafted proof-of-concept** that demonstrates solid software engineering practices. The code is clean, testable, and follows good design principles. However, it requires significant quantitative and operational enhancements before production use with real money.

**Recommended Path Forward:**

**Phase 1 (Immediate - 2-3 weeks):**
- Add production logging and error handling
- Implement data quality validation
- Add Greeks validation with fallback calculations

**Phase 2 (Short-term - 1-2 months):**
- Build risk management framework
- Improve statistical rigor
- Create backtesting engine

**Phase 3 (Medium-term - 2-3 months):**
- Implement pricing models
- Optimize code architecture
- Enhance testing and documentation

**Overall Rating**: **7/10**
- **Code Quality**: 9/10 (excellent)
- **Test Coverage**: 8/10 (very good)
- **Quantitative Rigor**: 5/10 (needs work)
- **Production Readiness**: 4/10 (significant gaps)
- **Documentation**: 7/10 (good foundation)

With the recommended improvements, this could become a **production-grade options screening platform**.
