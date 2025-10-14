"""Job Engine helper models."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from ..ids import JobId, JobRunId, TestExecutionId, TestRunId, UserId


@dataclass(frozen=True)
class JobConfigName:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class PortName:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class WMDataType:
    identifier: str

    def __str__(self) -> str:
        return self.identifier

    def to_json(self) -> str:
        return self.identifier


@dataclass
class WMValue:
    data_type: WMDataType
    value: Any

    def to_json(self) -> dict[str, Any]:
        return {"type": self.data_type.identifier, "data": self.value}


@dataclass
class JobRunSummary:
    id: JobRunId
    state: str
    creator: Optional[UserId]
    created: Optional[dt.datetime]
    started: Optional[dt.datetime]
    finished: Optional[dt.datetime]
    last_update: Optional[dt.datetime]
    failure_message: Optional[str]
    input_ports: Mapping[str, Any]
    test_execution_id: Optional[TestExecutionId]
    test_run_id: Optional[TestRunId]
    summary_information: Mapping[str, Any]

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "JobRunSummary":
        return cls(
            id=JobRunId.parse(payload.get("id")),
            state=str(payload.get("state")),
            creator=UserId.parse(payload["creator"]) if payload.get("creator") else None,
            created=_parse_datetime(payload.get("creationTime")),
            started=_parse_datetime(payload.get("startTime")),
            finished=_parse_datetime(payload.get("endTime")),
            last_update=_parse_datetime(payload.get("lastUpdateTime")),
            failure_message=payload.get("failureMessage"),
            input_ports=payload.get("inputPorts", {}),
            test_execution_id=TestExecutionId.parse(payload["testExecutionId"]) if payload.get("testExecutionId") else None,
            test_run_id=TestRunId.parse(payload["testRunId"]) if payload.get("testRunId") else None,
            summary_information=payload.get("summaryInformation", {}),
        )


def _parse_datetime(value: Any) -> Optional[dt.datetime]:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


__all__ = [
    "JobConfigName",
    "PortName",
    "WMDataType",
    "WMValue",
    "JobRunSummary",
]
