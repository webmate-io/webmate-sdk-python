"""Test management facade."""
from __future__ import annotations

from typing import Mapping, Optional

from ..http import ApiClient, UriTemplate
from ..ids import ProjectId, TestExecutionId, TestRunId, TestSessionId, TestTemplateId
from ..session import WebmateSession
from ..utils import to_jsonable


class TestMgmtClient:
    _GET_TEST_TEMPLATES = UriTemplate("/projects/{projectId}/tests", name="GetTestTemplates")
    _GET_TEST_TEMPLATE = UriTemplate("/testmgmt/tests/{testId}", name="GetTestTemplate")
    _CREATE_TEST_SESSION = UriTemplate("/projects/{projectId}/testsessions", name="CreateTestSession")
    _CREATE_TEST_EXECUTION = UriTemplate("/projects/{projectId}/testexecutions", name="CreateTestExecution")
    _START_TEST_EXECUTION = UriTemplate("/testmgmt/testexecutions/{testExecutionId}", name="StartTestExecution")
    _GET_TEST_EXECUTION = UriTemplate("/testmgmt/testexecutions/{testExecutionId}", name="GetTestExecution")
    _GET_TEST_RUN = UriTemplate("/testmgmt/testruns/{testRunId}", name="GetTestRun")
    _SET_TEST_RUN_NAME = UriTemplate("/testmgmt/testruns/{testRunId}/name", name="SetTestRunName")
    _FINISH_TEST_RUN = UriTemplate("/testmgmt/testruns/{testRunId}/finish", name="FinishTestRun")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    # ------------------------------------------------------------------
    def get_test_templates(self, project_id: ProjectId | None = None) -> list[dict]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._GET_TEST_TEMPLATES, path_params={"projectId": str(project)})
        data = _safe_json(response)
        return list(data) if isinstance(data, list) else []

    def get_test_template(self, test_id: TestTemplateId | str) -> dict | None:
        response = self._client.get(self._GET_TEST_TEMPLATE, path_params={"testId": str(test_id)})
        return _safe_json(response)

    def create_test_session(self, name: str, project_id: ProjectId | None = None) -> TestSessionId:
        project = project_id or self._session.require_project()
        response = self._client.post(
            self._CREATE_TEST_SESSION,
            path_params={"projectId": str(project)},
            json={"name": name},
        )
        data = _safe_json(response, allow_text=True)
        return TestSessionId.parse(data["id"] if isinstance(data, dict) else data)

    def create_test_execution(
        self,
        spec: Mapping[str, object],
        *,
        project_id: ProjectId | None = None,
        start_immediately: bool = False,
    ) -> dict:
        project = project_id or self._session.require_project()
        response = self._client.post(
            self._CREATE_TEST_EXECUTION,
            path_params={"projectId": str(project)},
            query={"start": "true" if start_immediately else None},
            json=to_jsonable(spec),
        )
        return _expect_dict(response)

    def start_test_execution(self, test_execution_id: TestExecutionId | str) -> TestRunId:
        response = self._client.post(
            self._START_TEST_EXECUTION,
            path_params={"testExecutionId": str(test_execution_id)},
        )
        data = _safe_json(response, allow_text=True)
        return TestRunId.parse(data["id"] if isinstance(data, dict) else data)

    def get_test_execution(self, test_execution_id: TestExecutionId | str) -> dict | None:
        response = self._client.get(
            self._GET_TEST_EXECUTION,
            path_params={"testExecutionId": str(test_execution_id)},
        )
        return _safe_json(response)

    def get_test_run(self, test_run_id: TestRunId | str) -> dict | None:
        response = self._client.get(self._GET_TEST_RUN, path_params={"testRunId": str(test_run_id)})
        return _safe_json(response)

    def set_test_run_name(self, test_run_id: TestRunId | str, name: str) -> None:
        self._client.post(
            self._SET_TEST_RUN_NAME,
            path_params={"testRunId": str(test_run_id)},
            json={"name": name},
        )

    def finish_test_run(self, test_run_id: TestRunId | str, finish_data: Mapping[str, object] | None = None) -> None:
        self._client.post(
            self._FINISH_TEST_RUN,
            path_params={"testRunId": str(test_run_id)},
            json=to_jsonable(finish_data) if finish_data else None,
        )


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            text = response.text.strip().strip('"')
            return text
        return None


def _expect_dict(response) -> dict:
    payload = _safe_json(response, allow_text=True)
    if isinstance(payload, dict):
        return payload
    return {"id": payload}


__all__ = ["TestMgmtClient"]
