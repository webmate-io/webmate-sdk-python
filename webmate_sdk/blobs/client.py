"""Blob subsystem facade."""
from __future__ import annotations

from typing import Optional

from ..http import ApiClient, UriTemplate
from ..ids import BlobId, ProjectId
from ..session import WebmateSession


class BlobClient:
    _PUT_BLOB = UriTemplate("/projects/{projectId}/blobs", name="PutBlob")
    _DELETE_BLOB = UriTemplate("/blobs/{blobId}", name="DeleteBlob")

    def __init__(self, session: WebmateSession) -> None:
        self._session = session
        self._client = ApiClient(session.auth, session.environment)

    def put_blob(self, blob: bytes, *, project_id: ProjectId | None = None, content_type: str | None = None) -> BlobId:
        project = project_id or self._session.require_project()
        headers = {"Content-Type": content_type} if content_type else None
        response = self._client.post(
            self._PUT_BLOB,
            path_params={"projectId": str(project)},
            data=blob,
            headers=headers,
        )
        payload = _safe_json(response, allow_text=True)
        return BlobId.parse(payload)

    def delete_blob(self, blob_id: BlobId | str) -> None:
        self._client.delete(self._DELETE_BLOB, path_params={"blobId": str(blob_id)})


def _safe_json(response, *, allow_text: bool = False):
    try:
        return response.json()
    except ValueError:
        if allow_text:
            return response.text.strip().strip('"')
        return None


__all__ = ["BlobClient"]
