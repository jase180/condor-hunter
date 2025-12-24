"""Caching utilities for expensive analytics calculations.

Provides LRU caching for computed analytics to avoid redundant calculations.
"""

from typing import Dict, Tuple, Callable, TypeVar, Optional
from collections import OrderedDict
import logging

from ..models.iron_condor import IronCondor
from ..models.analytics import Analytics

logger = logging.getLogger("condor_screener.cache")

T = TypeVar('T')


class AnalyticsCache:
    """Cache for expensive analytics calculations.

    Uses LRU (Least Recently Used) eviction policy when cache is full.
    """

    def __init__(self, maxsize: int = 1000):
        """Initialize analytics cache.

        Args:
            maxsize: Maximum number of cached analytics objects
        """
        self._cache: OrderedDict[Tuple, Analytics] = OrderedDict()
        self.maxsize = maxsize
        self._hits = 0
        self._misses = 0

    def get_or_compute(
        self,
        ic: IronCondor,
        spot: float,
        compute_func: Callable[[], Analytics],
        extra_key: Optional[Tuple] = None
    ) -> Analytics:
        """Get cached analytics or compute if not cached.

        Args:
            ic: IronCondor to get analytics for
            spot: Spot price (affects analytics calculations)
            compute_func: Function to compute analytics if not cached
            extra_key: Optional extra key components for cache key

        Returns:
            Analytics object (from cache or freshly computed)

        Example:
            >>> cache = AnalyticsCache()
            >>> analytics = cache.get_or_compute(
            >>>     ic=my_condor,
            >>>     spot=560.0,
            >>>     compute_func=lambda: analyze_iron_condor(my_condor, 560.0, ...)
            >>> )
        """
        # Create cache key from iron condor and spot price
        # IronCondor is frozen/hashable, so this works
        key = (ic, spot)
        if extra_key:
            key = key + extra_key

        # Check cache
        if key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            logger.debug(f"Cache hit for IC {ic.short_put.strike}/{ic.short_call.strike}")
            return self._cache[key]

        # Cache miss - compute
        self._misses += 1
        logger.debug(f"Cache miss for IC {ic.short_put.strike}/{ic.short_call.strike}")

        analytics = compute_func()

        # Store in cache
        if len(self._cache) >= self.maxsize:
            # Evict oldest entry (FIFO/LRU)
            evicted_key = next(iter(self._cache))
            del self._cache[evicted_key]
            logger.debug(f"Cache full, evicted entry")

        self._cache[key] = analytics

        return analytics

    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Analytics cache cleared")

    def stats(self) -> Dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            'size': len(self._cache),
            'maxsize': self.maxsize,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
        }

    def __repr__(self) -> str:
        """String representation of cache stats."""
        stats = self.stats()
        return (
            f"AnalyticsCache(size={stats['size']}/{stats['maxsize']}, "
            f"hits={stats['hits']}, misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']:.1f}%)"
        )
