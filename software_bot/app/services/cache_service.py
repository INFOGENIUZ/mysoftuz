import logging
import asyncio
import time
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class CacheService:
    """
    Lightweight, thread-safe In-Memory TTL Cache Layer with pattern invalidation.
    """
    _instance: Optional["CacheService"] = None

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "CacheService":
        if cls._instance is None:
            cls._instance = CacheService()
        return cls._instance

    async def get(self, key: str) -> Optional[Any]:
        """Fetch item from cache if key exists and has not expired."""
        async with self._lock:
            if key not in self._cache:
                return None
            val, expire_at = self._cache[key]
            if time.time() > expire_at:
                del self._cache[key]
                return None
            return val

    async def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        """Set item in cache with TTL expiry in seconds."""
        async with self._lock:
            expire_at = time.time() + ttl_seconds
            self._cache[key] = (value, expire_at)

    async def delete(self, key: str) -> bool:
        """Delete specific key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def invalidate_pattern(self, prefix: str) -> int:
        """Deletes all cache entries matching prefix."""
        async with self._lock:
            keys_to_del = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    async def clear(self) -> None:
        """Clears all cached entries."""
        async with self._lock:
            self._cache.clear()
