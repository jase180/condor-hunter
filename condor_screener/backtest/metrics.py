"""Performance metrics calculation for backtesting results."""

from dataclasses import dataclass
from typing import List
import math
import logging

from condor_screener.backtest.simulator import BacktestResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PerformanceMetrics:
    """Performance metrics for a set of backtest results.

    Attributes:
        total_trades: Total number of trades
        winners: Number of winning trades
        losers: Number of losing trades
        win_rate: Percentage of winning trades (0-100)
        avg_return_pct: Average return % per trade
        avg_winner_pct: Average return % for winners only
        avg_loser_pct: Average return % for losers only
        total_pnl: Total P&L across all trades
        max_drawdown_pct: Maximum drawdown as % of cumulative peak
        sharpe_ratio: Sharpe ratio (annualized)
        sortino_ratio: Sortino ratio (annualized, using downside deviation)
        profit_factor: Ratio of gross profit to gross loss
        avg_days_held: Average number of days positions were held
        best_trade_pct: Best single trade return %
        worst_trade_pct: Worst single trade return %
    """
    total_trades: int
    winners: int
    losers: int
    win_rate: float
    avg_return_pct: float
    avg_winner_pct: float
    avg_loser_pct: float
    total_pnl: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_days_held: float
    best_trade_pct: float
    worst_trade_pct: float


def calculate_metrics(results: List[BacktestResult]) -> PerformanceMetrics:
    """Calculate performance metrics from backtest results.

    Args:
        results: List of BacktestResult objects

    Returns:
        PerformanceMetrics with all calculated statistics
    """
    if not results:
        return PerformanceMetrics(
            total_trades=0,
            winners=0,
            losers=0,
            win_rate=0.0,
            avg_return_pct=0.0,
            avg_winner_pct=0.0,
            avg_loser_pct=0.0,
            total_pnl=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            profit_factor=0.0,
            avg_days_held=0.0,
            best_trade_pct=0.0,
            worst_trade_pct=0.0,
        )

    # Basic counts
    total_trades = len(results)
    winners = sum(1 for r in results if r.is_winner)
    losers = total_trades - winners
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0.0

    # Return statistics
    returns = [r.return_pct for r in results]
    avg_return_pct = sum(returns) / len(returns) if returns else 0.0

    winner_returns = [r.return_pct for r in results if r.is_winner]
    avg_winner_pct = sum(winner_returns) / len(winner_returns) if winner_returns else 0.0

    loser_returns = [r.return_pct for r in results if not r.is_winner]
    avg_loser_pct = sum(loser_returns) / len(loser_returns) if loser_returns else 0.0

    # P&L statistics
    total_pnl = sum(r.realized_pnl for r in results)
    best_trade_pct = max(returns) if returns else 0.0
    worst_trade_pct = min(returns) if returns else 0.0

    # Profit factor
    gross_profit = sum(r.realized_pnl for r in results if r.is_winner)
    gross_loss = abs(sum(r.realized_pnl for r in results if not r.is_winner))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    # Drawdown
    max_drawdown_pct = _calculate_max_drawdown(results)

    # Sharpe ratio (annualized)
    sharpe_ratio = _calculate_sharpe_ratio(returns)

    # Sortino ratio (annualized, using downside deviation)
    sortino_ratio = _calculate_sortino_ratio(returns)

    # Average holding period
    avg_days_held = sum(r.days_held for r in results) / len(results) if results else 0.0

    return PerformanceMetrics(
        total_trades=total_trades,
        winners=winners,
        losers=losers,
        win_rate=win_rate,
        avg_return_pct=avg_return_pct,
        avg_winner_pct=avg_winner_pct,
        avg_loser_pct=avg_loser_pct,
        total_pnl=total_pnl,
        max_drawdown_pct=max_drawdown_pct,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        profit_factor=profit_factor,
        avg_days_held=avg_days_held,
        best_trade_pct=best_trade_pct,
        worst_trade_pct=worst_trade_pct,
    )


def _calculate_max_drawdown(results: List[BacktestResult]) -> float:
    """Calculate maximum drawdown as % of cumulative peak.

    Returns:
        Max drawdown as percentage (positive number, e.g., 25.5 for 25.5% drawdown)
    """
    if not results:
        return 0.0

    # Sort by exit date to get chronological P&L
    sorted_results = sorted(results, key=lambda r: r.exit_date)

    cumulative_pnl = 0.0
    peak = 0.0
    max_dd = 0.0

    for result in sorted_results:
        cumulative_pnl += result.realized_pnl
        if cumulative_pnl > peak:
            peak = cumulative_pnl
        if peak > 0:
            drawdown = (peak - cumulative_pnl) / peak * 100
            max_dd = max(max_dd, drawdown)

    return max_dd


def _calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sharpe ratio.

    Args:
        returns: List of return percentages
        risk_free_rate: Annual risk-free rate (default 0%)

    Returns:
        Annualized Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    # Assume ~30-45 day holding period = ~8-12 trades per year
    # Use 10 as conservative estimate
    trades_per_year = 10
    annualization_factor = math.sqrt(trades_per_year)

    sharpe = ((avg_return - risk_free_rate) / std_dev) * annualization_factor
    return sharpe


def _calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sortino ratio (uses downside deviation only).

    Args:
        returns: List of return percentages
        risk_free_rate: Annual risk-free rate (default 0%)

    Returns:
        Annualized Sortino ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    avg_return = sum(returns) / len(returns)

    # Downside deviation (only negative returns)
    downside_returns = [r for r in returns if r < 0]
    if not downside_returns:
        # No downside = infinite Sortino, cap at 10.0
        return 10.0

    downside_variance = sum((r - 0) ** 2 for r in downside_returns) / len(downside_returns)
    downside_std = math.sqrt(downside_variance)

    if downside_std == 0:
        return 10.0

    # Annualize (assume ~10 trades per year)
    trades_per_year = 10
    annualization_factor = math.sqrt(trades_per_year)

    sortino = ((avg_return - risk_free_rate) / downside_std) * annualization_factor
    return sortino
