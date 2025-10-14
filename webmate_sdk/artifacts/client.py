"""Artifact subsystem facade."""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence

from ..http import ApiClient, UriTemplate
from ..ids import ArtifactId, BrowserSessionId, ProjectId, TestRunId
from ..session import WebmateSession


class ArtifactClient:
    _QUERY_PROJECT = UriTemplate("/projects/{projectId}/artifact-infos", name="QueryArtifacts")
    _QUERY_BROWSER_SESSION = UriTemplate("/browsersession/{browserSessionId}/artifacts", name="QueryArtifactsForBrowserSession")
    _GET_ARTIFACT = UriTemplate("/artifact/artifacts/{artifactId}", name="GetArtifact")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    def query_artifacts(
        self,
        *,
        project_id: ProjectId | None = None,
        test_run_id: TestRunId | None = None,
        browser_session_id: BrowserSessionId | None = None,
        artifact_types: Sequence[str] | None = None,
    ) -> List[dict]:
        params: dict[str, str] = {}
        if test_run_id:
            params["testRunId"] = str(test_run_id)
        if browser_session_id:
            params["browserSessionId"] = str(browser_session_id)
        if artifact_types:
            params["types"] = ",".join(artifact_types)
        project = project_id or self._session.require_project()
        response = self._client.get(
            self._QUERY_PROJECT,
            path_params={"projectId": str(project)},
            query=params,
        )
        data = _safe_json(response)
        return list(data) if isinstance(data, list) else []

    def query_artifacts_for_session(self, browser_session_id: BrowserSessionId) -> List[dict]:
        response = self._client.get(
            self._QUERY_BROWSER_SESSION,
            path_params={"browsersessionId": str(browser_session_id)},
        )
        data = _safe_json(response)
        return list(data) if isinstance(data, list) else []

    def get_artifact(self, artifact_id: ArtifactId) -> dict | None:
        response = self._client.get(self._GET_ARTIFACT, path_params={"artifactId": str(artifact_id)})
        return _safe_json(response)


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


__all__ = ["ArtifactClient"]
