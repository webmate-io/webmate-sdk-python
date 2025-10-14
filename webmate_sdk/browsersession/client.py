"""Browser session facade."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from ..exceptions import WebmateApiError
from ..http import ApiClient, UriTemplate
from ..ids import ActionSpanId, BrowserSessionId, BrowserSessionStateId, TestRunId
from ..session import WebmateSession
from ..utils import to_jsonable
from .models import (
    BrowserSessionInfo,
    BrowserSessionScreenshotExtractionConfig,
    BrowserSessionStateExtractionConfig,
    FinishStoryActionAddArtifactData,
    StartStoryActionAddArtifactData,
)

DEFAULT_EXTRACTION_CONFIG = BrowserSessionStateExtractionConfig(
    extract_dom_state_data=True,
    screenshot_config=BrowserSessionScreenshotExtractionConfig(full_page=True, hide_fixed_elements=False),
)


class BrowserSessionClient:
    _CREATE_STATE = UriTemplate("/browsersession/{browserSessionId}/states", name="CreateBrowserSessionState")
    _ADD_ARTIFACT = UriTemplate("/browsersession/{expeditionId}/artifacts", name="AddBrowserSessionArtifact")
    _SESSION_INFO = UriTemplate("/browsersession/{browserSessionId}/info", name="BrowserSessionInfo")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)
        self._span_stack: Dict[str, List[ActionSpanId]] = {}

    # ------------------------------------------------------------------
    def get_browser_session_for_selenium_session(self, selenium_session_id: str) -> "BrowserSessionRef":
        browser_session_id = BrowserSessionId.parse(selenium_session_id)
        return BrowserSessionRef(browser_session_id, self)

    def create_state(
        self,
        browser_session_id: BrowserSessionId,
        matching_id: str,
        extraction_config: Optional[BrowserSessionStateExtractionConfig] = None,
    ) -> BrowserSessionStateId:
        payload = {
            "optMatchingId": matching_id,
            "extractionConfig": (extraction_config or DEFAULT_EXTRACTION_CONFIG).to_json(),
        }
        response = self._client.post(
            self._CREATE_STATE,
            path_params={"browserSessionId": str(browser_session_id)},
            json=payload,
        )
        data = _safe_json(response, allow_text=True)
        if isinstance(data, dict) and "id" in data:
            return BrowserSessionStateId.parse(data["id"])
        return BrowserSessionStateId.parse(data)

    def create_state_for_current(
        self,
        matching_id: str,
        extraction_config: Optional[BrowserSessionStateExtractionConfig] = None,
    ) -> BrowserSessionStateId:
        browser_session_id = self._session.get_only_associated_expedition()
        if not browser_session_id:
            raise WebmateApiError(
                "No browser session associated with this API session; call register_browser_session first"
            )
        return self.create_state(browser_session_id, matching_id, extraction_config)

    def start_action(
        self,
        browser_session_id: BrowserSessionId,
        action_name: str,
        *,
        associated_test_runs: Sequence[TestRunId] | None = None,
    ) -> ActionSpanId:
        span_id = ActionSpanId(uuid.uuid4())
        artifact = StartStoryActionAddArtifactData(action_name, span_id, associated_test_runs)
        self._client.post(
            self._ADD_ARTIFACT,
            path_params={"expeditionId": str(browser_session_id)},
            json=artifact.to_json(),
        )
        self._span_stack.setdefault(str(browser_session_id), []).append(span_id)
        return span_id

    def finish_action(
        self,
        browser_session_id: BrowserSessionId,
        message: Optional[str] = None,
    ) -> None:
        span_id = self._pop_span(browser_session_id)
        if not span_id:
            return
        artifact = FinishStoryActionAddArtifactData(span_id, success=True, message=message)
        self._client.post(
            self._ADD_ARTIFACT,
            path_params={"expeditionId": str(browser_session_id)},
            json=artifact.to_json(),
        )

    def finish_action_as_failure(
        self,
        browser_session_id: BrowserSessionId,
        error_message: str,
    ) -> None:
        span_id = self._pop_span(browser_session_id)
        if not span_id:
            return
        artifact = FinishStoryActionAddArtifactData(span_id, success=False, message=error_message)
        self._client.post(
            self._ADD_ARTIFACT,
            path_params={"expeditionId": str(browser_session_id)},
            json=artifact.to_json(),
        )

    def with_action(
        self,
        browser_session_id: BrowserSessionId,
        action_name: str,
        func: Callable[[ActionSpanId], None],
    ) -> None:
        span = self.start_action(browser_session_id, action_name)
        try:
            func(span)
        except Exception as exc:  # pragma: no cover - propagated to caller
            self.finish_action_as_failure(browser_session_id, str(exc))
            raise
        else:
            self.finish_action(browser_session_id)

    def get_browser_session_info(self, browser_session_id: BrowserSessionId) -> BrowserSessionInfo:
        response = self._client.get(self._SESSION_INFO, path_params={"browserSessionId": str(browser_session_id)})
        data = _safe_json(response)
        return BrowserSessionInfo.from_api(data)

    def terminate_browsersession(self, browser_session_id: BrowserSessionId) -> bool:
        # The Java SDK currently always returns false.
        return False

    # Internal helpers --------------------------------------------------
    def _pop_span(self, browser_session_id: BrowserSessionId) -> ActionSpanId | None:
        stack = self._span_stack.get(str(browser_session_id))
        if not stack:
            return None
        return stack.pop()


@dataclass
class BrowserSessionRef:
    browser_session_id: BrowserSessionId
    client: BrowserSessionClient

    def create_state(
        self,
        matching_id: str,
        extraction_config: Optional[BrowserSessionStateExtractionConfig] = None,
    ) -> BrowserSessionStateId:
        return self.client.create_state(self.browser_session_id, matching_id, extraction_config)

    def start_action(
        self,
        action_name: str,
        *,
        associated_test_runs: Sequence[TestRunId] | None = None,
    ) -> ActionSpanId:
        return self.client.start_action(self.browser_session_id, action_name, associated_test_runs=associated_test_runs)

    def finish_action(self, message: str | None = None) -> None:
        self.client.finish_action(self.browser_session_id, message)

    def finish_action_as_failure(self, error_message: str) -> None:
        self.client.finish_action_as_failure(self.browser_session_id, error_message)

    def with_action(self, action_name: str, func: Callable[[ActionSpanId], None]) -> None:
        self.client.with_action(self.browser_session_id, action_name, func)

    def get_browser_session_info(self) -> BrowserSessionInfo:
        return self.client.get_browser_session_info(self.browser_session_id)


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            return response.text.strip().strip('"')
        raise


__all__ = ["BrowserSessionClient", "BrowserSessionRef"]
