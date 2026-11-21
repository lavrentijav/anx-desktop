"""Authentication flows and session-token storage.

Contract source: ``docs/api.md`` §4 (authorization) and §5.1 (auth endpoints).

Important findings from the docs that shape this module:

* the session token is an **opaque query parameter** (§4.8), not a bearer
  token;
* there is no access/refresh-token pair, no ``expires_in`` and no refresh
  endpoint (§4.1, §4.9);
* there is no TOTP endpoint.  The only second factor is the e-mail code used by
  sign-up/restore and confirmed with ``POST /auth/verify`` (§4.3);
* logout is local-only; server-side revocation was not found (§4.10).

``TokenStore`` keeps persistence outside the library.  The default
``MemoryTokenStore`` is thread-safe and never writes to disk; callers can plug
in an OS-keyring implementation without changing the client.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from .errors import AnixartError, AuthError, ValidationError
from .models import (
    AnixartModel,
    CheckLoginResponse,
    FirebaseResponse,
    GoogleResponse,
    QrAuthResponse,
    ResendResponse,
    RestoreResendResponse,
    RestoreResponse,
    RestoreVerifyResponse,
    SignInResponse,
    SignUpResponse,
    TelegramResponse,
    VerifyResponse,
    VkResponse,
    YandexResponse,
)

if TYPE_CHECKING:
    from .client import AnixartClient

M = TypeVar("M", bound=AnixartModel)


@dataclass(frozen=True, slots=True)
class StoredToken:
    """Serializable session state kept by a :class:`TokenStore`."""

    token: str
    profile_id: int | None = None


@runtime_checkable
class TokenStore(Protocol):
    """Persistence interface for the opaque session token.

    Implementations must be safe to call from multiple threads.  The connector
    only calls ``load/save/clear``; it never logs the token.
    """

    def load(self) -> StoredToken | None:
        """Return the stored session, or ``None`` when logged out."""

    def save(self, token: StoredToken) -> None:
        """Persist a session token."""

    def clear(self) -> None:
        """Remove the session token."""


class MemoryTokenStore:
    """Default in-memory :class:`TokenStore` with a re-entrant lock."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._token: StoredToken | None = None

    def load(self) -> StoredToken | None:
        with self._lock:
            return self._token

    def save(self, token: StoredToken) -> None:
        with self._lock:
            self._token = token

    def clear(self) -> None:
        with self._lock:
            self._token = None


