import json
import pathlib
import sys
import unittest
from unittest import mock

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from webmate_sdk.auth import AuthInfo
from webmate_sdk.environment import WebmateEnvironment
from webmate_sdk.exceptions import WebmateApiError
from webmate_sdk.http import ApiClient, UriTemplate


def make_response(status=200, json_data=None, text="", headers=None):
    response = requests.Response()
    response.status_code = status
    if json_data is not None:
        response._content = json.dumps(json_data).encode("utf-8")
        response.headers["Content-Type"] = "application/json"
    else:
        response._content = text.encode("utf-8")
    response.headers.update(headers or {})
    response.encoding = "utf-8"
    response.url = "https://example.com/api"
    return response


class ApiClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = AuthInfo(api_token="token", email="user@example.com")
        self.environment = WebmateEnvironment()

    def test_session_headers_include_auth(self):
        client = ApiClient(self.auth, self.environment)
        self.assertEqual(client._session.headers["webmate.api-token"], "token")
        self.assertEqual(client._session.headers["webmate.user"], "user@example.com")
        self.assertIn("webmate-python-sdk", client._session.headers["User-Agent"])
        client.close()

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_request_raises_on_error_status(self, mock_request):
        mock_request.return_value = make_response(status=500, text="boom")
        client = ApiClient(self.auth, self.environment)
        with self.assertRaises(WebmateApiError) as ctx:
            client.get(UriTemplate("/boom"))
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.payload, "boom")
        client.close()

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_get_returns_response_on_success(self, mock_request):
        mock_request.return_value = make_response(status=200, json_data={"ok": True})
        client = ApiClient(self.auth, self.environment)
        response = client.get(UriTemplate("/ping"))
        self.assertEqual(response.json(), {"ok": True})
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "GET")
        self.assertIn("https://", kwargs["url"])
        client.close()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
