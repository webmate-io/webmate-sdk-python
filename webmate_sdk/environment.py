"""Runtime environment definitions."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin


DEFAULT_BASE_URL = "https://app.webmate.io/api/v1/"


@dataclass(frozen=True)
class WebmateEnvironment:
    """Container mirroring ``WebmateEnvironment`` from the Java SDK."""

    base_url: str = DEFAULT_BASE_URL

    def with_base_url(self, base_url: str) -> "WebmateEnvironment":
        return WebmateEnvironment(base_url=base_url.rstrip("/") + "/")

    def resolve(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))


__all__ = ["WebmateEnvironment", "DEFAULT_BASE_URL"]
