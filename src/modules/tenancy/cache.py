"""Tenant-scoped cache backed by Redis."""

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import redis.asyncio as redis

from src.config import settings
from src.modules.tenancy.constants import CACHE_PREFIX, CACHE_TTL_DEFAULT

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TenantCache:
    """Redis-backed cache with tenant-scoped key namespacing.

    All keys are prefixed with "tenant:{org_id}:" to ensure complete
    isolation between tenants. Supports TTL, bulk invalidation per tenant,
    and cached computation via get_or_set.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    def _make_key(self, organization_id: uuid.UUID, key: str) -> str:
        return f"{CACHE_PREFIX}:{organization_id}:{key}"

    async def get(self, organization_id: uuid.UUID, key: str) -> Any | None:
        """Get a cached value for the given tenant and key."""
        client = await self._get_redis()
        raw = await client.get(self._make_key(organization_id, key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(
        self,
        organization_id: uuid.UUID,
        key: str,
        value: Any,
        ttl: int = CACHE_TTL_DEFAULT,
    ) -> None:
        """Set a cached value with a TTL (in seconds)."""
        client = await self._get_redis()
        await client.set(
            self._make_key(organization_id, key),
            json.dumps(value, default=str),
            ex=ttl,
        )

    async def delete(self, organization_id: uuid.UUID, key: str) -> None:
        """Delete a specific cached key for a tenant."""
        client = await self._get_redis()
        await client.delete(self._make_key(organization_id, key))

    async def invalidate_tenant(self, organization_id: uuid.UUID) -> int:
        """Delete all cached keys for the given tenant.

        Returns the number of keys deleted.
        """
        client = await self._get_redis()
        pattern = f"{CACHE_PREFIX}:{organization_id}:*"
        deleted_count = 0
        async for batch_keys in client.scan_iter(match=pattern, count=100):
            await client.delete(batch_keys)
            deleted_count += 1
        return deleted_count

    async def get_or_set(
        self,
        organization_id: uuid.UUID,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int = CACHE_TTL_DEFAULT,
    ) -> T:
        """Return cached value if present, otherwise compute via factory, cache, and return.

        Args:
            organization_id: The tenant's organization ID.
            key: Cache key within the tenant namespace.
            factory: Async callable that produces the value on cache miss.
            ttl: Time-to-live in seconds.

        Returns:
            The cached or freshly computed value.
        """
        cached = await self.get(organization_id, key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(organization_id, key, value, ttl=ttl)
        return value
