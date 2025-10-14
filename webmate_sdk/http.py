"""HTTP client used by higher level service facades."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping, Optional
from urllib.parse import urlencode

import requests

from .auth import AuthInfo
from .environment import WebmateEnvironment
from .exceptions import WebmateApiError

DEFAULT_TIMEOUT = (5, 60)  # (connect, read)
SUCCESS_STATUSES = {200, 201, 202, 204}


@dataclass(frozen=True)
class UriTemplate:
    path: str
    name: Optional[str] = None

    def expand(self, path_params: Optional[Mapping[str, Any]] = None) -> str:
        path_params = path_params or {}
        safe_params = {key: _stringify(value) for key, value in path_params.items()}
        return self.path.format(**safe_params)


class ApiClient:
    """Lightweight wrapper around :mod:`requests` with webmate-specific defaults."""

    def __init__(
        self,
        auth: AuthInfo,
        environment: WebmateEnvironment,
        *,
        timeout: tuple[float, float] | float = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._auth = auth
        self._environment = environment
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({
            "User-Agent": "webmate-python-sdk",
            "Accept": "application/json",
        })
        self._session.headers.update(auth.headers())

    def close(self) -> None:
        self._session.close()

    def request(
        self,
        method: str,
        template: UriTemplate | str,
        *,
        path_params: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        json: Any | None = None,
        data: Any | None = None,
        headers: Optional[Mapping[str, str]] = None,
        expected: Iterable[int] = SUCCESS_STATUSES,
        stream: bool = False,
    ) -> requests.Response:
        if isinstance(template, UriTemplate):
            path = template.expand(path_params)
            name = template.name or template.path
        else:
            path = str(template)
            name = path
        url = self._environment.resolve(path)
        params = _filter_none(query)
        session_headers: dict[str, str] = {}
        if headers:
            session_headers.update(headers)
        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=session_headers or None,
                timeout=self._timeout,
                stream=stream,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise WebmateApiError(f"{name}: request failed: {exc}") from exc

        if response.status_code not in set(expected):
            payload: Any
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            raise WebmateApiError(
                f"{name}: unexpected status {response.status_code}",
                status_code=response.status_code,
                payload=payload,
            )
        return response

    def get(
        self,
        template: UriTemplate | str,
        *,
        path_params: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        expected: Iterable[int] = SUCCESS_STATUSES,
        stream: bool = False,
    ) -> requests.Response:
        return self.request("GET", template, path_params=path_params, query=query, expected=expected, stream=stream)

    def post(
        self,
        template: UriTemplate | str,
        *,
        path_params: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
        json: Any | None = None,
        data: Any | None = None,
        headers: Optional[Mapping[str, str]] = None,
        expected: Iterable[int] = SUCCESS_STATUSES,
    ) -> requests.Response:
        return self.request(
            "POST",
            template,
            path_params=path_params,
            query=query,
            json=json,
            data=data,
            headers=headers,
            expected=expected,
        )

    def put(
        self,
        template: UriTemplate | str,
        *,
        path_params: Optional[Mapping[str, Any]] = None,
        json: Any | None = None,
        expected: Iterable[int] = SUCCESS_STATUSES,
    ) -> requests.Response:
        return self.request("PUT", template, path_params=path_params, json=json, expected=expected)

    def delete(
        self,
        template: UriTemplate | str,
        *,
        path_params: Optional[Mapping[str, Any]] = None,
        expected: Iterable[int] = SUCCESS_STATUSES,
    ) -> requests.Response:
        return self.request("DELETE", template, path_params=path_params, expected=expected)


def _filter_none(query: Optional[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not query:
        return None
    return {key: _stringify(value) for key, value in query.items() if value is not None}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "to_json"):
        return str(value.to_json())
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return str(value.value)
    return str(value)


__all__ = ["ApiClient", "UriTemplate", "DEFAULT_TIMEOUT"]
