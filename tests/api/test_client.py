"""Transport, error mapping, retries and token redaction tests."""

from __future__ import annotations

import logging

import httpx
import pytest

from anx_desktop.api import (
    AuthError,
    NetworkError,
    NotFoundError,
    ProfileListStatus,
    RateLimitError,
    ServerError,
    ValidationError,
)


def test_profile_info_sends_token_and_redacts_logs(client_factory, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/profile/info"
        assert request.url.params["token"] == "secret-token"
        assert request.headers["accept"] == "application/json"
        assert request.headers["user-agent"].startswith("AnixartApp/")
        return httpx.Response(
            200,
            json={"code": 0, "is_banned": False, "rating_score": 5},
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    with caplog.at_level(logging.DEBUG, logger="anx_desktop.api.client"):
        response = client.profile.get_info()

    assert response.is_banned is False
    assert response.rating_score == 5
    # Logs contain method/path only, never the query token (§3.6, §10.4).
    assert "secret-token" not in caplog.text
    assert "/profile/info" in caplog.text


def test_missing_token_fails_before_network(client_factory):
    called = False

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        nonlocal called
        called = True
        return httpx.Response(200, json={"code": 0})

    client = client_factory(handler)
    with pytest.raises(AuthError):
        client.profile.get_info()
    assert called is False


def test_401_clears_session_and_preserves_body(client_factory):
    error_body = {"code": 1, "message": "invalid session"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json=error_body)

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(AuthError) as exc_info:
        client.profile.get_info()

    error = exc_info.value
    assert error.status_code == 401
    assert error.code == 1
    assert error.body == error_body
    assert error.path == "/profile/info"
    assert client.token is None
    assert "secret-token" not in str(error)


def test_429_maps_to_rate_limit_and_keeps_retry_after(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "7"},
            json={"code": 1, "message": "slow down"},
        )

    client = client_factory(handler, max_retries=0)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(RateLimitError) as exc_info:
        client.profile.get_info()

    assert exc_info.value.retry_after == 7.0
    assert exc_info.value.status_code == 429
    assert exc_info.value.body == {"code": 1, "message": "slow down"}


def test_5xx_is_retried_for_idempotent_read(client_factory):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"code": 1})
        return httpx.Response(200, json={"code": 0, "articleId": 5})

    client = client_factory(handler, max_retries=2)
    client.set_token("secret-token", profile_id=1)

    response = client.feed.get_latest_article()
    assert response.article_id == 5
    assert calls == 2


def test_5xx_is_not_retried_for_mutation(client_factory):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"code": 1})

    client = client_factory(handler, max_retries=2)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(ServerError):
        client.comments.add_comment(42, message="synthetic")
    assert calls == 1


def test_404_and_400_mapping(client_factory):
    not_found = client_factory(lambda request: httpx.Response(404, json={"code": 2}))
    not_found.set_token("secret-token")
    with pytest.raises(NotFoundError):
        not_found.profile.get_profile(1)

    bad_request = client_factory(lambda request: httpx.Response(400, json={"code": 1}))
    bad_request.set_token("secret-token")
    with pytest.raises(ValidationError):
        bad_request.profile.get_profile(1)


def test_nonzero_application_code_maps_to_validation_error(client_factory):
    body = {"code": 5, "message": "list limit"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(ValidationError) as exc_info:
        client.profile.add_to_list(ProfileListStatus.WATCHING, 42)

    assert exc_info.value.code == 5
    assert exc_info.value.body == body
    # Only a 401 invalidates the session; a business code does not.
    assert client.token == "secret-token"


def test_model_validation_failure_is_wrapped(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "profile": {"id": "not-an-int", "login": "x"}},
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(ValidationError) as exc_info:
        client.profile.get_profile(1)

    assert isinstance(exc_info.value.body, dict)
    assert exc_info.value.body["profile"]["id"] == "not-an-int"


def test_config_urls_sends_empty_token_before_login(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/config/urls"
        assert request.url.params.get("token") == ""
        return httpx.Response(
            200,
            json={
                "api_urls": ["https://api-s.anixsekai.com/"],
                "static_domain": "anixmirai.com",
                "should_use_mirror_urls": False,
            },
        )

    client = client_factory(handler)
    response = client.config.get_urls()
    assert response.api_urls == ["https://api-s.anixsekai.com/"]
    assert response.static_domain == "anixmirai.com"


def test_public_endpoint_does_not_send_token(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/config/anixplayer"
        assert "token" not in request.url.params
        return httpx.Response(200, json={"last_version_code": 1})

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)
    response = client.config.get_anixplayer_config()
    assert response.last_version_code == 1


def test_network_error_does_not_chain_url_with_token(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    with pytest.raises(NetworkError) as exc_info:
        client.profile.get_info()

    assert "secret-token" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_retry_delay_uses_retry_after(client_factory):
    delays: list[float] = []
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "3"}, json={"code": 1})
        return httpx.Response(200, json={"code": 0, "count": 1})

    from anx_desktop.api import MemoryTokenStore

    client = client_factory(handler, max_retries=1, token_store=MemoryTokenStore(), sleep=delays.append)
    client.set_token("secret-token", profile_id=1)

    response = client.notifications.get_count()
    assert response.count == 1
    assert delays == [3.0]
