"""Model parsing tests built from synthetic examples in docs/api.md."""

from __future__ import annotations

from anx_desktop.api.models import (
    Article,
    Badge,
    CommentAddResponse,
    ConfigUrlsResponse,
    EpisodeResponse,
    PageableResponse,
    Profile,
    ProfileBadgePageableResponse,
    ProfileListStatus,
    ProfileNotification,
    ProfilePreferenceResponse,
    ProfileResponse,
    ProfileRoleLevel,
    Release,
    ReleaseComment,
    ReleaseSearchResponse,
    Source,
)


def test_release_example_from_docs():
    release = Release.model_validate(
        {
            "id": 42,
            "title_ru": "Example",
            "year": "2024",
            "status": {"id": 1, "name": "Ongoing"},
            "grade": 4.5,
            "is_favorite": False,
            "unknown_field": "ignored",
        }
    )

    assert release.id == 42
    assert release.title_ru == "Example"
    assert release.year == "2024"
    assert release.status is not None and release.status.name == "Ongoing"
    assert release.grade == 4.5
    assert release.is_favorite is False


def test_source_type_accepts_object_or_bare_id():
    """Live source lists mix ``type: {...}`` and ``type: <id>``."""

    by_id = Source.model_validate({"id": 1, "name": "voice", "type": 2})
    by_object = Source.model_validate(
        {"id": 2, "name": "voice", "type": {"id": 2, "name": "voice"}}
    )

    assert by_id.type == 2
    assert by_object.type is not None and by_object.type.id == 2


def test_episode_list_tolerates_at_id_wire_name():
    """Live episode items use ``@id`` and have no ``id`` field."""

    response = EpisodeResponse.model_validate(
        {
            "code": 0,
            "episodes": [
                {
                    "@id": 11,
                    "releaseId": 42,
                    "sourceId": 3,
                    "position": 1,
                    "name": "Episode 1",
                    "url": "https://s.example/episode.m3u8",
                    "iframe": False,
                    "quality": 1080,
                    "release": 42,
                    "source": 3,
                }
            ],
        }
    )

    assert response.episodes[0].id == 11
    assert response.episodes[0].position == 1
    assert response.episodes[0].release == 42
    assert response.episodes[0].source == 3


def test_release_comment_accepts_object_or_bare_release_id():
    """Live comment lists mix ``release: {...}`` and ``release: <id>``."""

    by_id = ReleaseComment.model_validate(
        {"id": 1, "message": "text", "release": 42}
    )
    by_object = ReleaseComment.model_validate(
        {"id": 2, "message": "text", "release": {"id": 42}}
    )

    assert by_id.release == 42
    assert isinstance(by_object.release, Release)
    assert by_object.release.id == 42


def test_release_screenshot_animations_allow_null_entries():
    """Live releases contain ``screenshot_animations: [null, ...]``."""

    release = Release.model_validate(
        {
            "id": 1,
            "screenshot_images": ["https://s.example/1.jpg"],
            "screenshot_animations": [None, "https://s.example/1.webp"],
        }
    )

    assert release.screenshot_images == ["https://s.example/1.jpg"]
    assert release.screenshot_animations == [None, "https://s.example/1.webp"]


def test_release_year_numeric_is_tolerated():
    release = Release.model_validate({"id": 1, "year": 2024})
    assert release.year == "2024"


def test_profile_response_example_from_docs():
    response = ProfileResponse.model_validate(
        {
            "code": 0,
            "profile": {
                "id": 1,
                "login": "example",
                "avatar": "https://s.example/avatars/no_avatar.jpg",
                "isSponsor": True,
                "rating_score": 15,
                "privilege_level": 2,
            },
            "is_my_profile": False,
        }
    )

    assert response.profile is not None
    assert response.profile.id == 1
    assert response.profile.login == "example"
    assert response.profile.is_sponsor is True
    assert response.profile.rating_score == 15
    assert response.profile.privilege_level is ProfileRoleLevel.RELEASER
    assert response.is_my_profile is False


def test_history_page_example_from_docs():
    page = PageableResponse[Release].model_validate(
        {
            "code": 0,
            "content": [
                {
                    "id": 42,
                    "title_ru": "Example",
                    "last_view_episode_name": "1",
                    "last_view_timestamp": 1700000000,
                }
            ],
            "current_page": 1,
            "total_count": 1,
            "total_page_count": 1,
        }
    )

    assert page.total_page_count == 1
    assert page.content[0].last_view_episode_name == "1"
    assert page.content[0].last_view_timestamp == 1700000000


def test_release_search_is_bare_list_not_pageable():
    response = ReleaseSearchResponse.model_validate(
        {
            "code": 0,
            "releases": [{"id": 42, "title_ru": "Example"}],
            "related": None,
        }
    )

    assert [release.id for release in response.releases] == [42]
    assert response.related is None


def test_release_comment_add_example_from_docs():
    response = CommentAddResponse[ReleaseComment].model_validate(
        {
            "code": 0,
            "comment": {"id": 100, "message": "Synthetic comment", "vote_count": 0},
        }
    )

    assert response.comment is not None
    assert response.comment.id == 100
    assert response.comment.message == "Synthetic comment"
    assert response.comment.vote_count == 0


def test_article_feed_model_from_docs_example():
    article = Article.model_validate(
        {
            "id": 5,
            "author": {"id": 1, "login": "example"},
            "channel": {"id": 3, "title": "Example channel"},
            "payload": {"version": "2.26.5", "blocks": []},
            "comment_count": 0,
            "vote": 0,
            "is_pinned": False,
        }
    )

    assert article.author is not None
    assert article.channel is not None
    assert article.payload is not None
    assert article.author.login == "example"
    assert article.channel.title == "Example channel"
    assert article.payload.version == "2.26.5"
    assert article.is_pinned is False


