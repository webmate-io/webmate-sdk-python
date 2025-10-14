"""Selenium subsystem facade."""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional

from ..http import ApiClient, UriTemplate
from ..ids import BrowserSessionId, ProjectId, WebmateSeleniumSessionId
from ..session import WebmateSession


class SeleniumServiceClient:
    _GET_SESSION = UriTemplate("/seleniumsession/{sessionId}", name="GetSeleniumSession")
    _GET_SESSION_FOR_BROWSER_SESSION = UriTemplate("/seleniumsession/", name="GetSeleniumSessionForBrowserSession")
    _CAPABILITIES = UriTemplate("/projects/{projectId}/selenium/capabilities", name="GetSeleniumCapabilities")
    _SESSIONS = UriTemplate("/projects/{projectId}/seleniumsession", name="GetSeleniumSessions")
    _SESSION_IDS = UriTemplate("/projects/{projectId}/seleniumsession/id", name="GetSeleniumSessionIds")
    _STOP_SESSION = UriTemplate("/seleniumsession/{sessionId}/stop", name="StopSeleniumSession")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    def get_session(self, session_id: WebmateSeleniumSessionId | str) -> dict | None:
        response = self._client.get(self._GET_SESSION, path_params={"sessionId": str(session_id)})
        return _safe_json(response)

    def get_session_for_browser_session(self, browser_session_id: BrowserSessionId | str) -> dict | None:
        response = self._client.get(
            self._GET_SESSION_FOR_BROWSER_SESSION,
            query={"expeditionId": str(browser_session_id)},
        )
        return _safe_json(response)

    def get_capabilities(self, project_id: ProjectId | None = None) -> List[dict]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._CAPABILITIES, path_params={"projectId": str(project)})
        data = _safe_json(response)
        return list(data) if isinstance(data, list) else []

    def list_sessions(
        self,
        project_id: ProjectId | None = None,
        *,
        after: WebmateSeleniumSessionId | str | None = None,
        count: int | None = None,
        state: str | None = None,
    ) -> List[dict]:
        project = project_id or self._session.require_project()
        query = {
            "after": str(after) if after else None,
            "count": str(count) if count is not None else None,
            "state": state,
        }
        response = self._client.get(self._SESSIONS, path_params={"projectId": str(project)}, query=query)
        data = _safe_json(response)
        return list(data) if isinstance(data, list) else []

    def list_session_ids(
        self,
        project_id: ProjectId | None = None,
        *,
        after: WebmateSeleniumSessionId | str | None = None,
        count: int | None = None,
        state: str | None = None,
    ) -> List[WebmateSeleniumSessionId]:
        project = project_id or self._session.require_project()
        query = {
            "after": str(after) if after else None,
            "count": str(count) if count is not None else None,
            "state": state,
        }
        response = self._client.get(self._SESSION_IDS, path_params={"projectId": str(project)}, query=query)
        data = _safe_json(response)
        if isinstance(data, list):
            return [WebmateSeleniumSessionId.parse(item) for item in data]
        return []

    def stop_session(self, session_id: WebmateSeleniumSessionId | str) -> None:
        self._client.post(self._STOP_SESSION, path_params={"sessionId": str(session_id)})


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


__all__ = ["SeleniumServiceClient"]
