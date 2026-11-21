"""Offline tests for the UI connector adapter (task 12).

Every fake client is a plain Python object: no test imports the transport,
opens a socket or reaches the network.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from anx_desktop.api.models import (
    Article as ApiArticle,
    ArticlePayload,
    Badge as ApiBadge,
    BadgeCategory,
    Category,
    Channel as ApiChannel,
    Episode as ApiEpisode,
    EpisodeCompact,
    EpisodeResponse,
    Interesting,
    Profile as ApiProfile,
    ProfileCompact,
    ProfileGenre,
    ProfileListStatus,
    ProfileResponse,
    ProfileSlim,
    ProfileWatchDynamics,
    Release as ApiRelease,
    Related,
    ReleaseComment,
    ReleaseCompact,
    ReleaseSearchResponse,
    ReleaseStatus,
    ReleaseType,
    RoleDto,
    SortOrder,
    Source,
    SourcesResponse,
    TypesResponse,
)
from anx_desktop.ui import connector_adapter
from anx_desktop.ui.connector_adapter import ConnectorRepository, create_repository


# ---------------------------------------------------------------------------
# Synthetic API objects and fake endpoints
# ---------------------------------------------------------------------------


def api_release(**overrides):
    values = {
        "id": 42,
        "title_ru": "Лунный странник",
        "title_original": "Tsuki no Wanderer",
        "year": "2024",
        "grade": 4.5,
        "episodes_total": 12,
        "episodes_released": 5,
        "description": "Описание релиза",
        "country": "Япония",
        "studio": "Studio Example",
        "source": "Манга",
        "genres": "Фэнтези, Приключения",
        "status": ReleaseStatus(id=1, name="Выходит"),
        "age_rating": "16+",
        "is_adult": False,
        "is_favorite": True,
        "vote_count": 123,
        "vote_1_count": 1,
        "vote_2_count": 2,
        "vote_3_count": 3,
        "vote_4_count": 4,
        "vote_5_count": 5,
        "duration": 24,
        "category": Category(id=1, name="Сериал"),
    }
    values.update(overrides)
    return ApiRelease(**values)


def page(content=(), *, current_page=1, total_count=None, total_page_count=None):
    if total_count is None:
        total_count = len(content)
    if total_page_count is None:
        total_page_count = 1 if content else 0
    return SimpleNamespace(
        content=list(content),
        current_page=current_page,
        total_count=total_count,
        total_page_count=total_page_count,
    )


def _result(response):
    if isinstance(response, Exception):
        raise response
    return response


class FakeSearch:
    def __init__(self):
        self.filter_calls = []
        self.extended_modes = []
        self.search_calls = []
        self.filter_response = page()
        self.search_response = SimpleNamespace(releases=[])

    def filter_releases(self, page_number, request=None, *, extended_mode=None):
        self.filter_calls.append((page_number, request))
        self.extended_modes.append(extended_mode)
        return _result(self.filter_response)

    def search_releases(self, page_number, query, *, search_by=0):
        self.search_calls.append((page_number, query))
        return _result(self.search_response)


class FakeReleases:
    def __init__(self):
        self.release_response = SimpleNamespace(release=None)
        self.related_response = page()
        self.badges_response = page()
        self.favorites_response = page()
        self.release_calls = []
        self.related_calls = []
        self.badge_calls = []
        self.favorite_calls = []

    def get_release(self, release_id, *, extended_mode=None):
        self.release_calls.append(release_id)
        return _result(self.release_response)

    def get_related(self, related_id, page_number=1):
        self.related_calls.append((related_id, page_number))
        return _result(self.related_response)

    def get_badges(self, release_id, page_number=1):
        self.badge_calls.append((release_id, page_number))
        return _result(self.badges_response)

    def get_favorites(self, page_number=1, *, sort=None, filter_announce=None):
        self.favorite_calls.append((page_number, sort, filter_announce))
        return _result(self.favorites_response)


class FakeComments:
    def __init__(self):
        self.comments_response = page()
        self.calls = []

    def get_comments(self, release_id, page_number=1, *, sort=None):
        self.calls.append((release_id, page_number))
        return _result(self.comments_response)


class FakeEpisodes:
    def __init__(self):
        self.types_response = TypesResponse(types=[])
        self.sources_response = SourcesResponse(sources=[])
        self.episodes_response = EpisodeResponse(episodes=[])
        self.type_calls = []
        self.source_calls = []
        self.episode_calls = []

    def get_types(self, release_id):
        self.type_calls.append(release_id)
        return _result(self.types_response)

    def get_sources(self, release_id, type_id):
        self.source_calls.append((release_id, type_id))
        return _result(self.sources_response)

    def get_episodes(self, release_id, type_id, source_id, *, sort=None):
        self.episode_calls.append((release_id, type_id, source_id))
        return _result(self.episodes_response)


class FakeFeed:
    def __init__(self):
        self.recommendations_response = page()
        self.interesting_response = page()
        self.watching_response = page()
        self.discussing_response = page()
        self.comments_response = page()
        self.feed_response = page()
        self.recommendation_calls = []
        self.interesting_calls = 0
        self.discussing_calls = 0
        self.watching_calls = []
        self.comments_calls = 0
        self.feed_calls = []

    def get_recommendations(self, page_number=1, *, previous_page=None):
        self.recommendation_calls.append(page_number)
        return _result(self.recommendations_response)

    def get_interesting(self):
        self.interesting_calls += 1
        return _result(self.interesting_response)

    def get_discussing(self):
        self.discussing_calls += 1
        return _result(self.discussing_response)

    def get_watching(self, page_number=1):
        self.watching_calls.append(page_number)
        return _result(self.watching_response)

    def get_comments_week(self):
        self.comments_calls += 1
        return _result(self.comments_response)

    def get_feed(self, page_number=1, *, channel_id=None, date=None):
        self.feed_calls.append((page_number, channel_id, date))
        return _result(self.feed_response)


class FakeProfile:
    def __init__(self):
        self.info_response = SimpleNamespace()
        self.profile_response = SimpleNamespace(profile=None)
        self.list_response = page()
        self.info_calls = 0
        self.profile_calls = []
        self.list_calls = []

    def get_info(self):
        self.info_calls += 1
        return _result(self.info_response)

    def get_profile(self, profile_id):
        self.profile_calls.append(profile_id)
        return _result(self.profile_response)

    def get_list(self, status, page_number=1, *, sort=None, filter_announce=None):
        self.list_calls.append((status, page_number))
        return _result(self.list_response)


class FakeHistory:
    def __init__(self):
        self.history_response = page()
        self.calls = []

    def get_history(self, page_number=1):
        self.calls.append(page_number)
        return _result(self.history_response)


class FakeNotifications:
    def __init__(self):
        self.notifications_response = page()
        self.calls = []

    def get_all(self, page_number=1):
        self.calls.append(page_number)
        return _result(self.notifications_response)


class FakeClient:
    instances: list["FakeClient"] = []

    def __init__(self):
        self.token = None
        self.is_authenticated = False
        self.session = None
        self.search = FakeSearch()
        self.releases = FakeReleases()
        self.comments = FakeComments()
        self.episodes = FakeEpisodes()
        self.feed = FakeFeed()
        self.profile = FakeProfile()
        self.history = FakeHistory()
        self.notifications = FakeNotifications()
        FakeClient.instances.append(self)

    def set_token(self, token, *, profile_id=None):
        self.token = token
        self.is_authenticated = bool(token)
        self.session = SimpleNamespace(profile_id=profile_id)


def authenticated_client() -> FakeClient:
    client = FakeClient()
    client.set_token("test-token", profile_id=7)
    return client


def comment_model(**overrides):
    values = {
        "id": 11,
        "message": "Текст комментария",
        "timestamp": 1_700_000_000,
        "profile": ProfileCompact(id=2, login="reader", is_verified=True),
        "vote_count": 7,
        "vote": 1,
        "reply_count": 3,
        "is_spoiler": True,
        "is_edited": True,
    }
    values.update(overrides)
    return ReleaseComment(**values)


# ---------------------------------------------------------------------------
# Page / home mapping
# ---------------------------------------------------------------------------


def test_pageable_response_maps_to_ui_page_and_filter_request():
    client = FakeClient()
    client.search.filter_response = page(
        [api_release()], current_page=2, total_count=30, total_page_count=3
    )
    repo = ConnectorRepository(client)

    mapped = repo.fetch_home("home_1", 2, 12)

    assert mapped.page == 2
    assert mapped.page_size == 12
    assert mapped.total_count == 30
    assert mapped.total_pages == 3
    assert mapped.has_more is True
    assert mapped.items[0].id == 42

    request = client.search.filter_calls[0][1]
    assert request.country == "Япония"
    assert int(request.sort) == int(SortOrder.DATE_UPDATE_DESC)


def test_home_country_and_latest_tabs_use_the_documented_filters():
    client = FakeClient()
    repo = ConnectorRepository(client)

    repo.fetch_home("home_2", 1, 12)
    china = client.search.filter_calls[-1][1]
    assert china.country == "Китай"
    assert int(china.sort) == int(SortOrder.DATE_UPDATE_DESC)

    repo.fetch_home("home_3", 1, 12)
    latest = client.search.filter_calls[-1][1]
    assert latest.country is None
    assert int(latest.sort) == int(SortOrder.DATE_UPDATE_DESC)


def test_home_zero_uses_recommendations_only_with_a_token():
    anonymous = FakeClient()
    repo = ConnectorRepository(anonymous)
    repo.fetch_home("home_0", 1, 12)
    assert anonymous.feed.recommendation_calls == []
    assert anonymous.search.filter_calls[-1][1].country is None
    assert int(anonymous.search.filter_calls[-1][1].sort) == int(
        SortOrder.POPULAR_DESC
    )

    client = authenticated_client()
    repo = ConnectorRepository(client)
    api_release_value = api_release(id=77)
    client.feed.recommendations_response = page([api_release_value])

    mapped = repo.fetch_home("home_0", 1, 12)
    assert client.feed.recommendation_calls == [1]
    assert client.search.filter_calls == []
    assert mapped.items[0].id == 77


def test_empty_recommendations_fall_back_to_popular():
    client = authenticated_client()
    client.search.filter_response = page([api_release(id=88)])
    repo = ConnectorRepository(client)

    mapped = repo.fetch_home("home_0", 1, 12)

    assert client.feed.recommendation_calls == [1]
    assert len(client.search.filter_calls) == 1
    assert int(client.search.filter_calls[0][1].sort) == int(SortOrder.POPULAR_DESC)
    assert mapped.items[0].id == 88


def test_status_and_category_tabs_use_verified_filter_ids():
    client = FakeClient()
    client.search.filter_response = page([api_release()])
    repo = ConnectorRepository(client)

    cases = {
        "home_4": ("status_id", 1),
        "home_5": ("status_id", 2),
        "home_6": ("status_id", 3),
        "home_7": ("category_id", 2),
        "home_8": ("category_id", 3),
    }
    for tab_key, (field, value) in cases.items():
        mapped = repo.fetch_home(tab_key, 1, 12)
        assert mapped.items
        request = client.search.filter_calls[-1][1]
        assert getattr(request, field) == value
        assert int(request.sort) == int(SortOrder.DATE_UPDATE_DESC)
        assert request.types == []
        assert request.genres == []
        assert request.is_genres_exclude_mode_enabled is False
        assert client.search.extended_modes[-1] is True


# ---------------------------------------------------------------------------
# Release, comments, episodes
# ---------------------------------------------------------------------------


def test_age_rating_wire_values_map_to_android_labels():
    assert connector_adapter._age_rating(1) == "0+"
    assert connector_adapter._age_rating(2) == "6+"
    assert connector_adapter._age_rating(3) == "12+"
    assert connector_adapter._age_rating(4) == "16+"
    assert connector_adapter._age_rating(5) == "18+"
    assert connector_adapter._age_rating(0) == ""


def test_release_mapping_includes_details_related_comments_and_badges():
    client = FakeClient()
    client.releases.release_response = SimpleNamespace(
        release=api_release(
            category=Category(id=2, name="Фильм"),
            screenshot_images=["one", "two"],
            image="https://s.example/poster.jpg",
            profile_list_status=1,
            related=Related(id=900),
            recommended_releases=[api_release(id=99)],
            your_vote=4,
        )
    )
    client.releases.related_response = page([api_release(id=43, title_ru="Связанный")])
    client.releases.badges_response = page(
        [
            ApiBadge(
                id=5,
                name="Первый отзыв",
                description="Описание",
                rarity="rare",
                category=BadgeCategory(id=1, title="Активность"),
                ownership_percentage=12.5,
                is_owned=True,
            )
        ]
    )
    client.comments.comments_response = page([comment_model()])
    repo = ConnectorRepository(client)

    details = repo.fetch_release(42)

    assert details.release.id == 42
    assert details.release.title == "Лунный странник"
    assert details.release.original_title == "Tsuki no Wanderer"
    assert details.release.year == 2024
    assert details.release.grade == 4.5
    assert details.release.episodes_total == 12
    assert details.release.episodes_released == 5
    assert details.release.genres == ("Фэнтези", "Приключения")
    assert details.release.status == "Выходит"
    assert details.release.age_rating == "16+"
    assert details.release.votes == (1, 2, 3, 4, 5)
    assert details.release.is_movie is True
    assert details.release.image_url == "https://s.example/poster.jpg"
    assert details.release.list_status == 1
    assert details.screenshots == 2
    assert details.user_vote == 4.0
    assert [item.id for item in details.related] == [43]
    assert [item.id for item in details.recommended] == [99]
    assert details.comments[0].author == "reader"
    assert details.comments[0].text == "Текст комментария"
    assert details.comments[0].votes == 7
    assert details.comments[0].is_verified is True
    assert details.badges[0].name == "Первый отзыв"
    assert details.badges[0].category == "Активность"
    assert client.releases.release_calls == [42]
    assert client.releases.related_calls == [(900, 1)]


def test_episode_mapping_uses_types_sources_and_episodes():
    client = FakeClient()
    release_type = ReleaseType(id=1, name="Озвучка")
    source = Source(
        id=7,
        name="AniLibria",
        episodes_count=12,
        type=release_type,
    )
    client.episodes.types_response = TypesResponse(types=[release_type])
    client.episodes.sources_response = SourcesResponse(sources=[source])
    client.episodes.episodes_response = EpisodeResponse(
        episodes=[
            ApiEpisode(
                id=101,
                name="Серия 1",
                position=1,
                playback_duration=1440,
                is_watched=True,
                is_filler=False,
                source=source,
                added_date=1_700_000_000,
                url="https://kodik.example/iframe/1",
                iframe=True,
            )
        ]
    )
    repo = ConnectorRepository(client)

    episodes = repo.fetch_episodes(42)
    sources = repo.episode_sources(42)

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.id == 101
    assert episode.number == 1
    assert episode.title == "Серия 1"
    assert episode.duration_seconds == 1440
    assert episode.watched is True
    assert episode.filler is False
    assert episode.type_name == "Озвучка"
    assert episode.source_name == "AniLibria"
    assert episode.added_ts == 1_700_000_000.0
    assert episode.stream_url == "https://kodik.example/iframe/1"
    assert episode.iframe is True
    assert [(item.id, item.name, item.kind, item.episodes_count) for item in sources] == [
        (7, "AniLibria", "Озвучка", 12)
    ]
    assert client.episodes.episode_calls == [(42, 1, 7)]


def test_episode_types_expose_subtitle_flag():
    client = FakeClient()
    client.episodes.types_response = TypesResponse(
        types=[
            ReleaseType(id=1, name="Озвучка", is_sub=False),
            ReleaseType(id=2, name="Субтитры", is_sub=True),
        ]
    )
    repo = ConnectorRepository(client)

    types = repo.episode_types(42)

    assert [(item.id, item.name, item.is_sub) for item in types] == [
        (1, "Озвучка", False),
        (2, "Субтитры", True),
    ]


def test_fetch_episodes_passes_explicit_source():
    client = FakeClient()
    client.episodes.types_response = TypesResponse(
        types=[ReleaseType(id=1, name="Озвучка")]
    )
    client.episodes.sources_response = SourcesResponse(
        sources=[
            Source(id=7, name="AniLibria", episodes_count=12),
            Source(id=8, name="Studio Band", episodes_count=12),
        ]
    )
    repo = ConnectorRepository(client)

    repo.fetch_episodes(42, type_id=1, source_id=8)

    assert client.episodes.episode_calls == [(42, 1, 8)]


def test_episodes_are_empty_when_type_or_source_is_unknown():
    client = FakeClient()
    client.episodes.types_response = TypesResponse(types=[])
    repo = ConnectorRepository(client)

    assert repo.fetch_episodes(42) == ()
    assert repo.episode_sources(42) == ()
    assert client.episodes.episode_calls == []


# ---------------------------------------------------------------------------
# Search, comments, discover, feed
# ---------------------------------------------------------------------------


def test_search_mapping_and_empty_query_short_circuit():
    client = FakeClient()
    client.search.search_response = ReleaseSearchResponse(releases=[api_release()])
    repo = ConnectorRepository(client)

    results = repo.fetch_search("  луна  ")

    assert results.query == "  луна  "
    assert [item.id for item in results.releases] == [42]
    assert results.articles == ()
    assert results.channels == ()
    assert results.profiles == ()
    assert results.collections == ()
    assert client.search.search_calls == [(1, "луна")]

    empty = repo.fetch_search("   ")
    assert empty.releases == ()
    assert client.search.search_calls == [(1, "луна")]


def test_comment_mapping():
    client = FakeClient()
    client.comments.comments_response = page([comment_model()])
    repo = ConnectorRepository(client)

    comments = repo.fetch_comments("release", 42)

    assert len(comments) == 1
    comment = comments[0]
    assert comment.id == 11
    assert comment.author == "reader"
    assert comment.text == "Текст комментария"
    assert comment.timestamp == 1_700_000_000.0
    assert comment.votes == 7
    assert comment.user_vote == 1
    assert comment.is_spoiler is True
    assert comment.is_edited is True
    assert comment.is_verified is True
    assert comment.replies == 3
    assert client.comments.calls == [(42, 1)]


def test_discover_maps_only_model_compatible_sections():
    client = FakeClient()
    client.feed.interesting_response = page(
        [Interesting(id=9, title="Актуальное", description="Описание")]
    )
    client.feed.recommendations_response = page([api_release(id=50)])
    client.feed.watching_response = page([api_release(id=51)])
    client.feed.comments_response = page([comment_model(id=52)])
    repo = ConnectorRepository(client)

    data = repo.fetch_discover()

    assert [card.id for card in data.trending] == [9]
    assert data.trending[0].title == "Актуальное"
    assert [item.id for item in data.recommendations] == [50]
    assert [item.id for item in data.watching_now] == [51]
    assert [item.id for item in data.comments_week] == [52]
    assert data.discussed == ()
    assert data.collections_week == ()
    assert data.quick_links == ()
    assert data.social_links == ()
    assert data.sponsorship_text == ""
    assert client.feed.discussing_calls == 1


def test_feed_mapping_keeps_unknown_article_fields_empty():
    client = FakeClient()
    channel = ApiChannel(
        id=3,
        title="Северный ветер",
        description="Описание канала",
        subscriber_count=100,
        is_verified=True,
        is_subscribed=True,
        article_count=4,
    )
    article = ApiArticle(
        id=5,
        channel=channel,
        author=ProfileSlim(id=1, login="author"),
        payload=ArticlePayload(blocks=[]),
        comment_count=4,
        vote_count=8,
        repost_count=1,
        creation_date=1_700_000_000,
        is_pinned=True,
    )
    client.feed.feed_response = page([article])
    repo = ConnectorRepository(client)

    mapped = repo.fetch_feed("feed_0", 1, 8)

    assert len(mapped.items) == 1
    item = mapped.items[0]
    assert item.article.id == 5
    assert item.article.title == ""
    assert item.article.blocks == ()
    assert item.article.author == "author"
    assert item.article.votes == 8
    assert item.article.comments_count == 4
    assert item.article.reposts == 1
    assert item.channel.id == 3
    assert item.channel.title == "Северный ветер"
    assert item.article.channel_id == 3
    assert client.feed.feed_calls == [(1, None, None)]


# ---------------------------------------------------------------------------
# Profile, notifications, history / bookmarks
# ---------------------------------------------------------------------------


def test_profile_without_token_requires_authentication():
    client = FakeClient()
    repo = ConnectorRepository(client)

    with pytest.raises(RuntimeError, match="Authentication is required"):
        repo.fetch_profile(7)

    assert client.profile.profile_calls == []
    assert client.profile.info_calls == 0


def test_profile_mapping_with_token():
    client = authenticated_client()
    client.profile.profile_response = ProfileResponse(
        profile=ApiProfile(
            id=7,
            login="me",
            status="Статус",
            is_verified=True,
            is_sponsor=True,
            is_online=True,
            register_date=1_700_000_000,
            rating_score=5,
            roles=[RoleDto(id=1, name="Moderator")],
            watching_count=1,
            plan_count=2,
            completed_count=3,
            hold_on_count=4,
            dropped_count=5,
            favorite_count=6,
            watched_episode_count=10,
            watched_time=240,
            comment_count=11,
            video_count=12,
            collection_count=13,
            friend_count=14,
            preferred_genres=[ProfileGenre(name="Драма")],
            watch_dynamics=[
                ProfileWatchDynamics(count=1),
                ProfileWatchDynamics(count=3),
            ],
            badges_preview=[ApiBadge(id=1, name="Значок", rarity="rare")],
            votes=[api_release(id=60)],
            history=[api_release(id=61)],
        ),
        is_my_profile=True,
    )
    repo = ConnectorRepository(client)

    data = repo.fetch_profile(7)

    assert data.profile.id == 7
    assert data.profile.nick == "me"
    assert data.profile.status == "Статус"
    assert data.profile.is_verified is True
    assert data.profile.is_sponsor is True
    assert data.profile.rating == 5.0
    assert data.profile.roles == ("Moderator",)
    assert data.profile.counters.watching == 1
    assert data.profile.counters.favorites == 6
    assert data.profile.watched_minutes == 240
    assert data.dynamics == (1, 3)
    assert data.genres == ("Драма",)
    assert [badge.name for badge in data.badges] == ["Значок"]
    assert [item.id for item in data.votes] == [60]
    assert [item.id for item in data.history] == [61]
    assert [stat.count for stat in data.stats] == [1, 2, 3, 4, 5]
    assert client.profile.profile_calls == [7]


def test_profile_mapping_without_login_uses_id_fallback():
    """An empty login must not produce a non-string nick for the screen."""

    client = authenticated_client()
    client.profile.profile_response = ProfileResponse(
        profile=ApiProfile(id=7, login="", status="Статус"),
        is_my_profile=True,
    )
    repo = ConnectorRepository(client)

    data = repo.fetch_profile(7)

    assert data.profile.nick == "id7"


def test_notifications_are_mapped_and_filtered_by_kind():
    client = authenticated_client()
    client.notifications.notifications_response = page(
        [
            SimpleNamespace(
                id=1,
                timestamp=100,
                is_new=True,
                episode=EpisodeCompact(
                    name="Серия 2",
                    release=ReleaseCompact(id=42, title_ru="Лунный странник"),
                ),
            ),
            SimpleNamespace(
                id=2,
                timestamp=200,
                is_new=False,
                article=SimpleNamespace(
                    id=5, channel=SimpleNamespace(title="Северный ветер")
                ),
            ),
            SimpleNamespace(
                id=3,
                timestamp=300,
                is_new=True,
                comment=SimpleNamespace(message="Ответ", is_spoiler=True),
                by_profile=SimpleNamespace(id=3, login="reader"),
            ),
            SimpleNamespace(
                id=4,
                timestamp=400,
                is_new=False,
                status=0,
                by_profile=SimpleNamespace(id=4, login="friend"),
            ),
        ]
    )
    repo = ConnectorRepository(client)

    all_items = repo.fetch_notifications("all")
    assert [item.kind for item in all_items] == ["episode", "article", "reply", "friend"]
    assert all_items[0].target_kind == "release"
    assert all_items[0].target_id == 42
    assert all_items[1].target_kind == "article"
    assert all_items[1].target_id == 5
    assert all_items[2].target_kind == "profile"
    assert all_items[2].spoiler is True
    assert all_items[3].target_id == 4

    assert [item.id for item in repo.fetch_notifications("episodes")] == [1]
    assert [item.id for item in repo.fetch_notifications("articles")] == [2]
    assert [item.id for item in repo.fetch_notifications("replies")] == [3]
    assert [item.id for item in repo.fetch_notifications("friends")] == [4]
    assert client.notifications.calls == [1, 1, 1, 1, 1]


def test_notifications_without_token_are_empty():
    client = FakeClient()
    repo = ConnectorRepository(client)

    items = repo.fetch_notifications("all")

    assert items == ()
    assert client.notifications.calls == []


def test_history_and_bookmarks_require_a_token():
    client = FakeClient()
    repo = ConnectorRepository(client)

    history = repo.fetch_history(1, 12)
    bookmarks = repo.fetch_bookmarks("bookmark_2", 1, 12)

    assert history.items == ()
    assert bookmarks.items == ()
    assert client.history.calls == []
    assert client.releases.favorite_calls == []


def test_history_and_bookmark_mapping_with_token():
    client = authenticated_client()
    client.history.history_response = page(
        [
            api_release(
                id=42,
                last_view_episode_name="Серия 3",
                last_view_timestamp=1_700_000_100,
                last_view_episode=SimpleNamespace(
                    name="Серия 3",
                    source=SimpleNamespace(name="AniLibria"),
                ),
            )
        ]
    )
    client.releases.favorites_response = page([api_release(id=43)])
    client.profile.list_response = page([api_release(id=44)])
    repo = ConnectorRepository(client)

    history = repo.fetch_history(1, 12)
    assert history.items[0].release.id == 42
    assert history.items[0].episode_name == "Серия 3"
    assert history.items[0].source_name == "AniLibria"
    assert history.items[0].watch_ts == 1_700_000_100.0

    favorites = repo.fetch_bookmarks("bookmark_2", 1, 12)
    assert [item.id for item in favorites.items] == [43]
    assert client.releases.favorite_calls == [(1, None, None)]

    watching = repo.fetch_bookmarks("bookmark_3", 1, 12)
    assert [item.id for item in watching.items] == [44]
    assert client.profile.list_calls[0][0] == ProfileListStatus.WATCHING


# ---------------------------------------------------------------------------
# Fallback on errors and unsupported domains
# ---------------------------------------------------------------------------


def test_api_errors_do_not_return_demo_data():
    client = FakeClient()
    client.search.filter_response = RuntimeError("boom")
    client.search.search_response = RuntimeError("boom")
    client.releases.release_response = RuntimeError("boom")
    client.feed.interesting_response = RuntimeError("boom")
    client.feed.recommendations_response = RuntimeError("boom")
    client.feed.discussing_response = RuntimeError("boom")
    client.feed.watching_response = RuntimeError("boom")
    client.feed.comments_response = RuntimeError("boom")
    repo = ConnectorRepository(client)

    home = repo.fetch_home("home_1", 1, 12)
    search = repo.fetch_search("query")
    with pytest.raises(RuntimeError, match="Could not load release"):
        repo.fetch_release(42)
    discover = repo.fetch_discover()

    assert home.items == ()
    assert search.releases == ()
    assert discover.trending == ()
    assert discover.recommendations == ()
    assert discover.watching_now == ()
    assert discover.comments_week == ()


def test_unsupported_lists_are_empty():
    repo = ConnectorRepository(FakeClient())

    assert repo.fetch_collections() == ()
    assert repo.fetch_channels() == ()
    assert repo.fetch_articles() == ()
    assert repo.fetch_badges() == ()
    assert repo.fetch_schedule() == {}
    assert repo.fetch_related("unknown") == ()
    assert repo.fetch_home("unknown", 2, 12).items == ()


@pytest.mark.parametrize(
    ("method", "args"),
    [
        ("fetch_collection", (2000,)),
        ("fetch_channel", (3000,)),
        ("fetch_article", (4000,)),
        ("fetch_health", ()),
        ("fetch_deletion", ()),
    ],
)
def test_unsupported_details_raise(method, args):
    repo = ConnectorRepository(FakeClient())
    with pytest.raises(RuntimeError, match="unavailable"):
        getattr(repo, method)(*args)


def test_search_history_starts_empty_and_can_be_cleared():
    repo = ConnectorRepository(FakeClient())
    assert repo.search_history() == []
    repo.remember_search(" test query ")
    repo.remember_search("test query")
    assert repo.search_history() == ["test query"]
    repo.clear_search_history()
    assert repo.search_history() == []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_raises_when_module_is_missing(monkeypatch):
    monkeypatch.setattr(connector_adapter, "connector_module", lambda: None)

    with pytest.raises(RuntimeError, match="Could not initialise"):
        create_repository()


def test_factory_raises_when_module_lookup_raises(monkeypatch):

    def broken_module():
        raise RuntimeError("import exploded")

    monkeypatch.setattr(connector_adapter, "connector_module", broken_module)

    with pytest.raises(RuntimeError, match="Could not initialise"):
        create_repository()


def test_connector_repository_accepts_a_connector_module():
    FakeClient.instances.clear()
    repo = ConnectorRepository(SimpleNamespace(AnixartClient=FakeClient))

    assert isinstance(repo._client, FakeClient)
    assert FakeClient.instances[-1].token is None


def test_factory_returns_live_connector_without_the_flag(monkeypatch):
    monkeypatch.delenv("ANX_UI_USE_CONNECTOR", raising=False)
    FakeClient.instances.clear()
    monkeypatch.setattr(
        connector_adapter,
        "connector_module",
        lambda: SimpleNamespace(AnixartClient=FakeClient),
    )
    monkeypatch.delenv("ANIXART_TOKEN", raising=False)

    repo = create_repository()

    assert isinstance(repo, ConnectorRepository)
    assert FakeClient.instances[-1].token is None


def test_factory_passes_token_from_environment(monkeypatch):
    FakeClient.instances.clear()
    monkeypatch.setenv("ANIXART_TOKEN", "super-secret")
    monkeypatch.setattr(
        connector_adapter,
        "connector_module",
        lambda: SimpleNamespace(AnixartClient=FakeClient),
    )

    repo = create_repository()

    assert isinstance(repo, ConnectorRepository)
    assert FakeClient.instances[-1].token == "super-secret"


def test_factory_passes_profile_id_from_environment(monkeypatch):
    FakeClient.instances.clear()
    monkeypatch.setenv("ANIXART_TOKEN", "super-secret")
    monkeypatch.setenv("ANIXART_PROFILE_ID", "12345")
    monkeypatch.setattr(
        connector_adapter,
        "connector_module",
        lambda: SimpleNamespace(AnixartClient=FakeClient),
    )

    repo = create_repository()

    assert isinstance(repo, ConnectorRepository)
    assert FakeClient.instances[-1].session.profile_id == 12345


def test_factory_raises_when_client_construction_fails(monkeypatch):
    class BrokenClient:
        def __init__(self):
            raise RuntimeError("cannot construct")

    monkeypatch.setattr(
        connector_adapter,
        "connector_module",
        lambda: SimpleNamespace(AnixartClient=BrokenClient),
    )

    with pytest.raises(RuntimeError, match="Could not initialise"):
        create_repository()


def test_login_and_logout_use_api_session(monkeypatch):
    monkeypatch.setenv("ANIXART_TOKEN", "environment-token")
    client = FakeClient()
    repo = ConnectorRepository(client)
    response = object()
    calls = []

    def login(login, password):
        calls.append((login, password))
        client.set_token("session-token", profile_id=7)
        return response

    def logout():
        calls.append("logout")
        client.set_token(None)

    client.auth = SimpleNamespace(login=login, logout=logout)
    assert repo.is_authenticated is False
    assert repo.login("test-user", "test-password") is response
    assert repo.is_authenticated is True
    repo.logout()
    assert repo.is_authenticated is False
    assert repo.fetch_history(1, 12).items == ()
    assert client.history.calls == []
    assert calls == [("test-user", "test-password"), "logout"]


def test_login_propagates_api_errors():
    client = FakeClient()
    error = ValueError("sign-in failed")

    def login(login, password):
        raise error

    client.auth = SimpleNamespace(login=login)
    repo = ConnectorRepository(client)
    with pytest.raises(ValueError) as caught:
        repo.login("test-user", "test-password")
    assert caught.value is error
    assert repo.is_authenticated is False
