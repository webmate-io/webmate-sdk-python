"""Shared utility models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping


@dataclass
class Dimension:
    width: int
    height: int

    def as_dict(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}


@dataclass
class Tag:
    name: str
    value: Any | None = None

    def as_json(self) -> dict[str, Any | None]:
        return {self.name: self.value}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "Tag":
        name, value = next(iter(payload.items()))
        return cls(name=name, value=value)


__all__ = ["Dimension", "Tag"]
