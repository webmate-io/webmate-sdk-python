"""Device subsystem facade."""
from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Sequence

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
    _INSTALL_APP = UriTemplate("/device/{deviceId}/appinstall/{packageId}", name="InstallApp")
    _UPLOAD_IMAGE = UriTemplate("/projects/{projectId}/images", name="UploadImage")
    _IMPOSE_REQUIREMENT = UriTemplate("/device/devices/{deviceId}/requirements/propertyRequirement", name="ImposeRequirement")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    def list_devices(self, project_id: ProjectId | None = None) -> List[DeviceId]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._LIST_DEVICES, path_params={"projectId": str(project)})
        data = _safe_json(response)
        if isinstance(data, list):
            return [DeviceId.parse(item) for item in data]
        return []

    def get_device(self, device_id: DeviceId | str) -> dict | None:
        response = self._client.get(self._GET_DEVICE, path_params={"deviceId": str(device_id)})
        return _safe_json(response)

    def request_device(self, device_request: Mapping[str, object], project_id: ProjectId | None = None) -> dict:
        project = project_id or self._session.require_project()
        payload = to_jsonable(device_request)
        response = self._client.post(
            self._REQUEST_DEVICE,
            path_params={"projectId": str(project)},
            json=payload,
        )
        data = _safe_json(response)
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from device request")
        return data

    def synchronize_device(self, device_id: DeviceId | str) -> None:
        self._client.post(self._SYNCHRONIZE_DEVICE, path_params={"deviceId": str(device_id)})

    def release_device(self, device_id: DeviceId | str) -> None:
        self._client.delete(self._RELEASE_DEVICE, path_params={"deviceId": str(device_id)})

    def redeploy_device(self, device_id: DeviceId | str) -> None:
        self._client.post(self._REDEPLOY_DEVICE, path_params={"deviceId": str(device_id)})

    def reset_device(self, device_id: DeviceId | str) -> None:
        self._client.post(self._RESET_DEVICE, path_params={"deviceId": str(device_id)})

    def install_app(self, device_id: DeviceId | str, package_id: PackageId | str, *, instrumented: bool = False) -> None:
        query = {"wait": "true", "instrumented": str(bool(instrumented)).lower()}
        self._client.post(
            self._INSTALL_APP,
            path_params={"deviceId": str(device_id), "packageId": str(package_id)},
            query=query,
        )

    def impose_property_requirement(self, device_id: DeviceId | str, requirement: Mapping[str, object]) -> None:
        self._client.post(
            self._IMPOSE_REQUIREMENT,
            path_params={"deviceId": str(device_id)},
            json=to_jsonable(requirement),
        )

    def upload_image(
        self,
        project_id: ProjectId | None,
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
        return ImageId.parse(data)


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            return response.text.strip().strip('"')
        return None


__all__ = ["DeviceClient"]
