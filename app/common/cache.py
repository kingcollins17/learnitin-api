"""Centralized caching service built on cachetools.TTLCache.

Provides a unified API so feature modules don't instantiate TTLCache directly.
Modules register a named cache via ``cache_service.register()`` and then
interact entirely through the service's public key-level methods.

Usage:
    from app.common.cache import cache_service

    # At module load — register the cache once
    cache_service.register("credit_balances", maxsize=4096, ttl=30)

    # At runtime — read / write through the service
    cache_service.set("credit_balances", user_id, 500)
    balance = cache_service.get("credit_balances", user_id)
    cache_service.delete("credit_balances", user_id)
    cache_service.clear("credit_balances")
"""

import threading
from typing import Any, Hashable, Optional

from cachetools import TTLCache


class _CacheNamespace:
    """Internal wrapper around a single TTLCache instance.

    Not part of the public API — consumers interact with
    CacheService methods instead.
    """

    __slots__ = ("name", "_cache")

    def __init__(self, name: str, cache: TTLCache) -> None:  # type: ignore[type-arg]
        self.name = name
        self._cache: TTLCache = cache  # type: ignore[type-arg]

    def get(self, key: Hashable, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: Hashable, value: Any) -> None:
        self._cache[key] = value

    def delete(self, key: Hashable) -> Any:
        return self._cache.pop(key, None)

    def has(self, key: Hashable) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()

    def delete_many(self, keys: list[Hashable]) -> int:
        deleted = 0
        for key in keys:
            if self._cache.pop(key, None) is not None:
                deleted += 1
        return deleted

    @property
    def size(self) -> int:
        return self._cache.currsize.__ceil__()

    @property
    def maxsize(self) -> int:
        return self._cache.maxsize.__ceil__()


class CacheService:
    """Factory, registry, and gateway for named TTL caches.

    All caching goes through this service so that cache lifecycle,
    introspection, and bulk operations are centralized.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._namespaces: dict[str, _CacheNamespace] = {}

    # ==================== Registration ====================

    def register(
        self,
        name: str,
        *,
        maxsize: int = 1024,
        ttl: float = 60,
    ) -> None:
        """Register a named cache namespace.

        Idempotent — calling with the same *name* a second time is a no-op.

        Args:
            name: Unique identifier for this cache (e.g. "credit_balances").
            maxsize: Maximum entries before LRU eviction kicks in.
            ttl: Seconds before an entry expires.
        """
        with self._lock:
            if name not in self._namespaces:
                cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)  # type: ignore[type-arg]
                self._namespaces[name] = _CacheNamespace(name, cache)

    # ==================== Key-level operations ====================

    def _resolve(self, namespace: str) -> _CacheNamespace:
        """Return the namespace or raise if not registered."""
        ns = self._namespaces.get(namespace)
        if ns is None:
            raise KeyError(
                f"Cache namespace '{namespace}' is not registered. "
                f"Call cache_service.register('{namespace}', ...) first."
            )
        return ns

    def get(self, namespace: str, key: Hashable, default: Any = None) -> Any:
        """Retrieve a cached value.

        Args:
            namespace: The registered cache name.
            key: The cache key to look up.
            default: Value to return if not found or expired.

        Returns:
            The cached value, or *default*.
        """
        return self._resolve(namespace).get(key, default)

    def set(self, namespace: str, key: Hashable, value: Any) -> None:
        """Store a value in the cache.

        Args:
            namespace: The registered cache name.
            key: The cache key.
            value: The value to cache.
        """
        self._resolve(namespace).set(key, value)

    def delete(self, namespace: str, key: Hashable) -> Any:
        """Remove a single key from the cache.

        Args:
            namespace: The registered cache name.
            key: The cache key to remove.

        Returns:
            The removed value, or None if the key was absent.
        """
        return self._resolve(namespace).delete(key)

    def has(self, namespace: str, key: Hashable) -> bool:
        """Check whether a key exists and has not expired.

        Args:
            namespace: The registered cache name.
            key: The cache key to check.

        Returns:
            True if the key is present and live.
        """
        return self._resolve(namespace).has(key)

    def delete_many(self, namespace: str, keys: list[Hashable]) -> int:
        """Remove multiple keys from a namespace.

        Args:
            namespace: The registered cache name.
            keys: The cache keys to remove.

        Returns:
            Number of keys that were actually deleted.
        """
        return self._resolve(namespace).delete_many(keys)

    # ==================== Namespace-level operations ====================

    def clear(self, namespace: str) -> bool:
        """Clear all entries in a specific namespace.

        Returns True if the namespace existed and was cleared,
        False if no namespace with that name was found.
        """
        ns = self._namespaces.get(namespace)
        if ns is not None:
            ns.clear()
            return True
        return False

    def clear_all(self) -> None:
        """Clear every registered cache namespace."""
        with self._lock:
            for ns in self._namespaces.values():
                ns.clear()

    # ==================== Introspection ====================

    @property
    def namespaces(self) -> list[str]:
        """List all registered namespace names."""
        return list(self._namespaces.keys())

    def stats(self) -> dict[str, dict[str, int]]:
        """Return size/maxsize for every registered namespace."""
        return {
            name: {"size": ns.size, "maxsize": ns.maxsize}
            for name, ns in self._namespaces.items()
        }

    def __repr__(self) -> str:
        return f"CacheService(namespaces={self.namespaces})"


# ==================== Module-level singleton ====================

cache_service = CacheService()
"""Global CacheService instance. Import and use this everywhere."""

