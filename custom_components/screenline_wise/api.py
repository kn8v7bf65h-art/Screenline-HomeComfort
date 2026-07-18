"""Local API client for ScreenLine WISE hubs."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .const import API_MOVE, API_POSITION, API_ROOMS, API_TILT, DEFAULT_PORT


class ScreenLineError(Exception):
    """Base exception for ScreenLine API errors."""


class ScreenLineAuthError(ScreenLineError):
    """Raised when authentication fails."""


class ScreenLineConnectionError(ScreenLineError):
    """Raised when the hub cannot be reached."""


class ScreenLineApiError(ScreenLineError):
    """Raised for unexpected API responses."""


class ScreenLineApiClient:
    """Communicate with a ScreenLine WISE hub over its local HTTPS API."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        token: str,
        *,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self._host = host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        self._token = token.strip().removeprefix("Bearer ").strip()
        self._verify_ssl = verify_ssl
        self._timeout = ClientTimeout(total=15)

    @property
    def host(self) -> str:
        """Return configured hub host."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return local API base URL."""
        host = self._host
        if ":" not in host:
            host = f"{host}:{DEFAULT_PORT}"
        return f"https://{host}"

    @property
    def headers(self) -> dict[str, str]:
        """Return request headers."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: ClientResponse) -> Any:
        if response.status == 401:
            raise ScreenLineAuthError("The hub rejected the Bearer token")
        if response.status >= 400:
            body = await response.text()
            raise ScreenLineApiError(
                f"ScreenLine API returned HTTP {response.status}: {body[:300]}"
            )
        if response.status == 204:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type.lower():
            return await response.json(content_type=None)
        body = await response.text()
        return body or None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                json=json,
                ssl=self._verify_ssl,
                timeout=self._timeout,
            ) as response:
                return await self._handle_response(response)
        except ScreenLineError:
            raise
        except (asyncio.TimeoutError, ClientError) as err:
            raise ScreenLineConnectionError(
                f"Unable to communicate with ScreenLine hub at {self.base_url}"
            ) from err

    async def async_get_plant(self) -> dict[str, Any]:
        """Return plant, rooms and blinds."""
        result = await self._request("GET", API_ROOMS)
        if not isinstance(result, dict):
            raise ScreenLineApiError("The hub returned an invalid plant response")
        return result

    async def async_set_position(
        self,
        room_id: int,
        blind_ids: list[int],
        coverage: int,
        inclination: int,
    ) -> Any:
        """Set exact coverage and inclination."""
        payload = {
            "coverage": max(0, min(100, int(coverage))),
            "inclination": max(-75, min(75, int(inclination))),
            "blindIds": blind_ids,
        }
        return await self._request(
            "POST", API_POSITION.format(room_id=room_id), json=payload
        )

    async def async_move(
        self, room_id: int, blind_ids: list[int], movement_type: str
    ) -> Any:
        """Start or stop blind movement."""
        payload = {"movementType": movement_type.upper(), "blindIds": blind_ids}
        return await self._request(
            "POST", API_MOVE.format(room_id=room_id), json=payload
        )

    async def async_tilt_step(
        self, room_id: int, blind_ids: list[int], tilt_type: str
    ) -> Any:
        """Increment or decrement blind tilt by one model step."""
        payload = {"tiltType": tilt_type.upper(), "blindIds": blind_ids}
        return await self._request(
            "POST", API_TILT.format(room_id=room_id), json=payload
        )
