"""Device subsystem facade."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Mapping, Optional, Union

from ..exceptions import WebmateApiError, WebmateTimeoutError
from ..http import ApiClient, UriTemplate
from ..ids import DeviceId, ImageId, PackageId, ProjectId
from ..session import WebmateSession
from ..utils import to_jsonable


class DeviceClient:
    _LIST_DEVICES = UriTemplate("/projects/{projectId}/device/devices", name="ListDevices")
    _GET_DEVICE = UriTemplate("/device/devices/{deviceId}", name="GetDevice")
    _REQUEST_DEVICE = UriTemplate("/projects/{projectId}/device/devices", name="RequestDevice")
    _SYNCHRONIZE_DEVICE = UriTemplate("/device/devices/{deviceId}/sync", name="SynchronizeDevice")
    _RELEASE_DEVICE = UriTemplate("/device/devices/{deviceId}", name="ReleaseDevice")
    _REDEPLOY_DEVICE = UriTemplate("/device/devices/{deviceId}/redeploy", name="RedeployDevice")
    _RESET_DEVICE = UriTemplate("/device/devices/{deviceId}/reset", name="ResetDevice")
    _UPLOAD_IMAGE = UriTemplate("/projects/{projectId}/images", name="UploadImage")
    _IMPOSE_REQUIREMENT = UriTemplate("/device/devices/{deviceId}/requirements/propertyRequirement", name="ImposeRequirement")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    def list_devices(self, project_id: Optional[ProjectId] = None) -> List[DeviceId]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._LIST_DEVICES, path_params={"projectId": str(project)})
        data = _safe_json(response)
        if isinstance(data, list):
            return [DeviceId.parse(item) for item in data]
        return []

    def get_device(self, device_id: Union[DeviceId, str]) -> Optional[Dict[str, Any]]:
        response = self._client.get(self._GET_DEVICE, path_params={"deviceId": str(device_id)})
        data = _safe_json(response)
        if isinstance(data, dict):
            return data
        return None

    def request_device(
        self,
        device_request: Mapping[str, object],
        project_id: Optional[ProjectId] = None,
        *,
        use_deployed: Optional[bool] = None,
    ) -> Dict[str, Any]:
        project = project_id or self._session.require_project()
        payload = to_jsonable(device_request)
        query = {"useDeployed": None if use_deployed is None else str(use_deployed).lower()}
        response = self._client.post(
            self._REQUEST_DEVICE,
            path_params={"projectId": str(project)},
            query=query,
            json=payload,
        )
        data = _safe_json(response)
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from device request")
        return data

    def synchronize_device(self, device_id: Union[DeviceId, str]) -> None:
        self._client.post(self._SYNCHRONIZE_DEVICE, path_params={"deviceId": str(device_id)})

    def release_device(self, device_id: Union[DeviceId, str]) -> None:
        self._client.delete(self._RELEASE_DEVICE, path_params={"deviceId": str(device_id)})

    def redeploy_device(self, device_id: Union[DeviceId, str]) -> None:
        self._client.post(self._REDEPLOY_DEVICE, path_params={"deviceId": str(device_id)})

    def reset_device(self, device_id: Union[DeviceId, str]) -> None:
        self._client.post(self._RESET_DEVICE, path_params={"deviceId": str(device_id)})

    def install_app(
        self,
        device_id: Union[DeviceId, str],
        package_id: Union[PackageId, str],
        *,
        package_type: Optional[str] = None,
        instrumented: bool = False,
        wait: bool = False,
        timeout_seconds: float = 600.0,
        poll_interval: float = 5.0,
    ) -> PackageId:
        """Request the installation of an app on a device.

        ``package_id`` is the id of the package as returned by the package management
        (e.g. by ``packages.upload_and_create_package``). The concrete package that gets
        installed is resolved from it: the original package, or the instrumented one if
        ``instrumented`` is set. ``package_type`` overrides the type reported for it.

        This writes the corresponding device property requirement. By default it does not
        wait for the installation to complete; with ``wait=True`` it blocks until the device
        reports the package as installed (see ``wait_for_installed_package``).

        Returns the id of the concrete package that is installed.
        """
        package = self._session.packages.get_package(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        if instrumented:
            resolved_id = package.get("instrumentedPackageId")
            if not resolved_id:
                raise ValueError(f"Package {package_id} has no instrumented version")
            resolved_type = package.get("instrumentedPackageType") or package.get("origPackageType")
        else:
            resolved_id = package.get("origPackageId")
            resolved_type = package.get("origPackageType")
        installation_id = str(uuid.uuid4())
        self.impose_property_requirement(
            device_id,
            _package_installation_requirement(
                resolved_id, package_type=package_type or resolved_type or "apk", installation_id=installation_id
            ),
        )
        installed_package_id = PackageId.parse(resolved_id)
        if wait:
            self.wait_for_installed_package(
                device_id,
                installed_package_id,
                installation_id=installation_id,
                timeout_seconds=timeout_seconds,
                poll_interval=poll_interval,
            )
        return installed_package_id

    def wait_for_installed_package(
        self,
        device_id: Union[DeviceId, str],
        installed_package_id: Union[PackageId, str],
        *,
        installation_id: Optional[str] = None,
        timeout_seconds: float = 600.0,
        poll_interval: float = 5.0,
    ) -> Dict[str, Any]:
        """Wait until the device reports the given package as installed and return the device.

        ``installed_package_id`` is the concrete package, as returned by ``install_app``.
        If ``installation_id`` is given, only the installation with that id is considered, so that
        a previous installation of the same package is not mistaken for the requested one.
        Raises ``WebmateApiError`` if the device reports the installation as failed and
        ``WebmateTimeoutError`` if it does not finish within ``timeout_seconds``.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            device = self.get_device(device_id)
            state = _installation_state(device, str(installed_package_id), installation_id)
            if state == "finished":
                return device
            if state == "failed":
                raise WebmateApiError(
                    f"Installation of package {installed_package_id} on device {device_id} failed", payload=device
                )
            if time.monotonic() >= deadline:
                raise WebmateTimeoutError(
                    f"Package {installed_package_id} was not installed on device {device_id} "
                    f"within {timeout_seconds} seconds"
                )
            time.sleep(poll_interval)

    def impose_property_requirement(self, device_id: Union[DeviceId, str], requirement: Mapping[str, object]) -> None:
        self._client.post(
            self._IMPOSE_REQUIREMENT,
            path_params={"deviceId": str(device_id)},
            json=_normalize_property_requirement(requirement),
        )

    def upload_image(
        self,
        project_id: Optional[ProjectId],
        image_bytes: bytes,
        *,
        name: str,
        content_type: str = "image/png",
    ) -> ImageId:
        project = project_id or self._session.require_project()
        headers = {"Content-Type": content_type}
        response = self._client.post(
            self._UPLOAD_IMAGE,
            path_params={"projectId": str(project)},
            query={"name": name},
            data=image_bytes,
            headers=headers,
        )
        data = _safe_json(response, allow_text=True)
        if not isinstance(data, str):
            raise ValueError("Unexpected response from image upload")
        return ImageId.parse(data)


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            return response.text.strip().strip('"')
        return None


