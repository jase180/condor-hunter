"""Scoring and ranking system for iron condors.

Implements transparent, weighted scoring with configurable weights.
"""

from dataclasses import replace
from typing import List, Dict, Any

from ..models.analytics import Analytics


class ScoringConfig:
    """Configuration for scoring weights and normalization ranges."""

    def __init__(
        self,
        weight_ror: float = 0.30,
        weight_distance: float = 0.30,
        weight_liquidity: float = 0.20,
        weight_iv_edge: float = 0.20,
        ror_min: float = 10.0,
        ror_max: float = 50.0,
        distance_min: float = 0.0,
        distance_max: float = 15.0,
        iv_ratio_min: float = 1.0,
        iv_ratio_max: float = 2.0,
    ):
        """Initialize scoring configuration.

        Args:
            weight_ror: Weight for return on risk component
            weight_distance: Weight for distance from expected move
            weight_liquidity: Weight for liquidity quality
            weight_iv_edge: Weight for IV/RV edge
            ror_min: Minimum ROR for normalization (%)
            ror_max: Maximum ROR for normalization (%)
            distance_min: Minimum distance for normalization (%)
            distance_max: Maximum distance for normalization (%)
            iv_ratio_min: Minimum IV/RV ratio for normalization
            iv_ratio_max: Maximum IV/RV ratio for normalization
        """
        self.weight_ror = weight_ror
        self.weight_distance = weight_distance
        self.weight_liquidity = weight_liquidity
        self.weight_iv_edge = weight_iv_edge

        self.ror_min = ror_min
        self.ror_max = ror_max
        self.distance_min = distance_min
        self.distance_max = distance_max
        self.iv_ratio_min = iv_ratio_min
        self.iv_ratio_max = iv_ratio_max

        # Validate weights sum to ~1.0
        total_weight = weight_ror + weight_distance + weight_liquidity + weight_iv_edge
        if abs(total_weight - 1.0) > 0.01:
            print(f"Warning: Weights sum to {total_weight:.3f}, not 1.0")

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ScoringConfig":
        """Create ScoringConfig from dictionary (e.g., from YAML).

        Args:
            config: Dictionary with scoring configuration

        Returns:
            ScoringConfig instance
        """
        weights = config.get('weights', {})
        norm = config.get('normalization', {})

        return cls(
            weight_ror=weights.get('return_on_risk', 0.30),
            weight_distance=weights.get('distance_from_em', 0.30),
            weight_liquidity=weights.get('liquidity', 0.20),
            weight_iv_edge=weights.get('iv_edge', 0.20),
            ror_min=norm.get('ror_min', 10.0),
            ror_max=norm.get('ror_max', 50.0),
            distance_min=norm.get('distance_min', 0.0),
            distance_max=norm.get('distance_max', 15.0),
            iv_ratio_min=norm.get('iv_ratio_min', 1.0),
            iv_ratio_max=norm.get('iv_ratio_max', 2.0),
        )


def score_analytics(analytics: Analytics, config: ScoringConfig) -> Analytics:
    """Compute composite score for an Analytics object.

    Args:
        analytics: Analytics object to score
        config: ScoringConfig with weights and normalization ranges

    Returns:
        New Analytics object with composite_score field set

    Design:
        - Each component normalized to [0, 1] using min-max scaling
        - Components weighted and summed
        - Score is transparent (user can inspect intermediate values)
    """
    # Component 1: Return on risk (higher is better)
    ror = analytics.iron_condor.return_on_risk
    ror_normalized = normalize(ror, config.ror_min, config.ror_max)

    # Component 2: Distance from expected move (higher is better)
    avg_distance = analytics.avg_distance_pct
    distance_normalized = normalize(avg_distance, config.distance_min, config.distance_max)

    # Component 3: Liquidity (already 0-1, no normalization needed)
    liquidity_normalized = analytics.liquidity_score

    # Component 4: IV edge (higher is better)
    iv_ratio = analytics.iv_to_rv_ratio
    iv_edge_normalized = normalize(iv_ratio, config.iv_ratio_min, config.iv_ratio_max)

    # Composite score
    composite = (
        config.weight_ror * ror_normalized +
        config.weight_distance * distance_normalized +
        config.weight_liquidity * liquidity_normalized +
        config.weight_iv_edge * iv_edge_normalized
    )

    # Return new Analytics object with score set
    return replace(analytics, composite_score=composite)


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalization to [0, 1] range.

    Args:
        value: Value to normalize
        min_val: Minimum expected value
        max_val: Maximum expected value

    Returns:
        Normalized value clamped to [0, 1]
    """
    if max_val == min_val:
        return 0.5  # Neutral if no range

    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))  # Clamp to [0, 1]


def rank_analytics(
    analytics_list: List[Analytics],
    config: ScoringConfig,
    top_n: int | None = None,
) -> List[Analytics]:
    """Score and rank a list of Analytics objects.

    Args:
        analytics_list: List of Analytics objects to score
        config: ScoringConfig with weights
        top_n: Optional limit on number of results to return

    Returns:
        Sorted list of Analytics objects (highest score first)

    Note:
        All Analytics objects will have composite_score field set.
    """
    # Score all candidates
    scored = [score_analytics(a, config) for a in analytics_list]

    # Sort by score (descending)
    ranked = sorted(scored, key=lambda a: a.composite_score or 0.0, reverse=True)

    # Return top N if specified
    if top_n is not None:
        return ranked[:top_n]
    else:
        return ranked


def adaptive_normalization(analytics_list: List[Analytics]) -> ScoringConfig:
    """Compute normalization ranges from actual candidate pool.

    Args:
        analytics_list: List of Analytics objects

    Returns:
        ScoringConfig with normalization ranges set from data

    Use case:
        When you don't know typical ranges in advance, compute them from
        the candidate pool. This ensures scoring uses the full [0, 1] range.
    """
    if not analytics_list:
        return ScoringConfig()  # Return defaults

    # Extract values
    rors = [a.iron_condor.return_on_risk for a in analytics_list]
    distances = [a.avg_distance_pct for a in analytics_list]
    iv_ratios = [a.iv_to_rv_ratio for a in analytics_list]

    # Compute min/max
    ror_min = min(rors)
    ror_max = max(rors)
    distance_min = min(distances)
    distance_max = max(distances)
    iv_ratio_min = min(iv_ratios)
    iv_ratio_max = max(iv_ratios)

    return ScoringConfig(
        ror_min=ror_min,
        ror_max=ror_max,
        distance_min=distance_min,
        distance_max=distance_max,
        iv_ratio_min=iv_ratio_min,
        iv_ratio_max=iv_ratio_max,
    )
