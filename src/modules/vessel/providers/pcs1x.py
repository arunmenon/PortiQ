"""PCS1x Indian port community system AIS provider implementation."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from src.config import settings
from src.modules.vessel.constants import PCS1X_PORTS, PCS1X_RETRY_POLICIES
from src.modules.vessel.providers.base import AisProviderBase

logger = logging.getLogger(__name__)


class Pcs1xProvider(AisProviderBase):
    def __init__(self) -> None:
        self.client_id = settings.pcs1x_client_id
        self.client_secret = settings.pcs1x_client_secret
        self.base_url = settings.pcs1x_base_url
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._client

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        client = await self._get_client()
        response = await client.post(
            "/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        response.raise_for_status()
        token_data = response.json()
        self._token = token_data["access_token"]
        self._token_expires_at = time.time() + token_data.get("expires_in", 3600)
        return self._token

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        client = await self._get_client()
        token = await self._ensure_token()
        kwargs.setdefault("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {token}"

        max_attempts = max(p["max_retries"] for p in PCS1X_RETRY_POLICIES.values()) + 1
        last_exception: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = await client.request(method, path, **kwargs)
                if response.status_code < 400:
                    return response
                policy = PCS1X_RETRY_POLICIES.get(response.status_code)
                if policy is None:
                    response.raise_for_status()
                if attempt >= policy["max_retries"]:
                    response.raise_for_status()
                delay = self._compute_delay(policy, attempt)
                logger.warning(
                    "PCS1x %s %s returned %d, retrying in %.1fs (attempt %d)",
                    method, path, response.status_code, delay, attempt + 1,
                )
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError:
                raise
            except Exception as exc:
                last_exception = exc
                await asyncio.sleep(2)

        if last_exception:
            raise last_exception
        raise httpx.HTTPStatusError(
            "Max retries exceeded", request=httpx.Request(method, path), response=response  # type: ignore[possibly-undefined]
        )

    @staticmethod
    def _compute_delay(policy: dict, attempt: int) -> float:
        base_delay = policy["delay_seconds"]
        strategy = policy["strategy"]
        if strategy == "exponential":
            return base_delay * (2 ** attempt)
        elif strategy == "linear":
            return base_delay * (attempt + 1)
        else:  # fixed
            return base_delay

    async def get_vessel_position(self, imo_number: str) -> dict | None:
        response = await self._request_with_retry(
            "GET", "/api/v1/vessels/position", params={"imo": imo_number}
        )
        data = response.json()
        if not data or not data.get("data"):
            return None
        vessel = data["data"]
        return {
            "latitude": vessel.get("latitude"),
            "longitude": vessel.get("longitude"),
            "speed_knots": vessel.get("speed"),
            "course": vessel.get("course"),
            "heading": vessel.get("heading"),
            "navigation_status": vessel.get("nav_status"),
            "recorded_at": vessel.get("timestamp"),
        }

    async def get_vessel_eta(self, imo_number: str) -> dict | None:
        response = await self._request_with_retry(
            "GET", "/api/v1/vessels/eta", params={"imo": imo_number}
        )
        data = response.json()
        if not data or not data.get("data"):
            return None
        eta_data = data["data"]
        return {
            "port_code": eta_data.get("port_code"),
            "port_name": eta_data.get("port_name"),
            "eta": eta_data.get("eta"),
            "distance_nm": eta_data.get("distance_remaining"),
            "eta_confidence": eta_data.get("confidence"),
        }

    async def get_port_arrivals(self, port_code: str) -> list[dict]:
        if port_code not in PCS1X_PORTS:
            return []
        response = await self._request_with_retry(
            "GET", "/api/v1/ports/arrivals", params={"locode": port_code}
        )
        data = response.json()
        if not data or not data.get("data"):
            return []
        return [
            {
                "imo_number": a.get("imo"),
                "vessel_name": a.get("vessel_name"),
                "eta": a.get("eta"),
                "distance_nm": a.get("distance_remaining"),
                "port_code": port_code,
                "berth": a.get("berth"),
            }
            for a in data["data"]
        ]

    async def get_vessel_track(self, imo_number: str, hours: int = 2160) -> list[dict]:
        response = await self._request_with_retry(
            "GET",
            "/api/v1/vessels/track",
            params={"imo": imo_number, "hours": hours},
        )
        data = response.json()
        if not data or not data.get("data"):
            return []
        return [
            {
                "latitude": point.get("latitude"),
                "longitude": point.get("longitude"),
                "speed_knots": point.get("speed"),
                "course": point.get("course"),
                "heading": point.get("heading"),
                "recorded_at": point.get("timestamp"),
            }
            for point in data["data"]
        ]

    async def health_check(self) -> bool:
        try:
            await self._ensure_token()
            return True
        except Exception:
            logger.exception("PCS1x health check failed")
            return False
