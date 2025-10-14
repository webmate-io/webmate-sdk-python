"""Browser session related dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence
from urllib.parse import urlparse

from ..common import Dimension
from ..ids import ActionSpanId, BrowserSessionId, BrowserSessionStateId, TestRunId
from ..utils import to_jsonable


# ---------------------------------------------------------------------------
# Browser and platform primitives
# ---------------------------------------------------------------------------


@dataclass
class Platform:
    platform_type: str
    platform_version: str
    platform_architecture: Optional[str] = None

    @classmethod
    def from_legacy(cls, value: str) -> "Platform":
        parts = value.split("_")
        if len(parts) == 2:
            return cls(parts[0], parts[1])
        if len(parts) == 3:
            return cls(parts[0], parts[1], parts[2])
        raise ValueError(f"Invalid platform string: {value}")

    def to_json(self) -> Mapping[str, Optional[str]]:
        payload: dict[str, Optional[str]] = {
            "platformType": self.platform_type,
            "platformVersion": self.platform_version,
        }
        if self.platform_architecture:
            payload["platformArchitecture"] = self.platform_architecture
        return payload


@dataclass
class Browser:
    browser_type: str
    version: Optional[str] = None
    platform: Optional[Platform | str] = None
    properties: Optional[Mapping[str, Any]] = None

    def to_json(self) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "browserType": self.browser_type,
            "version": self.version,
        }
        if self.platform:
            payload["platform"] = (
                self.platform.to_json() if isinstance(self.platform, Platform) else self.platform
            )
        if self.properties:
            payload["properties"] = self.properties
        return {k: v for k, v in payload.items() if v is not None}


# ---------------------------------------------------------------------------
# Expedition specs
# ---------------------------------------------------------------------------


@dataclass
class BrowserSpecification:
    browser: Browser
    viewport_dimensions: Optional[Dimension] = None
    use_proxy: bool = False

    def to_json(self) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "type": "BrowserSpecification",
            "browser": self.browser.to_json(),
            "useProxy": self.use_proxy,
        }
        if self.viewport_dimensions:
            payload["viewportDimensions"] = self.viewport_dimensions.as_dict()
        return payload


@dataclass
class DriverSpecification:
    type_name: str

    def to_json(self) -> Mapping[str, Any]:
        return {"type": self.type_name}


@dataclass
class URLListDriverSpecification(DriverSpecification):
    urls: Sequence[str]

    def __init__(self, urls: Sequence[str | Any]):
        normalized = [str(url) for url in urls]
        super().__init__("URLListDriverSpecification")
        self.urls = normalized

    def to_json(self) -> Mapping[str, Any]:
        payload = super().to_json()
        payload["urls"] = list(self.urls)
        return payload


@dataclass
class ExpeditionSpec:
    type_name: str

    def to_json(self) -> Mapping[str, Any]:
        return {"type": self.type_name}


@dataclass
class LiveExpeditionSpec(ExpeditionSpec):
    driver_spec: DriverSpecification
    vehicle_spec: BrowserSpecification

    def __init__(self, driver_spec: DriverSpecification, vehicle_spec: BrowserSpecification):
        super().__init__("LiveExpeditionSpec")
        self.driver_spec = driver_spec
        self.vehicle_spec = vehicle_spec

    def to_json(self) -> Mapping[str, Any]:
        payload = super().to_json()
        payload["driverSpec"] = self.driver_spec.to_json()
        payload["vehicleSpec"] = self.vehicle_spec.to_json()
        return payload


@dataclass
class OfflineExpeditionSpec(ExpeditionSpec):
    snapshot_id: str

    def __init__(self, snapshot_id: str):
        super().__init__("OfflineExpeditionSpec")
        self.snapshot_id = snapshot_id

    def to_json(self) -> Mapping[str, Any]:
        payload = super().to_json()
        payload["snapshotId"] = self.snapshot_id
        return payload


# ---------------------------------------------------------------------------
# State extraction configs
# ---------------------------------------------------------------------------


@dataclass
class FactType:
    artifact_type: Optional[str] = None
    finding_type: Optional[str] = None

    @classmethod
    def from_artifact(cls, artifact_type: str) -> "FactType":
        return cls(artifact_type=artifact_type)

    @classmethod
    def from_finding(cls, finding_type: str) -> "FactType":
        return cls(finding_type=finding_type)

    def to_json(self) -> Mapping[str, str]:
        if self.artifact_type:
            return {"artifactType": self.artifact_type}
        if self.finding_type:
            return {"findingType": self.finding_type}
        raise ValueError("FactType requires either artifact_type or finding_type")


@dataclass
class FactParams:
    value: Mapping[str, Any]

    def to_json(self) -> Mapping[str, Any]:
        return self.value


@dataclass
class FactRequest:
    fact_type: FactType
    params: Optional[FactParams] = None

    def to_json(self) -> Mapping[str, Any]:
        payload: dict[str, Any] = {"factType": self.fact_type.to_json()}
        if self.params:
            payload["params"] = self.params.to_json()
        return payload


@dataclass
class BrowserSessionScreenshotExtractionConfig:
    full_page: bool
    hide_fixed_elements: bool
    use_translate_y_scroll_strategy: bool = False

    def to_json(self) -> Mapping[str, Any]:
        return {
            "fullPage": self.full_page,
            "hideFixedElements": self.hide_fixed_elements,
            "useTranslateYScrollStrategy": self.use_translate_y_scroll_strategy,
        }


@dataclass
class BrowserSessionWarmUpConfig:
    page_warm_up_scroll_by: int
    page_warm_up_scroll_delay: int
    page_warm_up_max_scrolls: int

    def to_json(self) -> Mapping[str, int]:
        return {
            "pageWarmUpScrollBy": self.page_warm_up_scroll_by,
            "pageWarmUpScrollDelay": self.page_warm_up_scroll_delay,
            "pageWarmUpMaxScrolls": self.page_warm_up_max_scrolls,
        }


@dataclass
class BrowserSessionStateExtractionConfig:
    state_id: Optional[BrowserSessionStateId] = None
    extraction_delay: Optional[int] = None
    extraction_cooldown: Optional[int] = None
    viewport_dimension: Optional[Dimension] = None
    max_additional_waiting_time: Optional[int] = None
    extract_dom_state_data: Optional[bool] = None
    requested_facts: Optional[Sequence[FactRequest]] = None
    screenshot_config: Optional[BrowserSessionScreenshotExtractionConfig] = None
    warm_up_config: Optional[BrowserSessionWarmUpConfig] = None

    def to_json(self) -> Mapping[str, Any]:
        payload: dict[str, Any] = {}
        if self.state_id:
            payload["stateId"] = str(self.state_id)
        if self.extraction_delay is not None:
            payload["extractionDelay"] = self.extraction_delay
        if self.extraction_cooldown is not None:
            payload["extractionCooldown"] = self.extraction_cooldown
        if self.viewport_dimension:
            payload["optViewportDimension"] = self.viewport_dimension.as_dict()
        if self.max_additional_waiting_time is not None:
            payload["maxAdditionWaitingTimeForStateExtraction"] = self.max_additional_waiting_time
        if self.extract_dom_state_data is not None:
            payload["extractDomStateData"] = self.extract_dom_state_data
        if self.requested_facts:
            payload["requestedFacts"] = [fact.to_json() for fact in self.requested_facts]
        if self.screenshot_config:
            payload["screenShotConfig"] = self.screenshot_config.to_json()
        if self.warm_up_config:
            payload["warmUpConfig"] = self.warm_up_config.to_json()
        return payload


@dataclass
class BrowserSessionInfo:
    id: BrowserSessionId
    start: Optional[str] = None
    end: Optional[str] = None
    device_id: Optional[str] = None

    @classmethod
    def from_api(cls, payload: Mapping[str, Any]) -> "BrowserSessionInfo":
        return cls(
            id=BrowserSessionId.parse(payload.get("id")),
            start=payload.get("optStart"),
            end=payload.get("optEnd"),
            device_id=payload.get("optDeviceId"),
        )


@dataclass
class StartStoryActionAddArtifactData:
    name: str
    span_id: ActionSpanId
    associated_test_runs: Sequence[TestRunId] | None = None

    def to_json(self) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "artifactType": "Action.ActionStart",
            "data": {
                "name": self.name,
                "actionType": "story",
                "spanId": str(self.span_id),
            },
        }
        if self.associated_test_runs:
            payload["associatedTestRuns"] = [str(run) for run in self.associated_test_runs]
        return payload


@dataclass
class FinishStoryActionAddArtifactData:
    span_id: ActionSpanId
    success: bool
    message: Optional[str] = None

    def to_json(self) -> Mapping[str, Any]:
        data: dict[str, Any] = {"spanId": str(self.span_id)}
        if self.success:
            data["result"] = {"success": True, **({"message": self.message} if self.message else {})}
        else:
            error: dict[str, Any] = {"errorMessage": self.message or "Action failed"}
            data["error"] = error
        return {"artifactType": "Action.ActionFinish", "data": data}


__all__ = [
    "Browser",
    "Platform",
    "BrowserSpecification",
    "DriverSpecification",
    "URLListDriverSpecification",
    "LiveExpeditionSpec",
    "OfflineExpeditionSpec",
    "BrowserSessionStateExtractionConfig",
    "BrowserSessionScreenshotExtractionConfig",
    "BrowserSessionWarmUpConfig",
    "FactType",
    "FactParams",
    "FactRequest",
    "BrowserSessionInfo",
    "StartStoryActionAddArtifactData",
    "FinishStoryActionAddArtifactData",
]
