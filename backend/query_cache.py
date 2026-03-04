"""
Query Caching System for Performance Optimization
Reduces repeated search overhead with intelligent caching
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryCache:
    """
    In-memory cache for search queries with TTL and size limits

    Features:
    - Time-based expiration (TTL)
    - LRU eviction when cache is full
    - Hash-based keying from query + criteria
    """

    def __init__(self, ttl_minutes: int = 15, max_size: int = 100):
        """
        Initialize query cache

        Args:
            ttl_minutes: Time-to-live in minutes (default: 15)
            max_size: Maximum number of cached entries (default: 100)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

        logger.info(f"QueryCache initialized: TTL={ttl_minutes}min, max_size={max_size}")

    def _make_key(self, query: str, criteria: Dict) -> str:
        """
        Generate cache key from query and criteria

        Args:
            query: Search query string
            criteria: Parsed search criteria dict

        Returns:
            MD5 hash as hex string
        """
        # Serialize to JSON with sorted keys for consistency
        cache_input = json.dumps({
            "query": query.lower().strip(),  # Normalize query
            "criteria": criteria
        }, sort_keys=True)

        # Hash to get consistent key
        return hashlib.md5(cache_input.encode()).hexdigest()

    def get(self, query: str, criteria: Dict) -> Optional[List[Dict]]:
        """
        Retrieve cached results if available and not expired

        Args:
            query: Search query string
            criteria: Parsed search criteria

        Returns:
            Cached results list, or None if not found/expired
        """
        key = self._make_key(query, criteria)

        if key not in self.cache:
            self.misses += 1
            logger.debug(f"Cache MISS: {query[:50]}")
            return None

        entry = self.cache[key]
        age = datetime.now() - entry["timestamp"]

        # Check if expired
        if age > self.ttl:
            logger.debug(f"Cache EXPIRED: {query[:50]} (age: {age.total_seconds():.1f}s)")
            del self.cache[key]
            self.misses += 1
            return None

        # Cache hit
        self.hits += 1
        entry["last_accessed"] = datetime.now()
        logger.info(f"Cache HIT: {query[:50]} (age: {age.total_seconds():.1f}s)")
        return entry["result"]

    def set(self, query: str, criteria: Dict, result: List[Dict]):
        """
        Store query results in cache

        Args:
            query: Search query string
            criteria: Parsed search criteria
            result: Search results to cache
        """
        key = self._make_key(query, criteria)

        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_oldest()

        # Store entry
        self.cache[key] = {
            "timestamp": datetime.now(),
            "last_accessed": datetime.now(),
            "result": result,
            "query": query[:100],  # Store truncated query for debugging
        }

        logger.debug(f"Cache SET: {query[:50]} (size: {len(self.cache)}/{self.max_size})")

    def _evict_oldest(self):
        """
        Evict the least recently accessed entry (LRU)
        """
        if not self.cache:
            return

        # Find entry with oldest last_accessed time
        oldest_key = min(
            self.cache.items(),
            key=lambda x: x[1]["last_accessed"]
        )[0]

        evicted_query = self.cache[oldest_key]["query"]
        del self.cache[oldest_key]
        logger.debug(f"Cache EVICT (LRU): {evicted_query}")

    def clear(self):
        """Clear all cached entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache CLEAR: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 1),
            "ttl_minutes": self.ttl.total_seconds() / 60
        }

    def cleanup_expired(self):
        """
        Remove all expired entries from cache
        Useful for periodic maintenance
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry["timestamp"] > self.ttl
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cache cleanup: {len(expired_keys)} expired entries removed")

        return len(expired_keys)


# Global cache instance
# Initialized with default settings (15 min TTL, 100 max size)
query_cache = QueryCache(ttl_minutes=15, max_size=100)
