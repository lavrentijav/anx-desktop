"""Authentication flows, token store and local logout tests."""

from __future__ import annotations

import threading

import httpx
import pytest
import respx

from anx_desktop.api import (
    AnixartClient,
    AuthError,
    MemoryTokenStore,
    StoredToken,
)


def test_memory_token_store_is_thread_safe():
    store = MemoryTokenStore()
    threads = [
        threading.Thread(target=store.save, args=(StoredToken(f"token-{index}", index),))
        for index in range(20)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stored = store.load()
    assert stored is not None
    assert stored.token.startswith("token-")

    store.clear()
    assert store.load() is None


def _sign_in_body() -> dict:
    return {
        "code": 0,
        "profile": {"id": 1, "login": "example"},
        "profileToken": {"id": 1, "token": "opaque-session-token"},
    }


def test_login_success_stores_token(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/auth/signIn"
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        body = request.content.decode()
        assert "login=example" in body
        assert "password=secret" in body
        assert "token" not in request.url.params
        return httpx.Response(200, json=_sign_in_body())

    store = MemoryTokenStore()
    client = client_factory(handler, token_store=store)

    response = client.auth.login("example", "secret")

    assert response.profile is not None
    assert response.profile.login == "example"
    assert response.profile_token is not None
    assert response.profile_token.token == "opaque-session-token"
    assert client.token == "opaque-session-token"
    assert store.load() == StoredToken("opaque-session-token", profile_id=1)


def test_login_invalid_password_maps_to_auth_error(client_factory):
    body = {"code": 3}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    client = client_factory(handler)
    with pytest.raises(AuthError) as exc_info:
        client.auth.login("example", "wrong")

    assert exc_info.value.code == 3
    assert exc_info.value.body == body
    assert client.token is None


def test_login_success_without_token_is_rejected(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "profile": {"id": 1, "login": "example"}},
        )

    client = client_factory(handler)
    with pytest.raises(AuthError):
        client.auth.login("example", "secret")
    assert client.token is None


def test_login_success_without_profile_is_rejected(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "profileToken": {"id": 1, "token": "opaque"}},
        )

    client = client_factory(handler)
    with pytest.raises(AuthError):
        client.auth.login("example", "secret")
    assert client.token is None


def test_refresh_is_explicitly_not_implemented(client_factory):
    called = False

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        nonlocal called
        called = True
        return httpx.Response(200, json={"code": 0})

    client = client_factory(handler)
    client.set_token("opaque-session-token")

    with pytest.raises(NotImplementedError) as exc_info:
        client.auth.refresh()

    assert "§4.9" in str(exc_info.value)
    assert "task 06" in str(exc_info.value)
    assert called is False
    # refresh must not silently drop the existing session.
    assert client.token == "opaque-session-token"


def test_logout_is_local_only(client_factory):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"code": 0})

    client = client_factory(handler)
    client.set_token("opaque-session-token", profile_id=1)

    client.auth.logout()

    assert client.token is None
    assert calls == 0


def test_sign_up_uses_long_code_header(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/signUp"
        assert request.headers["X-Long-Code"] == "1"
        body = request.content.decode()
        assert "login=example" in body
        assert "email=user%40example.invalid" in body
        assert "password=secret" in body
        return httpx.Response(
            200,
            json={
                "code": 0,
                "hash": "pending-hash",
                "code_length": 5,
                "code_time_left": 120,
                "codeTimestampExpires": 1700000000,
                "suggested_logins": ["example2"],
            },
        )

    client = client_factory(handler)
    response = client.auth.sign_up("example", "user@example.invalid", "secret")

    assert response.hash == "pending-hash"
    assert response.code_length == 5
    assert response.code_timestamp_expires == 1700000000
    assert client.token is None


def test_verify_saves_session(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/verify"
        body = request.content.decode()
        assert "hash=pending-hash" in body
        assert "code=12345" in body
        return httpx.Response(
            200,
            json={
                "code": 0,
                "profile": {"id": 7, "login": "verified"},
                "profileToken": {"id": 7, "token": "verified-token"},
                "suggested_logins": [],
            },
        )

    client = client_factory(handler)
    response = client.auth.verify(hash="pending-hash", code="12345")

    assert response.profile is not None
    assert response.profile.login == "verified"
    assert client.token == "verified-token"
    assert client.session.profile_id == 7


def test_qr_status_saves_confirmed_session(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/qr/status"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "key": "key",
                "secret": "secret",
                "status": 2,
                "profile": {"id": 9, "login": "qr-user"},
                "profileToken": {"id": 9, "token": "qr-token"},
            },
        )

    client = client_factory(handler)
    response = client.auth.qr_status(key="key", secret="secret")

    assert response.status == 2
    assert client.token == "qr-token"


def test_qr_waiting_status_does_not_require_token(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "status": 0, "key": "k"})

    client = client_factory(handler)
    response = client.auth.qr_status(key="k", secret="s")
    assert response.status == 0
    assert client.token is None


def test_check_login_parses_availability(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/checkLogin"
        return httpx.Response(
            200,
            json={"code": 0, "available": True, "suggested_logins": ["example2"]},
        )

    client = client_factory(handler)
    response = client.auth.check_login("example")
    assert response.available is True
    assert response.suggested_logins == ["example2"]


@respx.mock
def test_login_with_respx_interceptor():
    route = respx.post("https://api.test/auth/signIn").mock(
        return_value=httpx.Response(200, json=_sign_in_body())
    )
    with AnixartClient("https://api.test") as client:
        response = client.auth.login("example", "secret")

    assert response.profile is not None
    assert response.profile.login == "example"
    assert client.token == "opaque-session-token"
    assert route.called