def test_config_urls_has_no_code_field():
    response = ConfigUrlsResponse.model_validate(
        {
            "api_urls": ["https://api-s.anixsekai.com/"],
            "editor_url": "https://example.invalid/editor",
            "static_domain": "anixmirai.com",
            "should_use_mirror_urls": False,
            "consent_required": False,
        }
    )
    assert response.api_urls == ["https://api-s.anixsekai.com/"]
    assert response.static_domain == "anixmirai.com"


def test_unknown_enum_value_does_not_crash():
    assert Release.model_validate({"id": 1, "profile_list_status": 99}).profile_list_status is ProfileListStatus.UNKNOWN
    assert ProfileListStatus(1) is ProfileListStatus.WATCHING
    assert ProfileListStatus(99) is ProfileListStatus.UNKNOWN


def test_badge_rarity_is_a_string():
    badge = Badge.model_validate({"id": 1, "name": "Badge", "rarity": "legendary"})
    assert badge.rarity == "legendary"
    assert Badge.model_validate({"id": 2, "name": "Badge"}).rarity is None


def test_profile_theme_fields_use_strings_and_floats():
    profile = Profile.model_validate(
        {
            "id": 1,
            "login": "example",
            "themeAnimationSpeed": "fast",
            "themeBackgroundMode": "gradient",
            "themeGradientAngle": "180",
            "themeIconDensity": "compact",
            "themeIconSize": "large",
            "themeBackgroundAlpha": 0.75,
            "themeIconAlpha": 1,
        }
    )

    assert profile.theme_animation_speed == "fast"
    assert profile.theme_background_mode == "gradient"
    assert profile.theme_gradient_angle == "180"
    assert profile.theme_icon_density == "compact"
    assert profile.theme_icon_size == "large"
    assert profile.theme_background_alpha == 0.75
    assert profile.theme_icon_alpha == 1.0
    assert isinstance(profile.theme_icon_alpha, float)

    empty = Profile.model_validate({"id": 2, "login": "example"})
    assert empty.theme_animation_speed is None
    assert empty.theme_background_alpha is None


def test_profile_preference_episode_widget_is_boolean():
    hidden = ProfilePreferenceResponse.model_validate(
        {"code": 0, "episodeChannelWidgetsHidden": True}
    )
    visible = ProfilePreferenceResponse.model_validate(
        {"code": 0, "episodeChannelWidgetsHidden": False}
    )
    absent = ProfilePreferenceResponse.model_validate({"code": 0})

    assert hidden.episode_channel_widgets_hidden is True
    assert visible.episode_channel_widgets_hidden is False
    assert absent.episode_channel_widgets_hidden is None


def test_profile_preference_privacy_and_bind_fields():
    response = ProfilePreferenceResponse.model_validate(
        {
            "code": 0,
            "privacyCounts": 2,
            "privacySocial": 1,
            "privacyStats": 0,
            "privacyFriendRequests": 3,
            "isIncognito": True,
            "isLoginChanged": False,
            "isChangeAvatarBanned": True,
            "isChangeLoginBanned": False,
        }
    )

    assert response.privacy_counts == 2
    assert response.privacy_social == 1
    assert response.privacy_stats == 0
    assert response.privacy_friend_requests == 3
    assert response.is_incognito is True
    assert response.is_login_changed is False
    assert response.is_change_avatar_banned is True
    assert response.is_change_login_banned is False

    absent = ProfilePreferenceResponse.model_validate({"code": 0})
    assert absent.privacy_counts is None
    assert absent.is_incognito is None


def test_release_new_optional_fields():
    release = Release.model_validate(
        {
            "id": 42,
            "age_rating": "16+",
            "translators": ["First", "Second"],
            "aired_on_date": "2020-01-01",
            "creation_date": 1600000000,
            "last_update_date": 1700000000,
            "profileReleaseTypeNotificationPreferences": [
                {"release_type": 1, "is_enabled": True}
            ],
        }
    )

    assert release.age_rating == "16+"
    assert release.translators == ["First", "Second"]
    assert release.aired_on_date == "2020-01-01"
    assert release.creation_date == 1600000000
    assert release.last_update_date == 1700000000
    assert release.profile_release_type_notification_preferences == [
        {"release_type": 1, "is_enabled": True}
    ]


def test_release_new_optional_fields_default_to_none():
    release = Release.model_validate({"id": 42, "title_ru": "Example"})

    assert release.age_rating is None
    assert release.translators is None
    assert release.aired_on_date is None
    assert release.creation_date is None
    assert release.last_update_date is None
    assert release.profile_release_type_notification_preferences is None


def test_unknown_notification_fields_are_ignored():
    notification = ProfileNotification.model_validate(
        {
            "id": 10,
            "timestamp": 1700000000,
            "is_new": True,
            "some_future_payload": {"x": 1},
        }
    )
    assert notification.id == 10
    assert notification.is_new is True


def test_profile_badge_pageable_keeps_envelope_and_profile():
    page = ProfileBadgePageableResponse.model_validate(
        {
            "code": 0,
            "content": [{"id": 1, "name": "Badge"}],
            "current_page": 1,
            "total_count": 1,
            "total_page_count": 1,
            "profile": {"id": 7, "login": "example"},
        }
    )
    assert page.content[0].name == "Badge"
    assert page.profile is not None
    assert page.profile.id == 7
