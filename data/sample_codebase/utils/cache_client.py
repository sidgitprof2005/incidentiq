import logging
from functools import lru_cache
from typing import Any, Optional

logger = logging.getLogger(__name__)

class CacheClient:
    """
    A simulated cache client utilizing an LRU cache for in-memory storage.
    """
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        logger.info("Initialized CacheClient with LRU cache capacity of 1000.")

    @lru_cache(maxsize=1000)
    def _fetch_from_cache(self, key: str) -> Optional[Any]:
        """
        Helper method decorated with lru_cache to fetch cached items.
        
        Args:
            key (str): The cache key.
            
        Returns:
            Optional[Any]: The cached value if found, else None.
        """
        logger.debug(f"Cache miss or cache fetch for key: {key}")
        return self.store.get(key)

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache.

        Args:
            key (str): The key to look up.

        Returns:
            Optional[Any]: The cached value if exists, otherwise None.
        """
        value = self._fetch_from_cache(key)
        if value is not None:
            logger.debug(f"Cache hit for key: {key}")
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Sets a value in the cache.

        Args:
            key (str): The key to set.
            value (Any): The value to store.
        """
        self.store[key] = value
        self._fetch_from_cache.cache_clear()
        logger.debug(f"Cache set for key: {key}")

    def invalidate(self, key: str) -> None:
        """
        Invalidates a specific key in the cache.

        Args:
            key (str): The key to invalidate.
        """
        if key in self.store:
            del self.store[key]
            self._fetch_from_cache.cache_clear()
            logger.debug(f"Cache key invalidated: {key}")
