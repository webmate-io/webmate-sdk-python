"""Python port of the webmate JobEngine facade."""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional

from ..exceptions import WebmateApiError
from ..http import ApiClient, UriTemplate
from ..ids import JobId, JobRunId, ProjectId
from ..session import WebmateSession
from ..utils import to_jsonable
from .models import JobConfigName, JobRunSummary, PortName, WMValue


class JobEngine:
    _CREATE_JOB = UriTemplate("/projects/{projectId}/job/jobs", name="CreateJob")
    _START_JOB = UriTemplate("/job/jobs/{jobId}/jobruns", name="StartJob")
    _JOB_RUNS_FOR_JOB = UriTemplate("/job/jobs/{jobId}/jobruns", name="GetJobRuns")
    _JOB_RUN_SUMMARY = UriTemplate("/job/jobruns/{jobRunId}/summary", name="GetJobRunSummary")
    _JOBS_FOR_PROJECT = UriTemplate("/projects/{projectId}/job/jobs", name="JobsForProject")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    # ---------------------------------------------------------------------
    def create_job(
        self,
        job_config_name: JobConfigName | str,
        job_instance_name: str,
        input_values: Mapping[PortName | str, WMValue | Mapping[str, object]],
        *,
        project_id: ProjectId | None = None,
        start_immediately: bool = False,
    ) -> JobId:
        project = project_id or self._session.require_project()
        payload = {
            "nameForJobInstance": job_instance_name,
            "inputValues": _serialize_input_values(input_values),
            "jobConfigIdOrName": str(job_config_name) if isinstance(job_config_name, JobConfigName) else str(job_config_name),
            "scheduling": {"jobSchedulingSpec": {"ExecuteLater": {}}},
        }
        response = self._client.post(
            self._CREATE_JOB,
            path_params={"projectId": str(project)},
            json=payload,
            query={"start": "true" if start_immediately else None},
        )
        return _parse_job_id(response)

    def start_job(
        self,
        job_config_name: JobConfigName | str,
        job_instance_name: str,
        input_values: Mapping[PortName | str, WMValue | Mapping[str, object]],
        *,
        project_id: ProjectId | None = None,
    ) -> JobRunId:
        job_id = self.create_job(job_config_name, job_instance_name, input_values, project_id=project_id)
        return self.start_existing_job(job_id)

    def start_existing_job(self, job_id: JobId | str) -> JobRunId:
        response = self._client.post(self._START_JOB, path_params={"jobId": str(job_id)})
        return _parse_job_run_id(response)

    def get_job_runs_for_job(self, job_id: JobId | str) -> List[JobRunId]:
        response = self._client.get(self._JOB_RUNS_FOR_JOB, path_params={"jobId": str(job_id)})
        data = _safe_json(response)
        if isinstance(data, list):
            return [JobRunId.parse(item) for item in data]
        raise WebmateApiError("Unexpected payload when listing job runs", payload=data)

    def get_job_run_summary(self, job_run_id: JobRunId | str) -> JobRunSummary:
        response = self._client.get(self._JOB_RUN_SUMMARY, path_params={"jobRunId": str(job_run_id)})
        data = _safe_json(response)
        return JobRunSummary.from_api(data)

    def list_jobs(self, *, project_id: ProjectId | None = None) -> List[JobId]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._JOBS_FOR_PROJECT, path_params={"projectId": str(project)})
        data = _safe_json(response)
        if isinstance(data, list):
            results: List[JobId] = []
            for item in data:
                if isinstance(item, dict) and "id" in item:
                    results.append(JobId.parse(item["id"]))
                else:
                    results.append(JobId.parse(item))
            return results
        raise WebmateApiError("Unexpected payload when listing jobs", payload=data)


def _serialize_input_values(
    input_values: Mapping[PortName | str, WMValue | Mapping[str, object]]
) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in input_values.items():
        if isinstance(key, PortName):
            name = key.name
        else:
            name = str(key)
        if isinstance(value, WMValue):
            result[name] = value.to_json()
        else:
            result[name] = to_jsonable(value)
    return result


def _parse_job_id(response) -> JobId:
    data = _safe_json(response, allow_text=True)
    if isinstance(data, dict) and "id" in data:
        return JobId.parse(data["id"])
    return JobId.parse(data)


def _parse_job_run_id(response) -> JobRunId:
    data = _safe_json(response, allow_text=True)
    if isinstance(data, dict) and "id" in data:
        return JobRunId.parse(data["id"])
    return JobRunId.parse(data)


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            return response.text.strip().strip('"')
        raise


__all__ = ["JobEngine"]
