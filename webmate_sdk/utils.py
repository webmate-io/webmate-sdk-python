"""Shared JSON helpers."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return {k: to_jsonable(v) for k, v in asdict(value).items() if v is not None}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items() if v is not None}
    if hasattr(value, "to_json"):
        return value.to_json()
    return value


__all__ = ["to_jsonable"]
