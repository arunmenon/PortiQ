"""Abstract base class for AIS data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AisProviderBase(ABC):
    @abstractmethod
    async def get_vessel_position(self, imo_number: str) -> dict | None:
        """Return latest position for a vessel, or None if unavailable."""

    @abstractmethod
    async def get_vessel_eta(self, imo_number: str) -> dict | None:
        """Return ETA information for a vessel, or None if unavailable."""

    @abstractmethod
    async def get_port_arrivals(self, port_code: str) -> list[dict]:
        """Return list of expected/actual arrivals at a port."""

    @abstractmethod
    async def get_vessel_track(self, imo_number: str, hours: int = 2160) -> list[dict]:
        """Return historical track positions (default 90 days)."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider API is reachable and authenticated."""
