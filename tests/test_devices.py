import json
import pathlib
import sys
import uuid
import unittest
from unittest import mock

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from webmate_sdk import AuthInfo, WebmateEnvironment
from webmate_sdk.exceptions import WebmateApiError, WebmateTimeoutError
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
        self.orig_package_id = PackageId(uuid.uuid4())

    def package_response(self, **overrides):
        package = {
            "id": str(self.package_id),
            "origPackageId": str(self.orig_package_id),
            "origPackageType": "apk",
        }
        package.update(overrides)
        return make_response(status=200, json_data=package)

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_property_requirement_route(self, mock_request):
        mock_request.side_effect = [self.package_response(), make_response(status=204)]

        self.client.install_app(self.device_id, self.package_id)

        get_kwargs = mock_request.call_args_list[0].kwargs
        self.assertEqual(get_kwargs["method"], "GET")
        self.assertTrue(get_kwargs["url"].endswith(f"/package/packages/{self.package_id}"))
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
        # The requirement names the concrete original package, not the package document id.
        self.assertEqual(package_installation["packageId"], str(self.orig_package_id))
        self.assertEqual(package_installation["packageType"], "apk")
        self.assertEqual(package_installation["state"], "finished")

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_instrumented_package(self, mock_request):
        instrumented_id = str(uuid.uuid4())
        mock_request.side_effect = [
            self.package_response(instrumentedPackageId=instrumented_id, instrumentedPackageType="apk"),
            make_response(status=204),
        ]

        self.client.install_app(self.device_id, self.package_id, instrumented=True)

        _, kwargs = mock_request.call_args
        package_installation = kwargs["json"]["package.installedPackages"]
        self.assertEqual(package_installation["packageId"], instrumented_id)

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_rejects_missing_instrumented_package(self, mock_request):
        mock_request.side_effect = [self.package_response()]

        with self.assertRaises(ValueError):
            self.client.install_app(self.device_id, self.package_id, instrumented=True)
        self.assertEqual(mock_request.call_count, 1)

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_package_type_from_package(self, mock_request):
        mock_request.side_effect = [self.package_response(origPackageType="ipa"), make_response(status=204)]

        self.client.install_app(self.device_id, self.package_id)

        _, kwargs = mock_request.call_args
        package_installation = kwargs["json"]["package.installedPackages"]
        self.assertEqual(package_installation["packageType"], "ipa")

    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_uses_overridden_package_type(self, mock_request):
        mock_request.side_effect = [self.package_response(), make_response(status=204)]

        self.client.install_app(
            self.device_id,
            self.package_id,
            package_type="ipa",
        )

        _, kwargs = mock_request.call_args
        package_installation = kwargs["json"]["package.installedPackages"]
        self.assertEqual(package_installation["packageType"], "ipa")

    def device_response(self, state=None, installation_id=None, previous_installation=False):
        installed = []
        if previous_installation:
            installed.append(self.installation(str(uuid.uuid4()), "finished"))
        if state is not None:
            installed.append(self.installation(installation_id or str(uuid.uuid4()), state))
        return make_response(status=200, json_data={
            "id": str(self.device_id),
            "properties": {"package.installedPackages": installed},
        })

    def installation(self, installation_id, state):
        return {
            "installationId": installation_id,
            "packageId": str(self.orig_package_id),
            "packageType": "apk",
            "state": state,
        }

    def fake_device(self, states, previous_installation=False):
        """Request side effect: answers the package lookup and the install requirement, then reports the given
        installation states (one per device lookup) for the installation id sent in the requirement."""
        requested = {}
        states = list(states)

        def respond(**kwargs):
            if kwargs["method"] == "POST":
                requested["id"] = kwargs["json"]["package.installedPackages"]["installationId"]
                return make_response(status=204)
            if "/package/packages/" in kwargs["url"]:
                return self.package_response()
            state = states.pop(0) if len(states) > 1 else states[0]
            return self.device_response(state, requested.get("id"), previous_installation)

        return respond

    @mock.patch("webmate_sdk.devices.client.time.sleep")
    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_returns_installed_package_without_waiting(self, mock_request, _sleep):
        mock_request.side_effect = [self.package_response(), make_response(status=204)]

        installed = self.client.install_app(self.device_id, self.package_id)

        self.assertEqual(str(installed), str(self.orig_package_id))
        self.assertEqual(mock_request.call_count, 2)

    @mock.patch("webmate_sdk.devices.client.time.sleep")
    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_waits_until_package_is_installed(self, mock_request, mock_sleep):
        mock_request.side_effect = self.fake_device([None, "requested", "finished"])

        self.client.install_app(self.device_id, self.package_id, wait=True, poll_interval=1)

        self.assertEqual(mock_request.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(1)

    @mock.patch("webmate_sdk.devices.client.time.sleep")
    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_install_app_does_not_mistake_previous_installation_for_requested_one(self, mock_request, mock_sleep):
        mock_request.side_effect = self.fake_device([None, "requested", "finished"], previous_installation=True)

        self.client.install_app(self.device_id, self.package_id, wait=True, poll_interval=1)

        self.assertEqual(mock_request.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 2)

    @mock.patch("webmate_sdk.devices.client.time.sleep")
    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_wait_for_installed_package_raises_on_failed_installation(self, mock_request, _sleep):
        mock_request.side_effect = [self.device_response("failed")]

        with self.assertRaises(WebmateApiError) as ctx:
            self.client.wait_for_installed_package(self.device_id, self.orig_package_id)
        self.assertNotIsInstance(ctx.exception, WebmateTimeoutError)

    @mock.patch("webmate_sdk.devices.client.time.sleep")
    @mock.patch("webmate_sdk.http.requests.Session.request")
    def test_wait_for_installed_package_times_out(self, mock_request, _sleep):
        mock_request.side_effect = lambda **_: self.device_response("requested")

        with self.assertRaises(WebmateTimeoutError):
            self.client.wait_for_installed_package(self.device_id, self.orig_package_id, timeout_seconds=0)

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
