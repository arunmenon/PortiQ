"""VesselFinder AIS provider implementation."""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.config import settings
from src.modules.vessel.providers.base import AisProviderBase

logger = logging.getLogger(__name__)

# Retry config for VesselFinder API
_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_BASE_BACKOFF_SECONDS = 2.0


class VesselFinderProvider(AisProviderBase):
    def __init__(self) -> None:
        self.api_key = settings.vessel_finder_api_key
        self.base_url = settings.vessel_finder_base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with exponential backoff for retryable errors."""
        client = await self._get_client()
        kwargs.setdefault("params", {})
        kwargs["params"]["userkey"] = self.api_key

        last_exception: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.request(method, path, **kwargs)
                if response.status_code < 400:
                    return response
                if response.status_code not in _RETRY_STATUSES or attempt >= _MAX_RETRIES:
                    response.raise_for_status()
                delay = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "VesselFinder %s %s returned %d, retrying in %.1fs (attempt %d/%d)",
                    method, path, response.status_code, delay, attempt + 1, _MAX_RETRIES,
                )
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError:
                raise
            except httpx.RequestError as exc:
                last_exception = exc
                if attempt >= _MAX_RETRIES:
                    raise
                delay = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "VesselFinder %s %s request error: %s, retrying in %.1fs",
                    method, path, exc, delay,
                )
                await asyncio.sleep(delay)

        if last_exception:
            raise last_exception
        raise RuntimeError("Max retries exceeded for VesselFinder request")

    async def get_vessel_position(self, imo_number: str) -> dict | None:
        response = await self._request_with_retry(
            "GET", "/vessels", params={"imo": imo_number},
        )
        data = response.json()
        if not data:
            return None
        vessel = data[0] if isinstance(data, list) else data
        return {
            "latitude": vessel.get("LAT"),
            "longitude": vessel.get("LON"),
            "speed_knots": vessel.get("SPEED"),
            "course": vessel.get("COURSE"),
            "heading": vessel.get("HEADING"),
            "navigation_status": vessel.get("NAVSTAT"),
            "recorded_at": vessel.get("TIMESTAMP"),
        }

    async def get_vessel_eta(self, imo_number: str) -> dict | None:
        response = await self._request_with_retry(
            "GET", "/expectedArrivals", params={"imo": imo_number},
        )
        data = response.json()
        if not data:
            return None
        arrival = data[0] if isinstance(data, list) else data
        return {
            "port_code": arrival.get("LOCODE"),
            "port_name": arrival.get("PORT_NAME"),
            "eta": arrival.get("ETA"),
            "distance_nm": arrival.get("DISTANCE_REMAINING"),
        }

    async def get_port_arrivals(self, port_code: str) -> list[dict]:
        response = await self._request_with_retry(
            "GET", "/expectedArrivals", params={"locode": port_code},
        )
        data = response.json()
        if not data:
            return []
        arrivals = data if isinstance(data, list) else [data]
        return [
            {
                "imo_number": a.get("IMO"),
                "vessel_name": a.get("NAME"),
                "eta": a.get("ETA"),
                "distance_nm": a.get("DISTANCE_REMAINING"),
                "port_code": port_code,
            }
            for a in arrivals
        ]

    async def get_vessel_track(self, imo_number: str, hours: int = 2160) -> list[dict]:
        response = await self._request_with_retry(
            "GET", "/vessels", params={"imo": imo_number, "interval": hours},
        )
        data = response.json()
        if not data:
            return []
        track_data = data if isinstance(data, list) else [data]
        return [
            {
                "latitude": point.get("LAT"),
                "longitude": point.get("LON"),
                "speed_knots": point.get("SPEED"),
                "course": point.get("COURSE"),
                "heading": point.get("HEADING"),
                "recorded_at": point.get("TIMESTAMP"),
            }
            for point in track_data
        ]

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get(
                "/vessels",
                params={"userkey": self.api_key, "imo": "0000000"},
            )
            return response.status_code in (200, 404)
        except Exception:
            logger.exception("VesselFinder health check failed")
            return False
