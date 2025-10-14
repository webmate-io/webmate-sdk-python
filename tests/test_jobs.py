import json
import pathlib
import sys
import uuid
import unittest
from unittest import mock

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from webmate_sdk import AuthInfo, WebmateEnvironment
from webmate_sdk.ids import ProjectId
from webmate_sdk.jobs import JobConfigName, JobEngine, PortName, WMDataType, WMValue
from webmate_sdk.session import WebmateSession


def make_response(status=200, json_data=None, text=""):
    response = requests.Response()
    response.status_code = status
    if json_data is not None:
        response._content = json.dumps(json_data).encode("utf-8")
        response.headers["Content-Type"] = "application/json"
    else:
        response._content = text.encode("utf-8")
    response.encoding = "utf-8"
    response.url = "https://example.com/api"
    return response


class JobEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project_id = ProjectId(uuid.uuid4())
        self.session = WebmateSession(
            auth=AuthInfo(api_token="token", email="user@example.com"),
            environment=WebmateEnvironment(),
            project_id=self.project_id,
        )

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_create_job_serializes_payload(self, mock_request):
        job_id = str(uuid.uuid4())
        mock_request.return_value = make_response(json_data=job_id)
        engine = self.session.job_engine

        input_values = {
            PortName("vehicleSpec"): WMValue(WMDataType("LiveExpeditionSpec"), {"foo": "bar"})
        }
        result = engine.create_job(JobConfigName("MyJob"), "Instance", input_values)
        self.assertEqual(str(result), job_id)

        _, kwargs = mock_request.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["nameForJobInstance"], "Instance")
        self.assertEqual(payload["jobConfigIdOrName"], "MyJob")
        self.assertIn("vehicleSpec", payload["inputValues"])
        self.assertEqual(payload["inputValues"]["vehicleSpec"]["type"], "LiveExpeditionSpec")
        self.assertEqual(payload["inputValues"]["vehicleSpec"]["data"], {"foo": "bar"})

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_start_existing_job_returns_job_run_id(self, mock_request):
        job_run_id = str(uuid.uuid4())
        mock_request.return_value = make_response(json_data=job_run_id)
        engine = self.session.job_engine

        result = engine.start_existing_job(uuid.uuid4())
        self.assertEqual(str(result), job_run_id)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
