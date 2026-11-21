"""Exceptions and HTTP/application-code mapping for the Anixart connector.

The mapping is derived from ``docs/api.md``:

* §3.5 — HTTP-level behavior and base application codes ``0/1/402/403``.
* §4.11 — recommended handling of ``401``, ``402`` and ``403``.
* §7.1 — application-code values for auth flows.

The exception classes deliberately keep the raw response body.  The
documentation does not describe a common error envelope, so callers must be
able to inspect the original payload themselves.
"""

from __future__ import annotations

from typing import Any


class AnixartError(Exception):
    """Base error for every connector failure.

    Parameters
    ----------
    message:
        Human-readable description.  It must never contain a session token.
    status_code:
        HTTP status code, if the failure came from an HTTP response.
    code:
        Application-level ``code`` from the response body, if present.
    body:
        Parsed response body (JSON when possible, otherwise text).
    path:
        Request path **without** the query string, so tokens are not exposed.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: int | None = None,
        body: Any | None = None,
        path: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.body = body
        self.path = path

    def __str__(self) -> str:
        details: list[str] = []
        if self.status_code is not None:
            details.append(f"HTTP {self.status_code}")
        if self.code is not None:
            details.append(f"code {self.code}")
        if self.path is not None:
            details.append(self.path)
        if not details:
            return self.message
        return f"{self.message} ({', '.join(details)})"


class AuthError(AnixartError):
    """Authentication/session failure (HTTP 401, or app codes 402/403).

    The Android client has no refresh endpoint (§4.9).  A 401 therefore means
    that the user must sign in again.
    """


class RateLimitError(AnixartError):
    """HTTP 429 or a server-side throttling response.

    ``retry_after`` is populated when the server sends a ``Retry-After``
    header.  Its presence was not observed statically (§3.6), so it is
    optional.
    """

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NotFoundError(AnixartError):
    """HTTP 404 (or an endpoint-specific "not found" application code)."""


class ValidationError(AnixartError):
    """Invalid request or endpoint-specific negative application code.

    This is the connector's own exception.  It is intentionally separate from
    :class:`pydantic.ValidationError`, which is raised for malformed response
    payloads and is converted into this class by the client.
    """


class ServerError(AnixartError):
    """HTTP 5xx response."""


class NetworkError(AnixartError):
    """Transport-level failure (DNS, connect, read timeout, etc.)."""


_BANNED_APP_CODES = frozenset({402, 403})


def _body_message(body: Any) -> str | None:
    """Return a server-provided message when one happens to be present.

    ``docs/api.md`` §3.5 explicitly says there is no observed common error
    envelope with a message field.  This helper only uses a message when the
    server sends one anyway; it never assumes that the field exists.
    """

    if isinstance(body, dict):
        for key in ("message", "error", "description"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _app_code(body: Any) -> int | None:
    if isinstance(body, dict):
        value = body.get("code")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def error_for_http_status(
    status_code: int,
    body: Any,
    *,
    path: str | None = None,
    retry_after: float | None = None,
) -> AnixartError:
    """Map an HTTP status to the connector exception hierarchy."""

    server_message = _body_message(body)
    suffix = f": {server_message}" if server_message else ""
    code = _app_code(body)

    if status_code == 401:
        return AuthError("Invalid or expired session" + suffix, status_code=401, code=code, body=body, path=path)
    if status_code in (402, 403):
        return AuthError("Account is banned" + suffix, status_code=status_code, code=code, body=body, path=path)
    if status_code == 404:
        return NotFoundError("Resource not found" + suffix, status_code=404, code=code, body=body, path=path)
    if status_code == 429:
        return RateLimitError(
            "Rate limit exceeded" + suffix,
            status_code=429,
            code=code,
            body=body,
            path=path,
            retry_after=retry_after,
        )
    if 500 <= status_code <= 599:
        return ServerError("Server error" + suffix, status_code=status_code, code=code, body=body, path=path)
    if 400 <= status_code <= 499:
        return ValidationError("Request rejected" + suffix, status_code=status_code, code=code, body=body, path=path)
    return AnixartError("Unexpected HTTP response" + suffix, status_code=status_code, code=code, body=body, path=path)


def error_for_app_code(
    code: int,
    body: Any,
    *,
    status_code: int | None = None,
    path: str | None = None,
) -> AnixartError:
    """Map a non-zero application ``code`` from a successful HTTP response.

    Endpoint-specific codes are not fully documented (§3.5, §9 U-11/U-12).
    Codes that are not bans are therefore surfaced as :class:`ValidationError`
    with the original body and numeric code preserved.
    """

    server_message = _body_message(body)
    suffix = f": {server_message}" if server_message else ""

    if code in _BANNED_APP_CODES:
        return AuthError("Account is banned" + suffix, status_code=status_code, code=code, body=body, path=path)
    if code == 1:
        return AnixartError("Generic API failure" + suffix, status_code=status_code, code=code, body=body, path=path)
    return ValidationError(
        f"API rejected the request with code {code}" + suffix,
        status_code=status_code,
        code=code,
        body=body,
        path=path,
    )


__all__ = [
    "AnixartError",
    "AuthError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "error_for_app_code",
    "error_for_http_status",
]
