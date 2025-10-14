"""SDK specific exceptions."""
from __future__ import annotations

from typing import Any, Iterable, Optional


class WebmateApiError(RuntimeError):
    """Generic error raised for failed HTTP interactions."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        details = [super().__repr__()]
        if self.status_code is not None:
            details.append(f"status_code={self.status_code}")
        if self.payload is not None:
            details.append(f"payload={self.payload!r}")
        return "WebmateApiError(" + ", ".join(details) + ")"


class WebmateTimeoutError(WebmateApiError):
    """Raised when async operations exceed the configured timeout."""


__all__ = ["WebmateApiError", "WebmateTimeoutError"]
