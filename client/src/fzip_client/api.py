"""HTTP client for the FZIP Locker API.

Replaces the 2022 ``client_socket.py``, which spoke a bespoke protocol over a
plaintext socket -- a 3-byte handshake, an 8-digit length prefix, then a
pickled dict. That design had three separate problems: the payload was
unpickled server-side (remote code execution), ``recv(length)`` assumed a
single TCP segment (silent truncation on large payloads), and nothing was
encrypted in transit.

This module sends JSON and multipart over TLS, and never sends the archive
password or file contents anywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .config import ClientConfig
from .errors import ApiError, AuthRequiredError, NetworkError
from .session import Session

Frames = list[bytes]


def _problem_to_error(response: httpx.Response) -> ApiError:
    """Turn an RFC 9457 problem document into a typed exception."""
    slug = "unknown"
    detail = f"HTTP {response.status_code}"
    try:
        body = response.json()
    except ValueError:
        return ApiError(response.status_code, slug, detail)

    if isinstance(body, dict):
        slug = str(body.get("type", "")).rsplit("/", 1)[-1] or slug
        detail = str(body.get("detail", detail))
        # Field-level validation errors are more useful than the generic text.
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                detail = f"{first.get('field', '')}: {first.get('message', detail)}"
    return ApiError(response.status_code, slug, detail)


class FzipApi:
    """Synchronous API client.

    Synchronous on purpose: it is always called from a background worker
    thread (see ``ui.workers``), never from the Qt event loop, so async would
    add a second concurrency model for no benefit.
    """

    def __init__(self, config: ClientConfig, session: Session) -> None:
        self._config = config
        self._session = session
        self._http = httpx.Client(
            base_url=config.api_url,
            verify=config.verify,
            timeout=config.request_timeout,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> FzipApi:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # -- plumbing ---------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = False,
        retry_on_expiry: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        headers: dict[str, str] = dict(kwargs.pop("headers", {}))
        if authenticated:
            if not self._session.access_token:
                raise AuthRequiredError
            headers["Authorization"] = f"Bearer {self._session.access_token}"

        try:
            response = self._http.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise NetworkError(str(exc)) from exc

        if response.is_success:
            return response

        error = _problem_to_error(response)

        # A 15-minute access token will routinely expire mid-session. Refresh
        # once and retry transparently rather than bouncing the user to the
        # sign-in screen.
        if (
            authenticated
            and retry_on_expiry
            and error.type_slug == "token-expired"
            and self._session.refresh_token
        ):
            self.refresh()
            return self._request(
                method, path, authenticated=True, retry_on_expiry=False, **kwargs
            )

        if error.type_slug in {"token-reused", "authentication-required"}:
            self._session.clear()
            raise AuthRequiredError(error.detail)

        raise error

    @staticmethod
    def _frame_files(frames: Frames) -> list[tuple[str, tuple[str, bytes, str]]]:
        return [
            ("frames", (f"frame-{i:02d}.jpg", data, "image/jpeg"))
            for i, data in enumerate(frames)
        ]

    # -- auth -------------------------------------------------------------
    def register(self, email: str, password: str, frames: Frames) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/api/v1/auth/register",
            data={"email": email, "password": password},
            files=self._frame_files(frames),
        )
        tokens: dict[str, Any] = response.json()
        self._session.email = email
        self._session.adopt(tokens)
        return tokens

    def login(self, email: str, password: str) -> dict[str, Any]:
        response = self._request(
            "POST", "/api/v1/auth/login", json={"email": email, "password": password}
        )
        tokens: dict[str, Any] = response.json()
        self._session.email = email
        self._session.adopt(tokens)
        return tokens

    def refresh(self) -> dict[str, Any]:
        if not self._session.refresh_token:
            raise AuthRequiredError
        try:
            response = self._request(
                "POST",
                "/api/v1/auth/refresh",
                json={"refresh_token": self._session.refresh_token},
            )
        except ApiError as exc:
            self._session.clear()
            raise AuthRequiredError(exc.detail) from exc

        tokens: dict[str, Any] = response.json()
        self._session.adopt(tokens)
        return tokens

    def logout(self) -> None:
        token = self._session.refresh_token
        if token:
            try:
                self._request("POST", "/api/v1/auth/logout", json={"refresh_token": token})
            except (ApiError, NetworkError, AuthRequiredError):
                # Local sign-out must succeed even if the server is gone.
                pass
        self._session.clear()

    def me(self) -> dict[str, Any]:
        body: dict[str, Any] = self._request(
            "GET", "/api/v1/auth/me", authenticated=True
        ).json()
        return body

    # -- face -------------------------------------------------------------
    def face_challenge(self) -> dict[str, Any]:
        body: dict[str, Any] = self._request(
            "POST", "/api/v1/face/challenge", authenticated=True
        ).json()
        return body

    def face_verify(self, nonce: str, frames: Frames) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/api/v1/face/verify",
            authenticated=True,
            data={"nonce": nonce},
            files=self._frame_files(frames),
        )
        body: dict[str, Any] = response.json()
        self._session.face_token = str(body.get("face_token", ""))
        return body

    # -- health -----------------------------------------------------------
    def reachable(self) -> bool:
        try:
            return self._http.get("/healthz").is_success
        except httpx.HTTPError:
            return False


def ca_bundle_hint(config: ClientConfig) -> str | None:
    """Guidance for the most common first-run TLS failure."""
    if config.verify is True and config.api_url.startswith("https://localhost"):
        return (
            "No local CA certificate found. Start the backend with "
            "`docker compose up -d`, wait for ./certs/root.crt to appear, then "
            "relaunch. Alternatively set FZIP_CA_BUNDLE to its path."
        )
    if isinstance(config.verify, str) and not Path(config.verify).is_file():
        return f"FZIP_CA_BUNDLE points at {config.verify}, which does not exist."
    return None