class AuthEndpoints:
    """Authentication methods bound to an :class:`AnixartClient`."""

    def __init__(self, client: AnixartClient) -> None:
        self._client = client

    # -- internal helpers -------------------------------------------------

    def _auth_model(self, model_type: type[M], method: str, path: str, **kwargs: Any) -> M:
        """Perform an auth request and surface business codes as ``AuthError``.

        Auth endpoint codes ``2..11`` are credential/flow failures (§7.1).
        Transport errors and rate limits keep their own exception types.
        """

        try:
            return self._client._request_model(model_type, method, path, **kwargs)
        except AuthError:
            raise
        except ValidationError as exc:
            # Only documented business codes (2..11) are credential failures;
            # a malformed response model must stay a validation error.
            if exc.code is not None and exc.code != 0:
                raise AuthError(
                    str(exc),
                    status_code=exc.status_code,
                    code=exc.code,
                    body=exc.body,
                    path=exc.path,
                ) from exc
            raise
        except AnixartError:
            raise

    def _store_session(
        self,
        response: AnixartModel,
        *,
        required: bool,
        context: str,
    ) -> None:
        """Single point where a successful auth response updates the token."""

        profile_token = getattr(response, "profile_token", None)
        profile = getattr(response, "profile", None)

        if required and profile is None:
            raise AuthError(
                f"{context}: docs/api.md §4.2 requires a non-null profile on success"
            )

        if profile_token is None or not profile_token.token:
            if required:
                raise AuthError(
                    f"{context}: docs/api.md §4.2 requires profileToken.token on success"
                )
            return

        profile_id = getattr(profile, "id", None) or profile_token.id
        self._client.set_token(profile_token, profile_id=profile_id)

    # -- password login ---------------------------------------------------

    def login(self, login: str, password: str) -> SignInResponse:
        """``POST /auth/signIn`` — docs/api.md §4.2, §5.1 (S#44).

        The server returns ``{code, profile, profileToken}``.  Both ``profile``
        and ``profileToken`` must be non-null on success; the token is stored
        immediately through the client's single token entry point.
        """

        response = self._auth_model(
            SignInResponse,
            "POST",
            "/auth/signIn",
            form={"login": login, "password": password},
            authenticated=False,
            idempotent=False,
        )
        self._store_session(response, required=True, context="sign-in")
        return response

    def check_login(self, login: str) -> CheckLoginResponse:
        """``POST /auth/checkLogin`` — docs/api.md §4.3, §5.1 (S#31).

        Returns login availability and suggested alternatives.  This is a
        read-only POST; retries are safe.
        """

        return self._auth_model(
            CheckLoginResponse,
            "POST",
            "/auth/checkLogin",
            form={"login": login},
            authenticated=False,
            idempotent=True,
        )

    # -- registration / e-mail second factor ------------------------------

    def sign_up(self, login: str, email: str, password: str) -> SignUpResponse:
        """``POST /auth/signUp`` with ``X-Long-Code: 1`` — §4.3 (S#45).

        The response carries a transaction ``hash`` and code timing.  The
        second factor is the e-mail code, verified by :meth:`verify`.
        """

        return self._auth_model(
            SignUpResponse,
            "POST",
            "/auth/signUp",
            form={"login": login, "email": email, "password": password},
            headers={"X-Long-Code": "1"},
            authenticated=False,
            idempotent=False,
        )

    def verify(
        self,
        *,
        hash: str,
        code: str,
        login: str | None = None,
        email: str | None = None,
        password: str | None = None,
        vk_access_token: str | None = None,
        google_id_token: str | None = None,
        telegram_id_token: str | None = None,
        yandex_access_token: str | None = None,
    ) -> VerifyResponse:
        """``POST /auth/verify`` — e-mail second-factor completion, §4.3 (S#48).

        On success the response contains ``profile`` and ``profileToken``; the
        token is saved through the client's single token entry point.
        """

        form = {
            "login": login,
            "email": email,
            "password": password,
            "vkAccessToken": vk_access_token,
            "googleIdToken": google_id_token,
            "telegramIdToken": telegram_id_token,
            "yandexAccessToken": yandex_access_token,
            "hash": hash,
            "code": code,
        }
        response = self._auth_model(
            VerifyResponse,
            "POST",
            "/auth/verify",
            form=form,
            authenticated=False,
            idempotent=False,
        )
        self._store_session(response, required=True, context="verify")
        return response

    def resend(
        self,
        *,
        hash: str,
        login: str | None = None,
        email: str | None = None,
        password: str | None = None,
        vk_access_token: str | None = None,
        google_id_token: str | None = None,
        telegram_id_token: str | None = None,
        yandex_access_token: str | None = None,
    ) -> ResendResponse:
        """``POST /auth/resend`` with ``X-Long-Code: 1`` — §4.3 (S#40)."""

        form = {
            "login": login,
            "email": email,
            "password": password,
            "vkAccessToken": vk_access_token,
            "googleIdToken": google_id_token,
            "telegramIdToken": telegram_id_token,
            "yandexAccessToken": yandex_access_token,
            "hash": hash,
        }
        return self._auth_model(
            ResendResponse,
            "POST",
            "/auth/resend",
            form=form,
            headers={"X-Long-Code": "1"},
            authenticated=False,
            idempotent=False,
        )

    # -- password restore -------------------------------------------------

    def restore(self, data: str) -> RestoreResponse:
        """``POST /auth/restore`` with ``X-Long-Code: 1`` — §4.4 (S#41)."""

        return self._auth_model(
            RestoreResponse,
            "POST",
            "/auth/restore",
            form={"data": data},
            headers={"X-Long-Code": "1"},
            authenticated=False,
            idempotent=False,
        )

    def restore_resend(self, *, data: str, password: str, hash: str) -> RestoreResendResponse:
        """``POST /auth/restore/resend`` — §4.4 (S#42)."""

        return self._auth_model(
            RestoreResendResponse,
            "POST",
            "/auth/restore/resend",
            form={"data": data, "password": password, "hash": hash},
            headers={"X-Long-Code": "1"},
            authenticated=False,
            idempotent=False,
        )

    def restore_verify(
        self,
        *,
        data: str,
        password: str,
        hash: str,
        code: str,
    ) -> RestoreVerifyResponse:
        """``POST /auth/restore/verify`` — §4.4 (S#43).

        Saves the returned session token when the restore succeeds.
        """

        response = self._auth_model(
            RestoreVerifyResponse,
            "POST",
            "/auth/restore/verify",
            form={"data": data, "password": password, "hash": hash, "code": code},
            authenticated=False,
            idempotent=False,
        )
        self._store_session(response, required=True, context="restore verify")
        return response

    # -- QR pairing -------------------------------------------------------

    def qr_create(self, device: str) -> QrAuthResponse:
        """``POST /auth/qr/create`` — desktop/TV pairing, §4.5 (S#36)."""

        return self._auth_model(
            QrAuthResponse,
            "POST",
            "/auth/qr/create",
            form={"device": device},
            authenticated=False,
            idempotent=False,
        )

    def qr_status(self, *, key: str, secret: str) -> QrAuthResponse:
        """``POST /auth/qr/status`` — §4.5 (S#39).

        Status ``2`` means confirmed and carries ``profile``/``profileToken``;
        the token is saved automatically in that case.
        """

        response = self._auth_model(
            QrAuthResponse,
            "POST",
            "/auth/qr/status",
            form={"key": key, "secret": secret},
            authenticated=False,
            idempotent=True,
        )
        self._store_session(response, required=False, context="QR status")
        return response

    def qr_open(self, key: str) -> QrAuthResponse:
        """``POST /auth/qr/open`` — approving-client action, §4.5 (S#38)."""

        return self._auth_model(
            QrAuthResponse,
            "POST",
            "/auth/qr/open",
            form={"key": key},
            authenticated=True,
            idempotent=False,
        )

    def qr_confirm(self, *, key: str, pin: str) -> QrAuthResponse:
        """``POST /auth/qr/confirm`` — approving-client PIN entry, §4.5 (S#35)."""

        return self._auth_model(
            QrAuthResponse,
            "POST",
            "/auth/qr/confirm",
            form={"key": key, "pin": pin},
            authenticated=True,
            idempotent=False,
        )

    def qr_decline(self, key: str) -> QrAuthResponse:
        """``POST /auth/qr/decline`` — approving-client decline, §4.5 (S#37)."""

        return self._auth_model(
            QrAuthResponse,
            "POST",
            "/auth/qr/decline",
            form={"key": key},
            authenticated=True,
            idempotent=False,
        )

    # -- external providers ----------------------------------------------

    def _provider_auth(
        self,
        model_type: type[M],
        path: str,
        field: str,
        token: str,
        *,
        login: str | None = None,
        email: str | None = None,
    ) -> M:
        form: dict[str, Any] = {field: token}
        headers: dict[str, str] = {}
        if login is not None and email is not None:
            form.update({"login": login, "email": email})
            headers["X-Long-Code"] = "1"
        response = self._auth_model(
            model_type,
            "POST",
            path,
            form=form,
            headers=headers,
            authenticated=False,
            idempotent=False,
        )
        self._store_session(response, required=False, context=path)
        return response

    def login_google(self, google_id_token: str) -> GoogleResponse:
        """``POST /auth/google`` sign-in — §4.6 (S#33)."""

        return self._provider_auth(GoogleResponse, "/auth/google", "googleIdToken", google_id_token)

    def sign_up_google(self, *, login: str, email: str, google_id_token: str) -> GoogleResponse:
        """``POST /auth/google`` sign-up — §4.6 (S#34)."""

        return self._provider_auth(
            GoogleResponse,
            "/auth/google",
            "googleIdToken",
            google_id_token,
            login=login,
            email=email,
        )

    def login_vk(self, vk_access_token: str) -> VkResponse:
        """``POST /auth/vk`` sign-in — §4.6 (S#49)."""

        return self._provider_auth(VkResponse, "/auth/vk", "vkAccessToken", vk_access_token)

    def sign_up_vk(self, *, login: str, email: str, vk_access_token: str) -> VkResponse:
        """``POST /auth/vk`` sign-up — §4.6 (S#50)."""

        return self._provider_auth(
            VkResponse, "/auth/vk", "vkAccessToken", vk_access_token, login=login, email=email
        )

    def login_telegram(self, telegram_id_token: str) -> TelegramResponse:
        """``POST /auth/telegram`` sign-in — §4.6 (S#46)."""

        return self._provider_auth(
            TelegramResponse, "/auth/telegram", "telegramIdToken", telegram_id_token
        )

    def sign_up_telegram(
        self, *, login: str, email: str, telegram_id_token: str
    ) -> TelegramResponse:
        """``POST /auth/telegram`` sign-up — §4.6 (S#47)."""

        return self._provider_auth(
            TelegramResponse,
            "/auth/telegram",
            "telegramIdToken",
            telegram_id_token,
            login=login,
            email=email,
        )

    def login_yandex(self, yandex_access_token: str) -> YandexResponse:
        """``POST /auth/yandex`` sign-in — §4.6 (S#51)."""

        return self._provider_auth(
            YandexResponse, "/auth/yandex", "yandexAccessToken", yandex_access_token
        )

    def sign_up_yandex(
        self, *, login: str, email: str, yandex_access_token: str
    ) -> YandexResponse:
        """``POST /auth/yandex`` sign-up — §4.6 (S#52)."""

        return self._provider_auth(
            YandexResponse,
            "/auth/yandex",
            "yandexAccessToken",
            yandex_access_token,
            login=login,
            email=email,
        )

    # -- FCM (optional for desktop) ---------------------------------------

    def firebase(self) -> FirebaseResponse:
        """``POST /auth/firebase`` — FCM topic registration, §4.7 (S#32).

        The FCM topic field's wire name is ambiguous (``topicName`` vs
        ``topic_name``, §9 U-24); the model accepts both.
        """

        return self._auth_model(
            FirebaseResponse,
            "POST",
            "/auth/firebase",
            authenticated=True,
            idempotent=False,
        )

    # -- lifecycle --------------------------------------------------------

    def refresh(self) -> None:
        """Refresh the session token.

        .. warning::
           **Not implemented by contract.**  ``docs/api.md`` §4.9 states that
           static analysis found no refresh endpoint, no expiry field and no
           retry-on-401 interceptor.  The practical behaviour is re-login; this
           method exists so callers get an explicit error instead of a
           fabricated request.

        TODO(task 06): resolve U-05/U-06 (token lifetime and hidden refresh
        endpoint) and replace this method only with verified behaviour.
        """

        raise NotImplementedError(
            "No refresh flow exists in docs/api.md §4.9; "
            "re-authenticate with AuthEndpoints.login(). TODO(task 06): U-05/U-06."
        )

    def logout(self) -> None:
        """Clear the local token.  No network call is made.

        ``docs/api.md`` §4.10 explicitly says there is no logout/revoke
        endpoint; a copied token may remain valid server-side until it expires
        (§9 U-07).  This method must not claim server-side revocation.
        """

        self._client.clear_token()


__all__ = [
    "AuthEndpoints",
    "MemoryTokenStore",
    "StoredToken",
    "TokenStore",
]
