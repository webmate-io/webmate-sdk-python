"""Device subsystem facade."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Mapping, Optional, Union

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
        package_type: str = "apk",
        instrumented: bool = False,
    ) -> None:
        # Keep the public signature stable although `instrumented` has no effect
        # with the requirement-based installation flow.
        _ = instrumented
        self.impose_property_requirement(
            device_id,
            _package_installation_requirement(package_id, package_type=package_type),
        )

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


def _package_installation_requirement(package_id: Union[PackageId, str], *, package_type: str) -> Dict[str, object]:
    return {
        "package.installedPackages": {
            "installationId": str(uuid.uuid4()),
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
