"""Provider factory — select the right AIS adapter for a given context."""

from __future__ import annotations

from src.models.enums import AisProvider
from src.modules.vessel.constants import PCS1X_PORTS
from src.modules.vessel.providers.base import AisProviderBase
from src.modules.vessel.providers.pcs1x import Pcs1xProvider
from src.modules.vessel.providers.vessel_finder import VesselFinderProvider

_instances: dict[AisProvider, AisProviderBase] = {}


def get_provider(provider: AisProvider) -> AisProviderBase:
    if provider not in _instances:
        if provider == AisProvider.VESSEL_FINDER:
            _instances[provider] = VesselFinderProvider()
        elif provider == AisProvider.PCS1X:
            _instances[provider] = Pcs1xProvider()
        else:
            raise ValueError(f"No adapter for provider: {provider}")
    return _instances[provider]


def get_provider_for_port(port_code: str) -> AisProviderBase:
    if port_code in PCS1X_PORTS:
        return get_provider(AisProvider.PCS1X)
    return get_provider(AisProvider.VESSEL_FINDER)


async def close_all_providers() -> None:
    """Close httpx clients on all cached providers.

    Must be called at the end of each asyncio.run() invocation in Celery tasks
    to prevent stale clients across event loop boundaries.
    """
    for provider in _instances.values():
        if hasattr(provider, "_client") and provider._client is not None:
            if not provider._client.is_closed:
                await provider._client.aclose()
            provider._client = None
