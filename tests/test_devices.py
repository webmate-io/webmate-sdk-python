import json
import pathlib
import sys
import uuid
import unittest
from unittest import mock

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from webmate_sdk import AuthInfo, WebmateEnvironment
from webmate_sdk.ids import DeviceId, PackageId
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


class DeviceClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session = WebmateSession(
            auth=AuthInfo(api_token="token", email="user@example.com"),
            environment=WebmateEnvironment(),
        )
        self.client = self.session.device
        self.device_id = DeviceId(uuid.uuid4())
        self.package_id = PackageId(uuid.uuid4())

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_property_requirement_route(self, mock_request):
        mock_request.return_value = make_response(status=204)

        self.client.install_app(self.device_id, self.package_id, instrumented=True)

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertTrue(kwargs["url"].endswith(
            f"/device/devices/{self.device_id}/requirements/propertyRequirement"
        ))
        self.assertIsNone(kwargs["params"])
        self.assertIn("package.installedPackages", kwargs["json"])
        package_installation = kwargs["json"]["package.installedPackages"]
        self.assertRegex(
            package_installation["installationId"],
            r"^[0-9a-f-]{36}$",
        )
        self.assertEqual(package_installation["packageId"], str(self.package_id))
        self.assertEqual(package_installation["packageType"], "apk")
        self.assertEqual(package_installation["state"], "finished")

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_overridden_package_type(self, mock_request):
        mock_request.return_value = make_response(status=204)

        self.client.install_app(
            self.device_id,
            self.package_id,
            package_type="ipa",
        )

        _, kwargs = mock_request.call_args
        package_installation = kwargs["json"]["package.installedPackages"]
        self.assertEqual(package_installation["packageType"], "ipa")

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_impose_property_requirement_posts_simple_payload(self, mock_request):
        mock_request.return_value = make_response(status=204)
        requirement = {"automation.available": True}

        self.client.impose_property_requirement(self.device_id, requirement)

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertTrue(kwargs["url"].endswith(
            f"/device/devices/{self.device_id}/requirements/propertyRequirement"
        ))
        self.assertEqual(kwargs["json"], requirement)

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_impose_property_requirement_normalizes_legacy_payload(self, mock_request):
        mock_request.return_value = make_response(status=204)
        requirement = {"propertyName": "automation.available", "value": True}

        self.client.impose_property_requirement(self.device_id, requirement)

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["json"], {"automation.available": True})

    def test_impose_property_requirement_rejects_multiple_properties(self):
        with self.assertRaises(ValueError):
            self.client.impose_property_requirement(
                self.device_id,
                {"automation.available": True, "simulation.simulateWebView": True},
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
