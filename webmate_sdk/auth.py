"""Authentication primitives for the Python webmate SDK."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthInfo:
    """Authentication payload mapping to ``WebmateAuthInfo`` in the Java SDK."""

    api_token: str
    email: Optional[str] = None

    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "webmate.api-token": self.api_token,
        }
        if self.email:
            headers["webmate.user"] = self.email
        return headers


__all__ = ["AuthInfo"]
