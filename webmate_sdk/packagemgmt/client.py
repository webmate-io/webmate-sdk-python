"""Package management facade."""
from __future__ import annotations

import time
from typing import List, Mapping, Optional

from ..blobs.client import BlobClient
from ..exceptions import WebmateApiError
from ..http import ApiClient, UriTemplate
from ..ids import BlobId, PackageId, ProjectId
from ..session import WebmateSession
from ..utils import to_jsonable


class PackageMgmtClient:
    _CREATE_PACKAGE = UriTemplate("/projects/{projectId}/packages", name="CreatePackage")
    _UPDATE_PACKAGE = UriTemplate("/package/packages/{packageId}", name="UpdatePackage")
    _GET_PACKAGE = UriTemplate("/package/packages/{packageId}", name="GetPackage")
    _GET_PACKAGES_FOR_PROJECT = UriTemplate("/projects/{projectId}/packages/full", name="GetPackagesForProject")
    _DELETE_PACKAGE = UriTemplate("/package/packages/{packageId}", name="DeletePackage")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)
        self._blob_client = BlobClient(session)

    def create_package(self, blob_id: BlobId | str, name: str, extension: str, *, project_id: ProjectId | None = None) -> dict:
        project = project_id or self._session.require_project()
        payload = {"blobId": str(blob_id), "name": name, "extension": extension}
        response = self._client.post(
            self._CREATE_PACKAGE,
            path_params={"projectId": str(project)},
            json=payload,
        )
        return _expect_dict(response)

    def update_package(self, package_id: PackageId | str, blob_id: BlobId | str, name: str, extension: str) -> dict:
        payload = {"blobId": str(blob_id), "name": name, "extension": extension}
        response = self._client.put(
            self._UPDATE_PACKAGE,
            path_params={"packageId": str(package_id)},
            json=payload,
        )
        return _expect_dict(response)

    def delete_package(self, package_id: PackageId | str) -> None:
        self._client.delete(self._DELETE_PACKAGE, path_params={"packageId": str(package_id)})

    def get_package(self, package_id: PackageId | str) -> dict | None:
        response = self._client.get(self._GET_PACKAGE, path_params={"packageId": str(package_id)})
        return _safe_json(response)

    def get_packages_for_project(self, project_id: ProjectId | None = None) -> List[dict]:
        project = project_id or self._session.require_project()
        response = self._client.get(self._GET_PACKAGES_FOR_PROJECT, path_params={"projectId": str(project)})
        return _safe_json(response)

    def wait_for_package(self, package_id: PackageId | str, *, timeout_seconds: float = 600.0, poll_interval: float = 3.0) -> dict:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                package = self.get_package(package_id)
                if package:
                    return package
            except WebmateApiError as exc:  # pragma: no cover - remote
                last_error = exc
            time.sleep(poll_interval)
        raise WebmateApiError(f"Package {package_id} not ready", payload=getattr(last_error, "payload", None))

    def upload_and_create_package(
        self,
        binary: bytes,
        *,
        name: str,
        extension: str,
        content_type: str | None = None,
        project_id: ProjectId | None = None,
    ) -> dict:
        project = project_id or self._session.require_project()
        blob_id = self._blob_client.put_blob(binary, project_id=project, content_type=content_type)
        return self.create_package(blob_id, name, extension, project_id=project)


def _expect_dict(response) -> dict:
    payload = _safe_json(response)
    if isinstance(payload, dict):
        return payload
    raise WebmateApiError("Unexpected package response", payload=payload)


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


__all__ = ["PackageMgmtClient"]
