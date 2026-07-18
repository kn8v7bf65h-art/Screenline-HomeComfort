"""API clients for Pellini HomeComfort cloud and ScreenLine WISE Hub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import APP_NAME, APP_VERSION, CLOUD_BASE_URL, CLOUD_LOGIN_PATH, LOCAL_PORT


class ScreenLineError(Exception):
    """Base ScreenLine exception."""


class ScreenLineAuthError(ScreenLineError):
    """Authentication failed."""


class ScreenLineConnectionError(ScreenLineError):
    """Connection to cloud or hub failed."""


@dataclass(slots=True)
class RegisteredHub:
    """Cloud-registered WISE Hub."""

    hub_name: str
    plant_name: str
    is_master: bool
    is_admin: bool
    is_premium: bool
    connection_type: int | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegisteredHub":
        return cls(
            hub_name=str(data["hubName"]),
            plant_name=str(data.get("plantName", data["hubName"])),
            is_master=bool(data.get("isMaster", False)),
            is_admin=bool(data.get("isAdmin", False)),
            is_premium=bool(data.get("isPremium", False)),
            connection_type=data.get("connectionType"),
        )


class PelliniCloudClient:
    """Client for the Pellini HomeComfort account service."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    @staticmethod
    def _device_info() -> str:
        # The official app sends deviceInfo as a JSON string inside the JSON body.
        return json.dumps(
            {
                "appVersion": APP_VERSION,
                "brand": "Home Assistant",
                "buildNumber": "1",
                "systemName": "Home Assistant",
                "deviceId": "HomeAssistant",
                "systemVersion": "unknown",
                "buildId": "-",
                "isTablet": False,
                "device": "-",
            },
            separators=(",", ":"),
        )

    async def login(self, email: str, password: str) -> tuple[str, list[RegisteredHub], bool]:
        payload = {
            "email": email,
            "password": password,
            "deviceInfo": self._device_info(),
            "deviceDateHour": datetime.now().strftime("%Y%m%d%H%M%S"),
            "appType": APP_NAME,
        }
        try:
            response = await self._session.post(
                f"{CLOUD_BASE_URL}{CLOUD_LOGIN_PATH}",
                json=payload,
                timeout=20,
            )
            if response.status in (400, 401, 403):
                body = await response.text()
                raise ScreenLineAuthError(body or "Invalid credentials")
            response.raise_for_status()
            data = await response.json()
        except ScreenLineAuthError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise ScreenLineConnectionError(str(err)) from err

        token = data.get("loginToken")
        if not token:
            raise ScreenLineAuthError("Cloud response did not contain a loginToken")

        hubs = [RegisteredHub.from_dict(item) for item in data.get("registeredHubs", [])]
        return str(token), hubs, bool(data.get("isTest", False))


class WiseHubClient:
    """Client for a local ScreenLine WISE Hub."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        token: str,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self._host = host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        self._token = token.removeprefix("Bearer ").strip()
        self._verify_ssl = verify_ssl

    def set_token(self, token: str) -> None:
        self._token = token.removeprefix("Bearer ").strip()

    @property
    def base_url(self) -> str:
        return f"https://{self._host}:{LOCAL_PORT}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = await self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                ssl=self._verify_ssl,
                timeout=20,
                **kwargs,
            )
            if response.status in (401, 403):
                raise ScreenLineAuthError("WISE Hub rejected the token")
            response.raise_for_status()
            if response.status == 204:
                return None
            content_type = response.headers.get("Content-Type", "")
            if "json" in content_type:
                return await response.json()
            text = await response.text()
            return text or None
        except ScreenLineAuthError:
            raise
        except ClientResponseError as err:
            raise ScreenLineConnectionError(f"WISE Hub returned HTTP {err.status}") from err
        except (ClientError, TimeoutError, ValueError) as err:
            raise ScreenLineConnectionError(str(err)) from err

    async def get_rooms(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", "/api/plant/rooms?includeBlinds=true&includeGlasses=true"
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("rooms", "items", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
        raise ScreenLineConnectionError("Unexpected rooms response from WISE Hub")

    async def move(self, room_id: int | str, blind_id: int, movement_type: str) -> None:
        await self._request(
            "POST",
            f"/api/rooms/{room_id}/move",
            json={"movementType": movement_type, "blindIds": [blind_id]},
        )

    async def set_position(
        self,
        room_id: int | str,
        blind_id: int,
        coverage: int,
        inclination: int,
    ) -> None:
        await self._request(
            "POST",
            f"/api/rooms/{room_id}/position",
            json={
                "coverage": max(0, min(100, int(coverage))),
                "inclination": max(0, min(90, int(inclination))),
                "blindIds": [blind_id],
            },
        )

    async def tilt(self, room_id: int | str, blind_id: int, tilt_type: str) -> None:
        await self._request(
            "POST",
            f"/api/rooms/{room_id}/tilt",
            json={"tiltType": tilt_type, "blindIds": [blind_id]},
        )
