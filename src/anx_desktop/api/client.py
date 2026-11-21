"""HTTP transport and the public :class:`AnixartClient` facade.

Contract sources: ``docs/api.md`` §2 (hosts), §3 (transport rules), §4.8
(token as a query parameter), §4.11 (401/402/403 handling).

Design decisions
----------------
* **Synchronous ``httpx.Client``.**  The desktop connector is a request/response
  API with path-based pagination; a sync client is simpler to use from the
  PySide6 UI thread pool and from tests.  There is no WebSocket/streaming
  contract in the docs (§2.3).
* **One client instance** owns base URL, headers, timeouts, connection limits
  and retries.  Tests can inject any ``httpx.BaseTransport`` (``MockTransport``,
  ``respx``) through the constructor.
* **Retries only for explicitly idempotent calls.**  The docs warn that many
  state-changing operations are HTTP ``GET`` (§3.1).  Endpoint methods therefore
  mark read-only requests as idempotent; mutations are never retried, even when
  they use ``GET``.
* **Token redaction.**  The token travels in the query string (§4.8).  This
  module logs only method + path, never query strings, headers or bodies.  On
  transport errors the original httpx exception is suppressed (``from None``)
  because it may contain the full URL with the token.
"""

from __future__ import annotations

import importlib
import logging
import threading
import time
from collections.abc import Callable, Mapping
from types import TracebackType
from typing import Any, Protocol, Self, TypeVar

import httpx
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from .auth import AuthEndpoints, MemoryTokenStore, StoredToken, TokenStore
from .errors import (
    AuthError,
    NetworkError,
    ValidationError,
    error_for_app_code,
    error_for_http_status,
)
from .models import AnixartModel, ProfileToken
from .pagination import Paginator

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api-s.anixsekai.com/"
"""Default API base from docs/api.md §2.1.  It is configurable on purpose."""

DEFAULT_USER_AGENT = "AnixartApp/11 BETA 2-26103015 (desktop; anx-desktop/0.1.0)"
"""Documented UA format (§3.2), adapted for a desktop client.

Android anti-tamper headers are supplied by an optional local module loaded
through ``anti_tamper`` (see ``tasks/07-anti-tamper-user-apk.md``).  A clean
checkout sends none; ``X-Codec-Profile``/``X-Media-Session`` additionally need
a native 72-byte codec profile.
"""

RETRY_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
"""Transient statuses.  Retried only for explicitly idempotent requests."""

T = TypeVar("T", bound=AnixartModel)


class HeaderProvider(Protocol):
    """Per-request header source (e.g. a local anti-tamper provider)."""

    def headers(self, *, now_ms: int | None = None) -> dict[str, str]: ...


def _load_default_anti_tamper() -> HeaderProvider | None:
    """Load the optional local anti-tamper module, if present.

    The implementation is intentionally not part of the repository for now;
    the tracked replacement is ``tasks/07-anti-tamper-user-apk.md``.  A clean
    checkout therefore simply runs without anti-tamper headers.
    """

    try:
        module = importlib.import_module(".antitamper", __package__)
    except ImportError:
        return None
    factory = getattr(module, "AntiTamper", None)
    if factory is None:  # pragma: no cover - defensive
        return None
    return factory()