def _installation_state(
    device: Optional[Mapping[str, Any]], package_id: str, installation_id: Optional[str] = None
) -> Optional[str]:
    """State of the latest installation of the package (or of the given installation) reported by the device, if any."""
    installed = ((device or {}).get("properties") or {}).get("package.installedPackages") or []
    if isinstance(installed, Mapping):
        installed = [installed]
    states = [
        p.get("state") for p in installed
        if isinstance(p, Mapping) and p.get("packageId") == package_id
        and (installation_id is None or p.get("installationId") == installation_id)
    ]
    return states[-1] if states else None


def _package_installation_requirement(
    package_id: Union[PackageId, str], *, package_type: str, installation_id: str
) -> Dict[str, object]:
    return {
        "package.installedPackages": {
            "installationId": installation_id,
            "packageId": str(package_id),
            "packageType": package_type,
            "state": "finished",
        },
    }


def _normalize_property_requirement(requirement: Mapping[str, object]) -> dict[str, Any]:
    payload = to_jsonable(requirement)
    if not isinstance(payload, dict):
        raise ValueError("Property requirement must serialize to a JSON object")

    if set(payload.keys()) == {"propertyName", "value"}:
        property_name = payload["propertyName"]
        if not isinstance(property_name, str) or not property_name:
            raise ValueError("propertyName must be a non-empty string")
        payload = {property_name: payload["value"]}

    if len(payload) != 1:
        raise ValueError("Exactly one property requirement must be sent per request")

    property_name = next(iter(payload))
    if not isinstance(property_name, str) or not property_name:
        raise ValueError("Property requirement key must be a non-empty string")

    return payload


__all__ = ["DeviceClient"]
