"""Endpoint-level tests: paths, query params, headers and key models."""

from __future__ import annotations

import json

import httpx

from anx_desktop.api import ProfileListStatus


def test_feed_filters_and_page_auth(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/feed/all/2"
        assert request.url.params["channel_id"] == "5"
        assert request.url.params["date"] == "1700000000"
        assert request.url.params["token"] == "secret-token"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "content": [
                    {
                        "id": 5,
                        "author": {"id": 1, "login": "example"},
                        "channel": {"id": 3, "title": "Example channel"},
                        "payload": {"version": "2.26.5", "blocks": []},
                    }
                ],
                "current_page": 2,
                "total_count": 1,
                "total_page_count": 2,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    page = client.feed.get_feed(2, channel_id=5, date=1700000000)
    assert page.current_page == 2
    assert page.content[0].id == 5


def test_release_card_and_extended_mode(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/release/42"
        assert request.url.params["extended_mode"] == "true"
        assert request.url.params["token"] == "secret-token"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "release": {
                    "id": 42,
                    "title_ru": "Example",
                    "year": "2024",
                    "status": {"id": 1, "name": "Ongoing"},
                    "grade": 4.5,
                    "is_favorite": False,
                },
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    response = client.releases.get_release(42, extended_mode=True)
    assert response.release.id == 42
    assert response.release.title_ru == "Example"


def test_release_search_sends_v2_header_and_bare_list(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/releases/1"
        assert request.headers["API-Version"] == "v2"
        assert request.url.params["token"] == "secret-token"
        assert json.loads(request.content) == {"query": "example", "searchBy": 0}
        return httpx.Response(
            200,
            json={
                "code": 0,
                "releases": [{"id": 42, "title_ru": "Example"}],
                "related": None,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    response = client.search.search_releases(1, "example")
    assert [release.id for release in response.releases] == [42]
    assert response.related is None


def test_filter_sends_documented_json_body(client_factory):
    from anx_desktop.api import FilterRequest, GenreMode, SortOrder

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/filter/1"
        assert request.url.params["extended_mode"] == "true"
        body = json.loads(request.content)
        assert body["sort"] == 0
        assert body["genres"] == ["Action"]
        assert body["genres_mode"] == 0
        assert "start_year" not in body
        return httpx.Response(
            200,
            json={
                "code": 0,
                "content": [{"id": 42}],
                "current_page": 1,
                "total_count": 1,
                "total_page_count": 1,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)
    request = FilterRequest(
        genres=["Action"],
        genres_mode=GenreMode.ALL,
        sort=SortOrder.DATE_UPDATE_DESC,
    )

    page = client.search.filter_releases(1, request, extended_mode=True)
    assert [release.id for release in page.content] == [42]


def test_release_comments_add_replies_and_vote(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "secret-token"
        if request.url.path == "/release/comment/add/42":
            body = json.loads(request.content)
            assert body["message"] == "Synthetic comment"
            assert body["spoiler"] is False
            assert "parentCommentId" not in body
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "comment": {
                        "id": 100,
                        "message": "Synthetic comment",
                        "vote_count": 0,
                    },
                },
            )
        if request.url.path == "/release/comment/replies/100/2":
            assert request.url.params["sort"] == "1"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "content": [{"id": 101, "message": "reply"}],
                    "current_page": 2,
                    "total_count": 1,
                    "total_page_count": 2,
                },
            )
        if request.url.path == "/release/comment/vote/100/1":
            return httpx.Response(200, json={"code": 0})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    added = client.comments.add_comment(42, message="Synthetic comment")
    assert added.comment.id == 100

    replies = client.comments.get_replies(100, 2, sort=1)
    assert replies.content[0].message == "reply"

    ack = client.comments.vote_comment(100, 1)
    assert ack.code == 0


def test_history_list_add_and_delete(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "secret-token"
        if request.url.path == "/history/2":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "content": [
                        {
                            "id": 42,
                            "title_ru": "Example",
                            "last_view_episode_name": "1",
                            "last_view_timestamp": 1700000000,
                        }
                    ],
                    "current_page": 2,
                    "total_count": 1,
                    "total_page_count": 2,
                },
            )
        if request.url.path == "/history/add/42/7/3":
            return httpx.Response(200, json={"code": 0})
        if request.url.path == "/history/delete/42":
            return httpx.Response(200, json={"code": 0})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    page = client.history.get_history(2)
    assert page.content[0].last_view_episode_name == "1"

    assert client.history.add(42, 7, 3).code == 0
    assert client.history.delete(42).code == 0


def test_profile_list_uses_enum_path_values(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/profile/list/add/1/42"
        assert request.url.params["token"] == "secret-token"
        return httpx.Response(200, json={"code": 0})

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    response = client.profile.add_to_list(ProfileListStatus.WATCHING, 42)
    assert response.code == 0


def test_profile_list_page_with_optional_filters(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/profile/list/all/1/2"
        assert request.url.params["sort"] == "0"
        assert request.url.params["filter_announce"] == "1"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "content": [{"id": 42}],
                "current_page": 2,
                "total_count": 1,
                "total_page_count": 2,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    page = client.profile.get_list(
        ProfileListStatus.WATCHING, 2, sort=0, filter_announce=1
    )
    assert page.content[0].id == 42


def test_notifications_count_and_list(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "secret-token"
        if request.url.path == "/notification/count":
            return httpx.Response(200, json={"code": 0, "count": 3})
        if request.url.path == "/notification/all/1":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "content": [{"id": 10, "is_new": True}],
                    "current_page": 1,
                    "total_count": 1,
                    "total_page_count": 1,
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    assert client.notifications.get_count().count == 3
    page = client.notifications.get_all(1)
    assert page.content[0].id == 10


def test_episodes_types_sources_and_list(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/episode/42":
            assert request.url.params["token"] == "secret-token"
            return httpx.Response(
                200,
                json={"code": 0, "types": [{"id": 3, "name": "Voice"}]},
            )
        if request.url.path == "/episode/42/3":
            assert "token" not in request.url.params
            return httpx.Response(
                200,
                json={"code": 0, "sources": [{"id": 7, "name": "Source"}]},
            )
        if request.url.path == "/episode/42/3/7":
            assert request.url.params["sort"] == "1"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "episodes": [
                        {
                            "id": 1,
                            "name": "1",
                            "position": 1,
                            "url": "https://example.invalid/player",
                        }
                    ],
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    assert client.episodes.get_types(42).types[0].name == "Voice"
    assert client.episodes.get_sources(42, 3).sources[0].id == 7
    episodes = client.episodes.get_episodes(42, 3, 7, sort=1)
    assert episodes.episodes[0].url == "https://example.invalid/player"


def test_related_requires_v2_header(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/related/9/1"
        assert request.headers["API-Version"] == "v2"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "content": [{"id": 42}],
                "current_page": 1,
                "total_count": 1,
                "total_page_count": 1,
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)
    page = client.releases.get_related(9, 1)
    assert page.content[0].id == 42


def test_favorites_and_vote_paths(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "secret-token"
        if request.url.path == "/favorite/add/42":
            return httpx.Response(200, json={"code": 0})
        if request.url.path == "/favorite/all/1":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "content": [{"id": 42}],
                    "current_page": 1,
                    "total_count": 1,
                    "total_page_count": 1,
                },
            )
        if request.url.path == "/release/vote/add/42/1":
            return httpx.Response(200, json={"code": 0})
        raise AssertionError(f"unexpected path {request.url.path}")

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    assert client.releases.add_favorite(42).code == 0
    assert client.releases.get_favorites(1).content[0].id == 42
    assert client.releases.vote(42, 1).code == 0


def test_episode_target_uses_captured_shape(client_factory):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/episode/target/1/2/3"
        assert request.url.params["token"] == "secret-token"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "episode": {
                    "@id": 11,
                    "releaseId": 1,
                    "sourceId": 2,
                    "position": 3,
                    "name": "Episode 3",
                    "url": "https://s.example/episode.m3u8",
                    "iframe": False,
                    "quality": 1080,
                    "is_filler": False,
                    "is_watched": True,
                },
            },
        )

    client = client_factory(handler)
    client.set_token("secret-token", profile_id=1)

    response = client.episodes.get_target(1, 2, 3)
    assert response.episode is not None
    assert response.episode.id == 11
    assert response.episode.url == "https://s.example/episode.m3u8"
    assert response.episode.quality == 1080
