"""Image subsystem facade."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..http import ApiClient, UriTemplate
from ..ids import ScreenshotId
from ..session import WebmateSession


@dataclass
class ScreenshotMetadata:
    width: int
    height: int

    @classmethod
    def from_api(cls, payload: dict) -> "ScreenshotMetadata":
        return cls(width=payload.get("width", 0), height=payload.get("height", 0))


class ImageClient:
    _GET_METADATA = UriTemplate("/images/{screenshotId}/meta", name="GetScreenshotMetadata")
    _GET_SCREENSHOT = UriTemplate("/images/{screenshotId}", name="GetScreenshot")

    def __init__(self, session: WebmateSession) -> None:
        self._client = ApiClient(session.auth, session.environment)

    def get_screenshot_metadata(self, screenshot_id: ScreenshotId) -> Optional[ScreenshotMetadata]:
        response = self._client.get(self._GET_METADATA, path_params={"screenshotId": str(screenshot_id)})
        payload = _safe_json(response)
        if not isinstance(payload, dict):
            return None
        return ScreenshotMetadata.from_api(payload)

    def get_screenshot(self, screenshot_id: ScreenshotId) -> Optional[bytes]:
        response = self._client.get(self._GET_SCREENSHOT, path_params={"screenshotId": str(screenshot_id)})
        return response.content if response.content else None


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


__all__ = ["ImageClient", "ScreenshotMetadata"]
