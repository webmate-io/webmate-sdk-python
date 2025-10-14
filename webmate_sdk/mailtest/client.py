"""Mail testing facade."""
from __future__ import annotations

from typing import List, Optional

from ..artifacts.client import ArtifactClient
from ..http import ApiClient, UriTemplate
from ..ids import ProjectId, TestRunId
from ..session import WebmateSession


class MailTestClient:
    _CREATE_ADDRESS = UriTemplate("/mailtest/testmail/{projectId}", name="CreateTestMailAddress")

    def __init__(self, session: WebmateSession, artifact_client: ArtifactClient | None = None) -> None:
        self._session = session
        self._artifact_client = artifact_client or ArtifactClient(session)
        self._client = ApiClient(session.auth, session.environment)

    def create_test_mail_address(self, project_id: ProjectId | None, test_run_id: TestRunId | str) -> str:
        project = project_id or self._session.require_project()
        response = self._client.post(
            self._CREATE_ADDRESS,
            path_params={"projectId": str(project)},
            json={"testRunId": str(test_run_id)},
        )
        payload = _safe_json(response)
        if isinstance(payload, dict) and "emailAddress" in payload:
            return payload["emailAddress"]
        if isinstance(payload, dict) and "address" in payload:
            return payload["address"]
        if isinstance(payload, str):
            return payload
        raise ValueError("Unexpected response while creating test mail address")

    def get_mails_in_test_run(self, project_id: ProjectId | None, test_run_id: TestRunId | str) -> List[dict]:
        project = project_id or self._session.require_project()
        artifacts = self._artifact_client.query_artifacts(
            project_id=project,
            test_run_id=TestRunId.parse(test_run_id),
            artifact_types=["Mail.MailContent"],
        )
        results: List[dict] = []
        for info in artifacts:
            artifact_id = info.get("id")
            if artifact_id:
                artifact = self._artifact_client.get_artifact(artifact_id)
                if artifact:
                    results.append(artifact)
        return results


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return response.text.strip()


__all__ = ["MailTestClient"]
