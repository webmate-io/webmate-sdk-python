"""Identifier helper types."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Type, TypeVar, Union


T = TypeVar("T", bound="Identifier")
IdentifierInput = Union[uuid.UUID, str, "Identifier"]


@dataclass(frozen=True)
class Identifier:
    """Lightweight UUID wrapper aligning with Java value objects."""

    value: uuid.UUID

    def __init__(self, value: IdentifierInput):
        object.__setattr__(self, "value", _coerce_uuid(value))

    def __str__(self) -> str:
        return str(self.value)

    def to_json(self) -> str:
        return str(self.value)

    @classmethod
    def parse(cls: Type[T], value: IdentifierInput) -> T:
        return cls(value)


def _coerce_uuid(value: IdentifierInput) -> uuid.UUID:
    if isinstance(value, Identifier):
        return value.value
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


class ProjectId(Identifier):
    pass


class BrowserSessionId(Identifier):
    pass


class BrowserSessionStateId(Identifier):
    pass


class FactSessionId(Identifier):
    pass


class JobId(Identifier):
    pass


class JobRunId(Identifier):
    pass


class ArtifactId(Identifier):
    pass


class ScreenshotId(Identifier):
    pass


class DeviceId(Identifier):
    pass


class TestRunId(Identifier):
    pass


class TestExecutionId(Identifier):
    pass


class TestSessionId(Identifier):
    pass


class TestTemplateId(Identifier):
    pass


class UserId(Identifier):
    pass


class PackageId(Identifier):
    pass


class ImageId(Identifier):
    pass


class BlobId(Identifier):
    pass


class ApplicationModelId(Identifier):
    pass


class ActionSpanId(Identifier):
    pass


class WebmateSeleniumSessionId(Identifier):
    pass


__all__ = [
    "Identifier",
    "ProjectId",
    "BrowserSessionId",
    "BrowserSessionStateId",
    "FactSessionId",
    "JobId",
    "JobRunId",
    "ArtifactId",
    "ScreenshotId",
    "DeviceId",
    "TestRunId",
    "TestExecutionId",
    "TestSessionId",
    "TestTemplateId",
    "UserId",
    "PackageId",
    "ImageId",
    "BlobId",
    "ApplicationModelId",
    "ActionSpanId",
    "WebmateSeleniumSessionId",
]
