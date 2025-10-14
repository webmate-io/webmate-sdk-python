import json
import pathlib
import sys
import uuid
import unittest
from unittest import mock

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from webmate_sdk import AuthInfo, WebmateEnvironment
from webmate_sdk.browsersession import BrowserSessionClient
from webmate_sdk.ids import BrowserSessionId
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


class BrowserSessionClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session = WebmateSession(
            auth=AuthInfo(api_token="token", email="user@example.com"),
            environment=WebmateEnvironment(),
        )
        self.client = self.session.browser_session
        self.browser_session_id = BrowserSessionId(uuid.uuid4())

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_create_state_uses_default_config(self, mock_request):
        state_id = str(uuid.uuid4())
        mock_request.return_value = make_response(json_data=state_id)

        result = self.client.create_state(self.browser_session_id, "checkpoint")
        self.assertEqual(str(result), state_id)

        _, kwargs = mock_request.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["optMatchingId"], "checkpoint")
        extraction = payload["extractionConfig"]
        self.assertTrue(extraction["extractDomStateData"])
        self.assertEqual(extraction["screenShotConfig"]["fullPage"], True)
        self.assertIn("hideFixedElements", extraction["screenShotConfig"])

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_finish_action_posts_artifact(self, mock_request):
        mock_request.return_value = make_response(json_data=str(uuid.uuid4()))
        span_return_id = self.client.start_action(self.browser_session_id, "Load page")
        self.client.finish_action(self.browser_session_id, message="done")

        self.assertTrue(span_return_id)
        self.assertGreaterEqual(mock_request.call_count, 2)
        _, kwargs = mock_request.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["artifactType"], "Action.ActionFinish")
        self.assertTrue(payload["data"]["result"]["success"])
        self.assertEqual(payload["data"]["result"]["message"], "done")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