class AnixartClient:
    """Synchronous Anixart API client.

    Parameters
    ----------
    base_url:
        API host root.  The docs say paths have no ``/v1`` or ``/api`` prefix
        (§2.1); a trailing slash is added automatically.
    token_store:
        Persistence for the opaque session token.  Defaults to
        :class:`~anx_desktop.api.auth.MemoryTokenStore` (no disk writes).
    transport:
        Optional ``httpx`` transport for tests (``MockTransport``/``respx``).
    timeout:
        Total request timeout in seconds, or an ``httpx.Timeout``.
    max_retries:
        Number of additional attempts for idempotent requests and transient
        statuses.  Defaults to ``2``; mutations are never retried.
    backoff_factor:
        Exponential backoff base in seconds.  ``Retry-After`` wins when present.
    headers:
        Additional default headers.  Anti-tamper headers from ``anti_tamper``
        are merged first and these values override them on conflict.
    anti_tamper:
        Optional provider of Android anti-tamper headers.  When omitted, the
        client tries to load the local anti-tamper module; if it is absent
        (clean checkout), no anti-tamper headers are sent.  Any object with a
        ``headers(now_ms=...)`` method is accepted.
    user_agent:
        Override for the documented ``User-Agent`` format.
    sleep:
        Injectable sleep function, used by tests to avoid real delays.
    follow_redirects:
        Let httpx follow redirects; the docs do not fully specify HTTP→HTTPS
        behavior (§9 U-26).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        token_store: TokenStore | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float | httpx.Timeout = 30.0,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        headers: Mapping[str, str] | None = None,
        anti_tamper: HeaderProvider | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        sleep: Callable[[float], None] = time.sleep,
        follow_redirects: bool = True,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")

        normalised_base = base_url.rstrip("/") + "/"
        self._base_url = normalised_base
        self._token_store: TokenStore = token_store or MemoryTokenStore()
        self._token_lock = threading.RLock()
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._sleep = sleep
        self._anti_tamper = (
            anti_tamper if anti_tamper is not None else _load_default_anti_tamper()
        )

        self._default_headers: dict[str, str] = dict(headers or {})
        default_headers: dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        if isinstance(timeout, (int, float)):
            timeout_config = httpx.Timeout(
                float(timeout),
                connect=min(10.0, float(timeout)),
                pool=min(10.0, float(timeout)),
            )
        else:
            timeout_config = timeout

        self._http = httpx.Client(
            base_url=normalised_base,
            headers=default_headers,
            timeout=timeout_config,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            ),
            transport=transport,
            follow_redirects=follow_redirects,
        )

        # Domain facades.  Imports are local to avoid a cycle at module import
        # time: endpoint modules import AnixartClient only under TYPE_CHECKING.
        from .endpoints.comments import CommentEndpoints
        from .endpoints.config import ConfigEndpoints
        from .endpoints.episodes import EpisodeEndpoints
        from .endpoints.feed import FeedEndpoints
        from .endpoints.history import HistoryEndpoints
        from .endpoints.notifications import NotificationEndpoints
        from .endpoints.profile import ProfileEndpoints
        from .endpoints.releases import ReleaseEndpoints
        from .endpoints.search import SearchEndpoints

        self.auth = AuthEndpoints(self)
        self.config = ConfigEndpoints(self)
        self.feed = FeedEndpoints(self)
        self.releases = ReleaseEndpoints(self)
        self.search = SearchEndpoints(self)
        self.comments = CommentEndpoints(self)
        self.profile = ProfileEndpoints(self)
        self.history = HistoryEndpoints(self)
        self.episodes = EpisodeEndpoints(self)
        self.notifications = NotificationEndpoints(self)

    # -- token entry points ------------------------------------------------

    @property
    def base_url(self) -> str:
        """Normalised base URL used by this client."""

        return self._base_url

    @property
    def session(self) -> StoredToken | None:
        """Current session snapshot, if any."""

        with self._token_lock:
            return self._token_store.load()

    @property
    def token(self) -> str | None:
        """Current opaque token, if any.  Do not log this value."""

        session = self.session
        return session.token if session and session.token else None

    @property
    def is_authenticated(self) -> bool:
        """Whether a non-empty session token is stored."""

        return self.token is not None

    def set_token(
        self,
        token: StoredToken | ProfileToken | str | None,
        *,
        profile_id: int | None = None,
    ) -> None:
        """Single entry point for installing or clearing a session token.

        Passing ``None`` or an empty token clears the session.  The operation is
        protected by a re-entrant lock so concurrent login/401 handling cannot
        leave a half-updated store.
        """

        with self._token_lock:
            if token is None:
                self._token_store.clear()
                return

            if isinstance(token, StoredToken):
                stored = token
            elif isinstance(token, ProfileToken):
                stored = StoredToken(
                    token=token.token,
                    profile_id=profile_id if profile_id is not None else token.id,
                )
            elif isinstance(token, str):
                stored = StoredToken(token=token, profile_id=profile_id)
            else:  # pragma: no cover - defensive
                raise TypeError(f"unsupported token type: {type(token)!r}")

            if not stored.token:
                self._token_store.clear()
                return
            self._token_store.save(stored)

    def clear_token(self) -> None:
        """Single entry point for invalidating the local session."""

        with self._token_lock:
            self._token_store.clear()

    # -- public request helpers -------------------------------------------

    def paginator(
        self,
        fetch_page: Callable[[int], Any],
        *,
        start_page: int = 1,
        max_pages: int | None = None,
    ) -> Paginator[Any]:
        """Create a :class:`~anx_desktop.api.pagination.Paginator`."""

        return Paginator(fetch_page, start_page=start_page, max_pages=max_pages)

    # -- internal transport ------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        form: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool = True,
        require_token: bool = True,
        send_empty_token: bool = False,
        idempotent: bool = False,
    ) -> httpx.Response:
        """Send one request, injecting the token query parameter when needed."""

        request_params = self._normalise_params(params)
        if authenticated:
            session = self.session
            if session and session.token:
                request_params["token"] = session.token
            elif require_token:
                raise AuthError(
                    "Authentication required: no session token is stored",
                    path=path,
                )
            elif send_empty_token:
                # §4.11: config endpoints may be called before login with an
                # empty token; guest acceptance is UNKNOWN (U-08).
                request_params["token"] = ""

        request_headers = (
            self._anti_tamper.headers() if self._anti_tamper is not None else {}
        )
        request_headers.update(self._default_headers)
        if headers:
            request_headers.update(headers)
        request_form = self._normalise_params(form) if form is not None else None

        # Log only the path: the token lives in the query string (§4.8).
        logger.debug("%s %s", method.upper(), path)

        try:
            response = self._send_with_retries(
                method,
                path,
                params=request_params or None,
                json_body=json_body,
                form=request_form,
                headers=request_headers or None,
                idempotent=idempotent,
            )
        except httpx.HTTPError:
            # Do not chain the httpx exception: its message may include the
            # full URL and therefore the session token.
            logger.warning("Network failure for %s %s", method.upper(), path)
            raise NetworkError(
                f"Network failure during {method.upper()} {path}",
                path=path,
            ) from None

        self._check_response(response, method=method, path=path, authenticated=authenticated)
        return response

    def _send_with_retries(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None,
        json_body: Any | None,
        form: Mapping[str, Any] | None,
        headers: Mapping[str, str] | None,
        idempotent: bool,
    ) -> httpx.Response:
        attempts = self._max_retries + 1

        for attempt in range(attempts):
            try:
                response = self._http.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                    data=form,
                    headers=headers,
                )
            except httpx.TransportError:
                if idempotent and attempt < attempts - 1:
                    self._sleep(self._backoff_delay(attempt, retry_after=None))
                    continue
                raise

            if (
                idempotent
                and response.status_code in RETRY_STATUS_CODES
                and attempt < attempts - 1
            ):
                retry_after = self._parse_retry_after(response)
                response.close()
                self._sleep(self._backoff_delay(attempt, retry_after=retry_after))
                continue

            return response

        raise AssertionError("retry loop exhausted unexpectedly")  # pragma: no cover

    def _check_response(
        self,
        response: httpx.Response,
        *,
        method: str,
        path: str,
        authenticated: bool,
    ) -> None:
        if response.is_success:
            return

        body = self._decode_body(response)
        retry_after = self._parse_retry_after(response)

        if response.status_code == 401 and authenticated:
            # §4.11 recommends clearing the session; there is no refresh flow.
            self.clear_token()

        logger.warning(
            "HTTP %s for %s %s",
            response.status_code,
            method.upper(),
            path,
        )
        raise error_for_http_status(
            response.status_code,
            body,
            path=path,
            retry_after=retry_after,
        )

    # -- response decoding -------------------------------------------------

    def _request_data(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        return self._decode_success(response, method=method, path=path)

    def _request_model(self, model_type: type[T], method: str, path: str, **kwargs: Any) -> T:
        """Request a JSON object and validate it with a pydantic model."""

        data = self._request_data(method, path, **kwargs)
        if data is None:
            data = {}
        try:
            return model_type.model_validate(data)
        except PydanticValidationError as exc:
            raise ValidationError(
                "Response payload does not match the documented model",
                status_code=200,
                code=self._extract_code(data),
                body=data,
                path=path,
            ) from exc

    def _request_list(self, item_type: type[T], method: str, path: str, **kwargs: Any) -> list[T]:
        """Request a bare JSON array (some documented endpoints return one)."""

        data = self._request_data(method, path, **kwargs)
        try:
            return TypeAdapter(list[item_type]).validate_python(data)  # type: ignore[misc]
        except PydanticValidationError as exc:
            raise ValidationError(
                "Response array does not match the documented model",
                status_code=200,
                body=data,
                path=path,
            ) from exc

    def _decode_success(self, response: httpx.Response, *, method: str, path: str) -> Any:
        data = self._decode_body(response)
        code = self._extract_code(data)
        if code is not None and code != 0:
            logger.warning(
                "Application code %s for %s %s", code, method.upper(), path
            )
            raise error_for_app_code(
                code,
                data,
                status_code=response.status_code,
                path=path,
            )
        return data

    @staticmethod
    def _decode_body(response: httpx.Response) -> Any:
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _extract_code(data: Any) -> int | None:
        if isinstance(data, dict):
            value = data.get("code")
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None

    @staticmethod
    def _normalise_params(values: Mapping[str, Any] | None) -> dict[str, Any]:
        if not values:
            return {}
        normalised: dict[str, Any] = {}
        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, bool):
                normalised[key] = "true" if value else "false"
            else:
                normalised[key] = value
        return normalised

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            parsed = float(value)
        except ValueError:
            # HTTP-date form is not documented for this API; ignore it.
            return None
        return max(parsed, 0.0)

    def _backoff_delay(self, attempt: int, *, retry_after: float | None) -> float:
        if retry_after is not None:
            return retry_after
        return self._backoff_factor * (2**attempt)

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        """Close the underlying ``httpx.Client``."""

        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_USER_AGENT",
    "RETRY_STATUS_CODES",
    "AnixartClient",
]
