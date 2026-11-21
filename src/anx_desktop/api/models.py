"""Pydantic v2 models reconstructed from ``docs/api.md`` §6.

Design rules from the specification:

* unknown response fields are ignored (Jackson tolerance, §3.3);
* wire names are mixed camelCase / snake_case, so every field whose wire name
  is not the Python name has an explicit alias;
* almost every response field is treated as optional unless §6 explicitly
  guarantees presence (§3.3, "Nullability");
* numeric enums documented with literal values use ``IntEnum`` with an
  ``UNKNOWN`` fallback, because the application is forward-compatible and the
  docs warn that unknown values must not crash the client (§7, §10.4).

The one documented enum whose wire representation is *not* known
(``AppealStatus``/``EntityType`` and friends, §7.2) is intentionally kept as a
plain ``int``/``str`` rather than being guessed.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Generic, TypeVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class AnixartModel(BaseModel):
    """Base model with the tolerance rules required by the API docs."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TolerantIntEnum(IntEnum):
    """Numeric enum mixin that maps unknown values to ``UNKNOWN`` (§7).

    Python 3.12 does not allow extending an enum that already has members, so
    each concrete enum below declares its own ``UNKNOWN`` member.
    """

    @classmethod
    def _missing_(cls, value: object) -> TolerantIntEnum:
        return cls.UNKNOWN  # type: ignore[attr-defined]


class ProfileListStatus(TolerantIntEnum):
    """Profile-list status, §7.2 (exact numeric values are documented)."""

    UNKNOWN = -1
    WATCHING = 1
    PLAN = 2
    COMPLETED = 3
    HOLD_ON = 4
    DROPPED = 5


class ChannelPermission(TolerantIntEnum):
    """Channel permission, §7.2."""

    UNKNOWN = -1
    MEMBER = 0
    ADMINISTRATOR = 1
    CREATOR = 2


class ProfileRoleLevel(TolerantIntEnum):
    """Profile role/privilege level, §7.2."""

    UNKNOWN = -1
    NONE = 0
    MEMBER = 1
    RELEASER = 2
    MODERATOR = 3
    ADMINISTRATOR = 4
    DEVELOPER = 5


class FriendStatus(TolerantIntEnum):
    """Friend-request state, §7.2."""

    UNKNOWN = -1
    PENDING_FIRST_SECOND = 0
    PENDING_SECOND_FIRST = 1
    FRIEND = 2


class SortOrder(TolerantIntEnum):
    """Filter sort constants, §7.3."""

    UNKNOWN = -1
    DATE_UPDATE_DESC = 0
    GRADE_DESC = 1
    YEAR_DESC = 2
    POPULAR_DESC = 3
    DATE_UPDATE_ASC = 4
    GRADE_ASC = 5
    YEAR_ASC = 6
    POPULAR_ASC = 7


class GenreMode(TolerantIntEnum):
    """Filter genre mode, §7.3."""

    UNKNOWN = -1
    ALL = 0
    ANY = 1
    EXCLUDE = 2


class AgeRating(TolerantIntEnum):
    """Filter age-rating constants, §7.3."""

    UNKNOWN = -1
    LESS_THAN_13 = 1
    MORE_THAN_13 = 2
    MORE_THAN_26 = 3
    MORE_THAN_100 = 4


# ---------------------------------------------------------------------------
# Common envelopes (§6.1)
# ---------------------------------------------------------------------------


class Response(AnixartModel):
    """Base response envelope ``{code}``, §6.1."""

    code: int = 0


class PageableResponse(Response, Generic[T]):
    """Paged envelope from §3.4 / §6.1.

    Only path-based page numbers exist; the docs explicitly say there is no
    cursor/limit/offset API.  ``content`` defaults to an empty list because the
    docs describe it as "no (default empty)".
    """

    content: list[T] = Field(default_factory=list)
    current_page: int = 1
    total_count: int = 0
    total_page_count: int = 0


# ---------------------------------------------------------------------------
# Profile and social models (§6.3)
# ---------------------------------------------------------------------------


class ProfileGenre(AnixartModel):
    name: str | None = None
    percentage: float | None = None


class ProfileWatchDynamics(AnixartModel):
    id: int | None = None
    day: int | None = None
    count: int | None = None
    timestamp: int | None = None


class RoleDto(AnixartModel):
    id: int | None = None
    name: str | None = None
    color: str | None = None


class BadgeAward(AnixartModel):
    trigger: str | None = None
    release_id: int | None = Field(default=None, alias="releaseId")
    release_image: str | None = Field(default=None, alias="releaseImage")
    release_title: str | None = Field(default=None, alias="releaseTitle")
    episode_name: str | None = Field(default=None, alias="episodeName")
    profile_list_status: int | None = Field(default=None, alias="profileListStatus")


class BadgeCategory(AnixartModel):
    id: int | None = None
    title: str | None = None


class Badge(AnixartModel):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    rarity: str | None = None
    type: int | None = None
    image_small_url: str | None = Field(default=None, alias="imageSmallUrl")
    image_medium_url: str | None = Field(default=None, alias="imageMediumUrl")
    image_url: str | None = Field(default=None, alias="imageUrl")
    is_available: bool | None = Field(default=None, alias="isAvailable")
    is_owned: bool | None = Field(default=None, alias="isOwned")
    is_selected: bool | None = Field(default=None, alias="isSelected")
    is_showcased: bool | None = Field(default=None, alias="isShowcased")
    ownership_percentage: float | None = Field(default=None, alias="ownershipPercentage")
    timestamp: int | None = None
    award: BadgeAward | None = None
    category: BadgeCategory | None = None


class BadgeSection(AnixartModel):
    id: int | None = None
    title: str | None = None
    count: int | None = None
    content: list[Badge] = Field(default_factory=list)


class Profile(AnixartModel):
    """Large profile object from §6.3.

    Only fields with a documented wire name are listed.  Nested previews whose
    full schema is not recovered (§6.12) are kept as ``Any`` on purpose.
    """

    id: int
    login: str
    avatar: str | None = None
    avatar_animation: str | None = None
    status: str | None = None

    vk_page: str | None = None
    tg_page: str | None = None
    inst_page: str | None = None
    tt_page: str | None = None
    discord_page: str | None = None

    is_social: bool | None = Field(default=None, alias="isSocial")
    is_social_hidden: bool | None = Field(default=None, alias="is_social_hidden")
    is_verified: bool | None = Field(default=None, alias="isVerified")
    is_online: bool | None = Field(default=None, alias="isOnline")
    is_sponsor: bool | None = Field(default=None, alias="isSponsor")

    is_banned: bool | None = Field(default=None, alias="isBanned")
    is_perm_banned: bool | None = Field(default=None, alias="isPermBanned")
    ban_expires: int | None = Field(default=None, alias="ban_expires")
    ban_reason: str | None = Field(default=None, alias="ban_reason")
    is_deleted: bool | None = Field(default=None, alias="isDeleted")
    is_deletion_requested: bool | None = Field(default=None, alias="is_deletion_requested")
    deletion_requested_at: int | None = Field(default=None, alias="deletion_requested_at")
    deletion_delete_at: int | None = Field(default=None, alias="deletion_delete_at")

    is_blocked: bool | None = Field(default=None, alias="isBlocked")
    is_me_blocked: bool | None = Field(default=None, alias="is_me_blocked")
    added_date: int | None = Field(default=None, alias="added_date")

    is_login_changed: bool | None = Field(default=None, alias="isLoginChanged")
    is_incognito: bool | None = Field(default=None, alias="isIncognito")
    last_activity_time: int | None = Field(default=None, alias="lastActivityTime")
    register_date: int | None = Field(default=None, alias="registerDate")

    watching_count: int | None = Field(default=None, alias="watchingCount")
    plan_count: int | None = Field(default=None, alias="planCount")
    completed_count: int | None = Field(default=None, alias="completedCount")
    hold_on_count: int | None = Field(default=None, alias="holdOnCount")
    dropped_count: int | None = Field(default=None, alias="droppedCount")
    favorite_count: int | None = Field(default=None, alias="favoriteCount")
    comment_count: int | None = Field(default=None, alias="commentCount")
    collection_count: int | None = Field(default=None, alias="collectionCount")
    video_count: int | None = Field(default=None, alias="videoCount")
    friend_count: int | None = Field(default=None, alias="friendCount")
    watched_episode_count: int | None = Field(default=None, alias="watchedEpisodeCount")
    watched_time: int | None = Field(default=None, alias="watchedTime")

    rating_score: int | None = None
    privilege_level: ProfileRoleLevel | None = None

    pinned_section_id: int | None = Field(default=None, alias="pinnedSectionId")
    friend_status: FriendStatus | None = Field(default=None, alias="friendStatus")
    roles: list[RoleDto] | None = None
    badge: Badge | None = None
    badge_id: int | None = Field(default=None, alias="badgeId")
    badge_name: str | None = Field(default=None, alias="badgeName")
    badge_type: int | None = Field(default=None, alias="badgeType")
    badge_url: str | None = Field(default=None, alias="badgeUrl")
    badge_count: int | None = Field(default=None, alias="badge_count")
    badges_preview: list[Badge] | None = Field(default=None, alias="badges_preview")

    collections_preview: list[Any] | None = Field(default=None, alias="collectionsPreview")
    comments_preview: list[Any] | None = Field(default=None, alias="commentsPreview")
    friends_preview: list[Any] | None = Field(default=None, alias="friendsPreview")
    history: list[Any] | None = None
    votes: list[Any] | None = None
    release_videos_preview: list[Any] | None = Field(default=None, alias="releaseVideosPreview")
    watch_dynamics: list[ProfileWatchDynamics] | None = Field(default=None, alias="watchDynamics")

    preferred_audiences: list[ProfileGenre] | None = Field(default=None, alias="preferredAudiences")
    preferred_genres: list[ProfileGenre] | None = Field(default=None, alias="preferredGenres")
    preferred_themes: list[ProfileGenre] | None = Field(default=None, alias="preferredThemes")

    is_stats_hidden: bool | None = Field(default=None, alias="isStatsHidden")
    is_counts_hidden: bool | None = Field(default=None, alias="isCountsHidden")
    is_comment_notifications_enabled: bool | None = Field(default=None, alias="isCommentNotificationsEnabled")
    is_episode_notifications_enabled: bool | None = Field(default=None, alias="isEpisodeNotificationsEnabled")
    is_first_episode_notification_enabled: bool | None = Field(
        default=None, alias="isFirstEpisodeNotificationEnabled"
    )
    is_friend_requests_disallowed: bool | None = Field(default=None, alias="isFriendRequestsDisallowed")

    is_vk_bound: bool | None = Field(default=None, alias="isVkBound")
    is_google_bound: bool | None = Field(default=None, alias="isGoogleBound")
    is_telegram_bound: bool | None = Field(default=None, alias="isTelegramBound")
    is_yandex_bound: bool | None = Field(default=None, alias="isYandexBound")

    theme_enabled: bool | None = Field(default=None, alias="themeEnabled")
    theme_animation_enabled: bool | None = Field(default=None, alias="themeAnimationEnabled")
    theme_animation_speed: str | None = Field(default=None, alias="themeAnimationSpeed")
    theme_background_alpha: float | None = Field(default=None, alias="themeBackgroundAlpha")
    theme_background_mode: str | None = Field(default=None, alias="themeBackgroundMode")
    theme_background_url: str | None = Field(default=None, alias="themeBackgroundUrl")
    theme_gradient_angle: str | None = Field(default=None, alias="themeGradientAngle")
    theme_gradient_end_color: str | None = Field(default=None, alias="themeGradientEndColor")
    theme_gradient_start_color: str | None = Field(default=None, alias="themeGradientStartColor")
    theme_icon_alpha: float | None = Field(default=None, alias="themeIconAlpha")
    theme_icon_color: str | None = Field(default=None, alias="themeIconColor")
    theme_icon_density: str | None = Field(default=None, alias="themeIconDensity")
    theme_icon_res_name: str | None = Field(default=None, alias="themeIconResName")
    theme_icon_size: str | None = Field(default=None, alias="themeIconSize")
    theme_icon_url: str | None = Field(default=None, alias="themeIconUrl")


class ProfileCompact(AnixartModel):
    id: int
    login: str
    avatar: str | None = None
    badge_id: int | None = Field(default=None, alias="badgeId")
    badge_name: str | None = Field(default=None, alias="badgeName")
    badge_type: int | None = Field(default=None, alias="badgeType")
    badge_url: str | None = Field(default=None, alias="badgeUrl")
    ban_expires: int | None = Field(default=None, alias="banExpires")
    ban_reason: str | None = Field(default=None, alias="banReason")
    is_banned: bool | None = Field(default=None, alias="isBanned")
    is_sponsor: bool | None = Field(default=None, alias="isSponsor")
    is_verified: bool | None = Field(default=None, alias="isVerified")
    privilege_level: ProfileRoleLevel | None = Field(default=None, alias="privilegeLevel")


class ProfileSlim(AnixartModel):
    id: int
    login: str
    avatar: str | None = None


class ChannelProfile(AnixartModel):
    channel_id: int
    permission: ChannelPermission | None = None
    permission_creation_date: int | None = None
    is_blocked: bool | None = None
    is_perm_blocked: bool | None = None
    block_expire_date: int | None = None
    block_reason: str | None = None


class ProfileRole(ProfileCompact):
    is_online: bool | None = Field(default=None, alias="is_online")
    roles: list[RoleDto] | None = None


class ProfileResponse(Response):
    profile: Profile | None = None
    is_my_profile: bool | None = None


class ProfileListResponse(Response):
    """Profile-list add/delete acknowledgement; payload fields are ``UNKNOWN``."""


class ProfileInfoResponse(Response):
    ban_expires: int | None = None
    channel_id: int | None = None
    is_banned: bool | None = None
    is_perm_banned: bool | None = None
    is_sponsor: bool | None = None
    privilege_level: ProfileRoleLevel | None = None
    rating_score: int | None = None
    sponsorship_expires: int | None = None


class ProfileSocialResponse(Response):
    vk_page: str | None = Field(default=None, alias="vkPage")
    tg_page: str | None = Field(default=None, alias="tgPage")
    inst_page: str | None = Field(default=None, alias="instPage")
    tt_page: str | None = Field(default=None, alias="ttPage")
    discord_page: str | None = Field(default=None, alias="discordPage")


class ProfilePreferenceResponse(Response):
    avatar: str | None = None
    status: str | None = None
    vk_page: str | None = Field(default=None, alias="vkPage")
    tg_page: str | None = Field(default=None, alias="tgPage")
    available_themes: list[Any] | None = Field(default=None, alias="availableThemes")
    selected_theme_id: int | None = Field(default=None, alias="selectedThemeId")
    pinned_section_id: int | None = Field(default=None, alias="pinnedSectionId")
    email_hint: str | None = Field(default=None, alias="emailHint")
    episode_channel_widgets_hidden: bool | None = Field(
        default=None, alias="episodeChannelWidgetsHidden"
    )
    is_vk_bound: bool | None = Field(default=None, alias="isVkBound")
    is_google_bound: bool | None = Field(default=None, alias="isGoogleBound")
    is_telegram_bound: bool | None = Field(default=None, alias="isTelegramBound")
    is_yandex_bound: bool | None = Field(default=None, alias="isYandexBound")
    privacy_counts: int | None = Field(default=None, alias="privacyCounts")
    privacy_social: int | None = Field(default=None, alias="privacySocial")
    privacy_stats: int | None = Field(default=None, alias="privacyStats")
    privacy_friend_requests: int | None = Field(default=None, alias="privacyFriendRequests")
    is_incognito: bool | None = Field(default=None, alias="isIncognito")
    is_login_changed: bool | None = Field(default=None, alias="isLoginChanged")
    is_change_avatar_banned: bool | None = Field(default=None, alias="isChangeAvatarBanned")
    is_change_login_banned: bool | None = Field(default=None, alias="isChangeLoginBanned")
    ban_change_avatar_expires: int | None = Field(default=None, alias="banChangeAvatarExpires")
    ban_change_login_expires: int | None = Field(default=None, alias="banChangeLoginExpires")
    channel_id: int | None = Field(default=None, alias="channelId")
    badge: Badge | None = None


class ProfileDeletionResponse(Response):
    requested_at: int | None = None
    delete_at: int | None = None


class ProfileHealthStatusResponse(Response):
    ban_count: int | None = Field(default=None, alias="banCount")
    ban_for_3_month_count: int | None = Field(default=None, alias="banFor3MonthCount")
    last_ban_timestamp: int | None = Field(default=None, alias="lastBanTimestamp")
    last_ban_expires: int | None = Field(default=None, alias="lastBanExpires")
    blog_mute_expires: int | None = Field(default=None, alias="blogMuteExpires")
    blog_suspension_expires: int | None = Field(default=None, alias="blogSuspensionExpires")


class ProfileEnforcement(AnixartModel):
    id: int | None = None
    reason: str | None = None
    creation_timestamp: int | None = Field(default=None, alias="creationTimestamp")
    is_revoked: bool | None = Field(default=None, alias="isRevoked")
    revocation_timestamp: int | None = Field(default=None, alias="revocationTimestamp")
    entity_type: Any | None = Field(default=None, alias="entityType")
    target_entity_type: Any | None = Field(default=None, alias="targetEntityType")
    appeal_status: Any | None = Field(default=None, alias="appealStatus")
    appeal_type: Any | None = Field(default=None, alias="appealType")
    appeal_submit_timestamp: int | None = Field(default=None, alias="appealSubmitTimestamp")
    appeal_process_timestamp: int | None = Field(default=None, alias="appealProcessTimestamp")
    appeal_process_message: str | None = Field(default=None, alias="appealProcessMessage")
    appeal_expires_timestamp: int | None = Field(default=None, alias="appealExpiresTimestamp")


class ProfileEnforcementResponse(Response):
    enforcement: ProfileEnforcement | None = None


class ProfileBadgeSectionsResponse(Response):
    profile: Profile | None = None
    recent: list[Badge] = Field(default_factory=list)
    sections: list[BadgeSection] = Field(default_factory=list)
    showcased: list[Badge] = Field(default_factory=list)
    total_count: int | None = None


class ProfileBadgePageableResponse(PageableResponse[Badge]):
    profile: Profile | None = None


# ---------------------------------------------------------------------------
# Release, video, taxonomy models (§6.4)
# ---------------------------------------------------------------------------


class Category(AnixartModel):
    id: int | None = None
    name: str | None = None


class Genre(AnixartModel):
    id: int | None = None
    name: str | None = None


class ReleaseStatus(AnixartModel):
    id: int | None = None
    name: str | None = None


class ReleaseCompact(AnixartModel):
    id: int
    image: str | None = None
    title_ru: str | None = None


class Related(AnixartModel):
    id: int | None = None
    name_ru: str | None = None
    description: str | None = None
    image: str | None = None
    cover_animation: str | None = None
    images: list[str] | None = None
    release_count: int | None = None


class Interesting(AnixartModel):
    id: int | None = None
    title: str | None = None
    description: str | None = None
    image: str | None = None
    image_animation: str | None = Field(default=None, alias="image_animation")
    action: int | None = None
    type: int | None = None
    is_hidden: bool | None = Field(default=None, alias="isHidden")


class ReleaseVideoCategory(AnixartModel):
    id: int | None = None
    name: str | None = None


class ReleaseVideoHosting(AnixartModel):
    id: int | None = None
    name: str | None = None
    icon: str | None = None


class ReleaseVideoBanner(AnixartModel):
    name: str | None = None
    image: str | None = None
    value: str | None = None
    action_id: int | None = Field(default=None, alias="action_id")
    is_new: bool | None = Field(default=None, alias="is_new")


class ReleaseVideo(AnixartModel):
    id: int | None = None
    title: str | None = None
    url: str | None = None
    player_url: str | None = None
    image: str | None = None
    timestamp: int | None = None
    favorites_count: int | None = None
    is_favorite: bool | None = None
    release: Release | None = None
    profile: ProfileCompact | None = None
    category: ReleaseVideoCategory | None = None
    hosting: ReleaseVideoHosting | None = None


class ReleaseVideoBlock(AnixartModel):
    category: ReleaseVideoCategory | None = None
    videos: list[ReleaseVideo] = Field(default_factory=list)


class ReleaseStreamingPlatform(AnixartModel):
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    url: str | None = None
    release: Release | None = None


class Release(AnixartModel):
    """Central release model, §6.4.  Wire names are mixed by design.

    ``age_rating``, ``translators``, ``aired_on_date``, ``creation_date``,
    ``last_update_date`` and ``profile_release_type_notification_preferences``
    exist in the application (A4) but are absent from ``docs/api.md`` §6.4.

    TODO: their exact wire types are not documented in the allowed sources;
    they are intentionally kept as ``Any`` until captured from real responses.
    """

    id: int
    title_ru: str | None = None
    title_original: str | None = None
    title_alt: str | None = None
    year: str | None = None
    description: str | None = None
    author: str | None = None
    director: str | None = None
    studio: str | None = None
    source: str | None = None
    country: str | None = None
    genres: str | None = None
    release_date: str | None = None
    aired_on_date: Any | None = None
    creation_date: Any | None = None
    last_update_date: Any | None = None
    duration: int | None = None
    season: int | None = None
    age_rating: Any | None = None
    translators: Any | None = None

    episodes_total: int | None = None
    episodes_released: int | None = None

    status: ReleaseStatus | None = None
    status_id: int | None = None
    rating: float | None = None
    grade: float | None = None
    vote_count: int | None = None
    your_vote: int | None = None
    my_vote: int | None = None
    voted_at: int | None = None
    vote_1_count: int | None = None
    vote_2_count: int | None = None
    vote_3_count: int | None = None
    vote_4_count: int | None = None
    vote_5_count: int | None = None

    watching_count: int | None = Field(default=None, alias="watchingCount")
    plan_count: int | None = Field(default=None, alias="planCount")
    completed_count: int | None = Field(default=None, alias="completedCount")
    hold_on_count: int | None = Field(default=None, alias="holdOnCount")
    dropped_count: int | None = Field(default=None, alias="droppedCount")
    favorites_count: int | None = None
    comment_count: int | None = Field(default=None, alias="commentCount")
    collection_count: int | None = Field(default=None, alias="collectionCount")
    related_count: int | None = Field(default=None, alias="relatedCount")
    badge_count: int | None = Field(default=None, alias="badgeCount")
    comment_per_day_count: int | None = Field(default=None, alias="commentPerDayCount")

    category: Category | None = None
    related: Related | None = None
    related_releases: list[Release] | None = Field(default=None, alias="relatedReleases")
    recommended_releases: list[Release] | None = Field(default=None, alias="recommendedReleases")
    profile_release_type_notification_preferences: Any | None = Field(
        default=None, alias="profileReleaseTypeNotificationPreferences"
    )
    comments: list[Any] | None = None
    badges_preview: list[Badge] | None = Field(default=None, alias="badgesPreview")
    video_banners: list[ReleaseVideoBanner] | None = Field(default=None, alias="videoBanners")
    last_view_episode: Any | None = Field(default=None, alias="lastViewEpisode")
    last_view_episode_name: str | None = Field(default=None, alias="lastViewEpisodeName")
    last_view_episode_type_name: str | None = Field(default=None, alias="lastViewEpisodeTypeName")
    last_view_timestamp: int | None = Field(default=None, alias="lastViewTimestamp")
    episode_last_update: Any | None = Field(default=None, alias="episodeLastUpdate")

    image: str | None = None
    poster_animation: str | None = None
    screenshot_images: list[str] | None = None
    screenshot_animations: list[str | None] | None = None

    is_adult: bool | None = None
    is_deleted: bool | None = Field(default=None, alias="isDeleted")
    is_favorite: bool | None = Field(default=None, alias="isFavorite")
    is_viewed: bool | None = Field(default=None, alias="isViewed")
    is_view_blocked: bool | None = Field(default=None, alias="isViewBlocked")
    is_ru_blocked: bool | None = Field(default=None, alias="isRuBlocked")
    is_play_disabled: bool | None = Field(default=None, alias="isPlayDisabled")
    is_release_type_notifications_enabled: bool | None = Field(
        default=None, alias="isReleaseTypeNotificationsEnabled"
    )
    is_tpp_disabled: bool | None = None
    can_torlook_search: bool | None = None
    can_video_appeal: bool | None = None
    broadcast: Any | None = None

    profile_list_status: ProfileListStatus | None = None
    last_set_watching_date: int | None = Field(default=None, alias="lastSetWatchingDate")
    last_set_plan_date: int | None = Field(default=None, alias="lastSetPlanDate")
    last_set_completed_date: int | None = Field(default=None, alias="lastSetCompletedDate")
    last_set_hold_on_date: int | None = Field(default=None, alias="lastSetHoldOnDate")
    last_set_dropped_date: int | None = Field(default=None, alias="lastSetDroppedDate")
    last_set_favorite_date: int | None = Field(default=None, alias="lastSetFavoriteDate")
    last_set_viewed_date: int | None = Field(default=None, alias="lastSetViewedDate")
    note: str | None = None
    note_background_color_light: str | None = Field(default=None, alias="noteBackgroundColorLight")
    note_background_color_dark: str | None = Field(default=None, alias="noteBackgroundColorDark")
    note_text_color_light: str | None = Field(default=None, alias="noteTextColorLight")
    note_text_color_dark: str | None = Field(default=None, alias="noteTextColorDark")

    @field_validator("year", mode="before")
    @classmethod
    def _normalise_year(cls, value: Any) -> Any:
        """``Release.year`` is documented as a string; tolerate numeric JSON."""

        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return value


class ReleaseResponse(Response):
    release: Release | None = None


class ReleaseVideosResponse(Response):
    """``GET /video/release/{releaseId}`` response.

    ``docs/api.md`` §6.12 lists the payload fields of this model as
    ``UNKNOWN``; only the shared ``code`` envelope is modelled.
    """


class ReleaseVideoCategoriesResponse(Response):
    """``GET /video/release/categories`` response.

    ``docs/api.md`` §6.12 lists the payload fields as ``UNKNOWN``; only the
    shared ``code`` envelope is modelled.
    """


class VoteReleaseResponse(Response):
    """Vote acknowledgement; additional fields are ``UNKNOWN`` (§6.12)."""


class DeleteVoteReleaseResponse(Response):
    """Vote deletion acknowledgement; fields are ``UNKNOWN`` (§6.12)."""


class FavoritesResponse(Response):
    """Favorite add/delete acknowledgement; fields are ``UNKNOWN`` (§6.12)."""


# ---------------------------------------------------------------------------
# Episodes, sources, history (§6.5)
# ---------------------------------------------------------------------------


class ReleaseType(AnixartModel):
    """The docs call this model ``Type``; renamed to avoid clashing with typing."""

    id: int | None = None
    name: str | None = None
    icon: str | None = None
    workers: str | None = None
    quality: int | None = None
    episodes_count: int | None = None
    view_count: int | None = None
    pinned: bool | None = None
    is_sub: bool | None = None


class Source(AnixartModel):
    id: int | None = None
    name: str | None = None
    quality: int | None = None
    episodes_count: int | None = None
    # Live source lists mix a nested type object with a bare type id.
    type: ReleaseType | int | None = None


class Episode(AnixartModel):
    # Live episode payloads (11 BETA 2) expose the identity as ``@id`` and
    # omit ``id`` entirely; accept both wire forms.
    id: int = Field(validation_alias=AliasChoices("@id", "id"))
    name: str | None = None
    position: int | None = None
    quality: int | None = None
    url: str | None = None
    iframe: bool | None = None
    playback_position: int | None = Field(default=None, alias="playbackPosition")
    playback_duration: int | None = Field(default=None, alias="playbackDuration")
    added_date: int | None = Field(default=None, alias="addedDate")
    is_filler: bool | None = None
    is_watched: bool | None = None
    release_id: int | None = Field(default=None, alias="releaseId")
    source_id: int | None = Field(default=None, alias="sourceId")
    # Live episode lists mix nested objects with bare ids per item.
    release: Release | int | None = None
    source: Source | int | None = None


class EpisodeCompact(AnixartModel):
    name: str | None = None
    release: ReleaseCompact | None = None
    source: Source | None = None


class EpisodeUpdate(AnixartModel):
    last_episode_update_date: int | None = None
    last_episode_update_name: str | None = None
    last_episode_source_update_id: int | None = None
    last_episode_source_update_name: str | None = None
    last_episode_type_update_id: int | None = None
    last_episode_type_update_name: str | None = Field(default=None, alias="lastEpisodeTypeUpdateName")


class TypesResponse(Response):
    types: list[ReleaseType] = Field(default_factory=list)


class SourcesResponse(Response):
    sources: list[Source] = Field(default_factory=list)


class EpisodeResponse(Response):
    episodes: list[Episode] = Field(default_factory=list)


class EpisodeTargetResponse(Response):
    """``GET /episode/target/{releaseId}/{sourceId}/{position}`` response.

    Captured from 11 BETA 2 on 2026-11-08: ``{code, episode}`` where the
    episode object has the same shape as list items (``@id``, ``release``,
    ``source``, ``name``, ``url``, ``iframe``, ``quality``, …).
    """

    episode: Episode | None = None


class EpisodeWatchResponse(Response):
    """Watch acknowledgement; extra fields are ``UNKNOWN`` (§6.5)."""


class EpisodeUnwatchResponse(Response):
    """Unwatch acknowledgement; extra fields are ``UNKNOWN`` (§6.5)."""


class HistoryResponse(Response):
    """History add/delete acknowledgement (§6.5)."""


# ---------------------------------------------------------------------------
# Comments (§6.7)
# ---------------------------------------------------------------------------


class CommentBase(AnixartModel):
    id: int
    message: str
    timestamp: int | None = None
    type: int | None = None
    profile: ProfileCompact | ChannelProfile | None = None
    vote: int | None = None
    vote_count: int | None = None
    likes_count: int | None = None
    can_like: bool | None = None
    reply_count: int | None = None
    parent_comment_id: int | None = None
    is_reply: bool | None = None
    is_spoiler: bool | None = None
    is_edited: bool | None = None
    is_deleted: bool | None = None


class ReleaseComment(CommentBase):
    # Live list responses mix a full release object with a bare release id.
    release: Release | int | None = None
    posted_at_episode: int | None = None


class CommentCompact(AnixartModel):
    id: int | None = None
    message: str | None = None
    profile: ProfileCompact | None = None
    is_spoiler: bool | None = Field(default=None, alias="isSpoiler")
    embeddable_description: str | None = Field(default=None, alias="embeddableDescription")


class CommentWeek(AnixartModel):
    id: int | None = None
    message: str | None = None
    timestamp: int | None = None
    profile: ProfileCompact | None = None
    release: Release | None = None
    vote_count: int | None = None
    is_edited: bool | None = Field(default=None, alias="isEdited")
    is_spoiler: bool | None = Field(default=None, alias="isSpoiler")


class PopularComment(AnixartModel):
    id: int | None = None
    message: str | None = None
    timestamp: int | None = None
    profile: ProfileCompact | None = None
    vote_count: int | None = None


class CommentAddRequest(AnixartModel):
    message: str
    parent_comment_id: int | None = Field(default=None, alias="parentCommentId")
    reply_to_profile_id: int | None = Field(default=None, alias="replyToProfileId")
    spoiler: bool = False


class CommentEditRequest(AnixartModel):
    message: str
    spoiler: bool = False


class CommentProcessRequest(AnixartModel):
    message: str | None = None
    reason: int | None = None
    ban_reason: str | None = Field(default=None, alias="banReason")
    ban_expires: int | None = Field(default=None, alias="banExpires")
    is_banned: bool | None = None
    is_deleted: bool | None = None
    is_spoiler: bool | None = None


class CommentAddResponse(Response, Generic[T]):
    comment: T | None = None


class CommentEditResponse(Response):
    """Edit acknowledgement; diagnostic codes 2–7 (§6.7)."""


class CommentDeleteResponse(Response):
    """Delete acknowledgement; diagnostic codes 2–3 (§6.7)."""


# ---------------------------------------------------------------------------
# Articles and channels (§6.8)
# ---------------------------------------------------------------------------


class Channel(AnixartModel):
    id: int
    title: str | None = None
    description: str | None = None
    avatar: str | None = None
    cover: str | None = None
    avatar_animation: str | None = Field(default=None, alias="avatarAnimation")
    cover_animation: str | None = Field(default=None, alias="coverAnimation")
    permission: ChannelPermission | None = None
    is_subscribed: bool | None = Field(default=None, alias="isSubscribed")
    is_blocked: bool | None = Field(default=None, alias="isBlocked")
    is_perm_blocked: bool | None = Field(default=None, alias="isPermBlocked")
    is_muted: bool | None = Field(default=None, alias="isMuted")
    is_blog: bool | None = Field(default=None, alias="isBlog")
    is_deleted: bool | None = Field(default=None, alias="isDeleted")
    is_commenting_enabled: bool | None = Field(default=None, alias="isCommentingEnabled")
    is_article_suggestion_enabled: bool | None = Field(
        default=None, alias="isArticleSuggestionEnabled"
    )
    is_episode_channel_widget_enabled: bool | None = Field(
        default=None, alias="isEpisodeChannelWidgetEnabled"
    )
    is_linked_to_type: bool | None = Field(default=None, alias="isLinkedToType")
    is_verified: bool | None = Field(default=None, alias="isVerified")
    is_creator: bool | None = Field(default=None, alias="isCreator")
    is_administrator_or_higher: bool | None = Field(
        default=None, alias="isAdministratorOrHigher"
    )
    blog_profile_id: int | None = Field(default=None, alias="blogProfileId")
    article_count: int | None = Field(default=None, alias="articleCount")
    recent_article_count: int | None = Field(default=None, alias="recentArticleCount")
    subscriber_count: int | None = Field(default=None, alias="subscriberCount")
    badge_id: int | None = Field(default=None, alias="badgeId")
    badge_name: str | None = Field(default=None, alias="badgeName")
    badge_type: int | None = Field(default=None, alias="badgeType")
    badge_url: str | None = Field(default=None, alias="badgeUrl")
    block_expire_date: int | None = Field(default=None, alias="blockExpireDate")
    block_reason: str | None = Field(default=None, alias="blockReason")
    creation_date: int | None = Field(default=None, alias="creationDate")
    last_update_date: int | None = Field(default=None, alias="lastUpdateDate")
    last_article_date: int | None = Field(default=None, alias="lastArticleDate")
    episode_channel_widget_sort: int | None = Field(
        default=None, alias="episodeChannelWidgetSort"
    )
    episode_channel_widget_popularity_period: int | None = Field(
        default=None, alias="episodeChannelWidgetPopularityPeriod"
    )
    episode_channel_widget_article_count: int | None = Field(
        default=None, alias="episodeChannelWidgetArticleCount"
    )


class ArticlePayload(AnixartModel):
    version: str | None = None
    block_count: int | None = Field(default=None, alias="blockCount")
    blocks: list[Any] = Field(default_factory=list)
    is_collapse_available: bool | None = Field(default=None, alias="isCollapseAvailable")
    is_expand_available: bool | None = Field(default=None, alias="isExpandAvailable")
    time: int | None = None


class Article(AnixartModel):
    id: int
    author: ProfileSlim | None = None
    channel: Channel | None = None
    payload: ArticlePayload | None = None
    comment_count: int | None = None
    vote_count: int | None = None
    repost_count: int | None = None
    vote: int | None = None
    repost_article: Article | None = Field(default=None, alias="repostArticle")
    contains_repost_article: bool | None = None
    popular_comment: PopularComment | None = Field(default=None, alias="popularComment")
    is_pinned: bool | None = None
    is_signed: bool | None = None
    is_muted: bool | None = None
    is_deleted: bool | None = None
    has_delete_enforcement: bool | None = Field(default=None, alias="hasDeleteEnforcement")
    creation_date: int | None = Field(default=None, alias="creationDate")
    last_update_date: int | None = Field(default=None, alias="lastUpdateDate")


class ArticleCompact(AnixartModel):
    id: int
    channel: Channel | None = None
    payload: ArticlePayload | None = None
    creation_date: int | None = Field(default=None, alias="creationDate")
    last_update_date: int | None = Field(default=None, alias="lastUpdateDate")


class ChannelResponse(Response):
    channel: Channel | None = None
    suggestion_count: int | None = None


class LatestArticleResponse(Response):
    article_id: int | None = Field(
        default=None, validation_alias=AliasChoices("articleId", "article_id")
    )


class ReleaseSearchResponse(Response):
    """Release search is a bare list plus related block, §6.1/§5.8.2."""

    releases: list[Release] = Field(default_factory=list)
    related: Related | None = None


class FeedSearchResponse(Response):
    articles: PageableResponse[Article] | None = None
    blogs: PageableResponse[Channel] | None = None
    channels: PageableResponse[Channel] | None = None
    tags: PageableResponse[str] | None = None


# ---------------------------------------------------------------------------
# Notifications (§6.9)
# ---------------------------------------------------------------------------


class ProfileNotification(AnixartModel):
    """Base notification plus known subtype fields.

    There is no explicit discriminator (§6.9), so optional subtype fields are
    kept on the base model; unknown payloads are ignored.
    """

    id: int
    timestamp: int | None = None
    is_new: bool | None = None
    is_pushed: bool | None = None
    by_profile: ProfileCompact | None = None
    status: FriendStatus | None = None
    episode: EpisodeCompact | None = None
    comment: Any | None = None
    article: ArticleCompact | None = None
    release: ReleaseCompact | None = None


class ProfileFriendNotification(ProfileNotification):
    pass


class ProfileEpisodeNotification(ProfileNotification):
    pass


class ProfileReleaseCommentNotification(ProfileNotification):
    pass


class ProfileCollectionCommentNotification(ProfileNotification):
    pass


class ProfileArticleNotification(ProfileNotification):
    pass


class ProfileArticleCommentNotification(ProfileNotification):
    pass


class ProfileRelatedReleaseNotification(ProfileNotification):
    pass


class ProfileMyArticleCommentNotification(ProfileNotification):
    pass


class ProfileMyCollectionCommentNotification(ProfileNotification):
    pass


class UnsupportedProfileNotification(ProfileNotification):
    pass


class NotificationCountResponse(Response):
    count: int | None = None


class NotificationPreferenceResponse(Response):
    is_article_notifications_enabled: bool | None = None
    is_comment_notifications_enabled: bool | None = None
    is_episode_notifications_enabled: bool | None = None
    is_first_episode_notification_enabled: bool | None = None
    is_my_article_comment_notifications_enabled: bool | None = None
    is_my_collection_comment_notifications_enabled: bool | None = None
    is_related_release_notifications_enabled: bool | None = None
    is_release_type_notifications_enabled: bool | None = None
    is_report_process_notifications_enabled: bool | None = None


# ---------------------------------------------------------------------------
# Config / feature flags (§6.10)
# ---------------------------------------------------------------------------


class ConfigUrlsResponse(AnixartModel):
    """``GET /config/urls`` response; it has **no** ``code`` field (§6.10)."""

    api_urls: list[str] = Field(default_factory=list)
    editor_url: str | None = None
    static_domain: str | None = None
    should_use_mirror_urls: bool | None = None
    consent_required: bool | None = None
    google_auth_available: bool | None = None
    telegram_auth_available: bool | None = None
    vk_auth_available: bool | None = None
    yandex_auth_available: bool | None = None


class TogglesResponse(Response):
    """Runtime toggles; §6.10 documents ~55 mostly-camelCase fields.

    Only a representative, documented subset is modelled.  Unknown toggles are
    ignored by the base model config; callers that need them must extend this
    model once task 06 captures the complete payload.
    """

    min_version_code: int | None = Field(default=None, alias="minVersionCode")
    last_version_code: int | None = Field(default=None, alias="lastVersionCode")
    whats_new: str | None = Field(default=None, alias="whatsNew")
    download_link: str | None = Field(default=None, alias="downloadLink")
    base_url: str | None = Field(default=None, alias="baseUrl")
    iframe_embed_url: str | None = Field(default=None, alias="iframeEmbedUrl")
    editor_url: str | None = Field(default=None, alias="editorUrl")
    static_domain: str | None = Field(default=None, alias="staticDomain")
    codec_profile: str | None = Field(default=None, alias="codecProfile")
    consent_required: bool | None = Field(default=None, alias="consentRequired")
    google_auth_available: bool | None = Field(default=None, alias="googleAuthAvailable")
    telegram_auth_available: bool | None = Field(default=None, alias="telegramAuthAvailable")
    vk_auth_available: bool | None = Field(default=None, alias="vkAuthAvailable")
    yandex_auth_available: bool | None = Field(default=None, alias="yandexAuthAvailable")


class AnixPlayerConfigResponse(AnixartModel):
    last_version_code: int | None = None
    whats_new: str | None = None
    download_links: dict[str, str] = Field(default_factory=dict)


class ScheduleResponse(Response):
    monday: list[Release] = Field(default_factory=list)
    tuesday: list[Release] = Field(default_factory=list)
    wednesday: list[Release] = Field(default_factory=list)
    thursday: list[Release] = Field(default_factory=list)
    friday: list[Release] = Field(default_factory=list)
    saturday: list[Release] = Field(default_factory=list)
    sunday: list[Release] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Auth models (§6.2)
# ---------------------------------------------------------------------------


class ProfileToken(AnixartModel):
    id: int
    token: str = ""


class SignInResponse(Response):
    profile: Profile | None = None
    profile_token: ProfileToken | None = Field(default=None, alias="profileToken")


class CheckLoginResponse(Response):
    available: bool = False
    suggested_logins: list[str] = Field(default_factory=list)


class QrAuthResponse(Response):
    key: str | None = None
    secret: str | None = None
    pin: str | None = None
    expires_in: int | None = None
    poll_interval: int | None = None
    status: int | None = None
    device: str | None = None
    country_code: str | None = None
    attempts_left: int | None = None
    profile: Profile | None = None
    profile_token: ProfileToken | None = Field(default=None, alias="profileToken")


class SignUpResponse(Response):
    hash: str | None = None
    code_length: int | None = None
    code_time_left: int | None = None
    code_timestamp_expires: int | None = Field(default=None, alias="codeTimestampExpires")
    suggested_logins: list[str] = Field(default_factory=list)


class VerifyResponse(Response):
    profile: Profile | None = None
    profile_token: ProfileToken | None = Field(default=None, alias="profileToken")
    suggested_logins: list[str] = Field(default_factory=list)


class ResendResponse(Response):
    code_length: int | None = None
    code_time_left: int | None = None
    timestamp_expires: int | None = Field(default=None, alias="timestampExpires")


class RestoreResponse(Response):
    hash: str | None = None
    code_length: int | None = None
    code_time_left: int | None = None
    code_timestamp_expires: int | None = Field(default=None, alias="codeTimestampExpires")


class RestoreResendResponse(Response):
    code_length: int | None = None
    code_time_left: int | None = None
    timestamp_expires: int | None = Field(default=None, alias="timestampExpires")


class RestoreVerifyResponse(Response):
    profile: Profile | None = None
    profile_token: ProfileToken | None = Field(default=None, alias="profileToken")
    attempts_left: int | None = None


class ProviderAuthResponse(Response):
    """Shared shape for Google/VK/Telegram/Yandex sign-in and sign-up."""

    profile: Profile | None = None
    profile_token: ProfileToken | None = Field(default=None, alias="profileToken")
    hash: str | None = None
    code_length: int | None = None
    code_time_left: int | None = None
    code_timestamp_expires: int | None = Field(default=None, alias="codeTimestampExpires")
    suggested_logins: list[str] = Field(default_factory=list)
    email: str | None = None


class GoogleResponse(ProviderAuthResponse):
    pass


class VkResponse(ProviderAuthResponse):
    pass


class TelegramResponse(ProviderAuthResponse):
    pass


class YandexResponse(ProviderAuthResponse):
    pass


class FirebaseResponse(Response):
    topic_name: str | None = Field(
        default=None, validation_alias=AliasChoices("topicName", "topic_name")
    )


# ---------------------------------------------------------------------------
# Request bodies (§6.11)
# ---------------------------------------------------------------------------


class SearchRequest(AnixartModel):
    query: str = ""
    search_by: int = Field(default=0, alias="searchBy")


class FilterRequest(AnixartModel):
    category_id: int | None = None
    status_id: int | None = None
    types: list[int] | None = None
    genres: list[str] | None = None
    genres_mode: int | None = None
    is_genres_exclude_mode_enabled: bool | None = None
    profile_list_exclusions: list[int] | None = None
    age_ratings: list[int] | None = None
    start_year: int | None = None
    end_year: int | None = None
    episodes_from: int | None = None
    episodes_to: int | None = None
    episode_duration_from: int | None = None
    episode_duration_to: int | None = None
    country: str | None = None
    season: int | None = None
    source: str | None = None
    studio: str | None = None
    sort: int = 0


class ProfileEnforcementAppealRequest(AnixartModel):
    message: str


class ReleaseVideoAppealRequest(AnixartModel):
    release_id: int = Field(alias="releaseId")
    category_id: int = Field(alias="categoryId")
    title: str
    url: str


# Resolve forward references.  Pydantic v2 resolves most lazily, but explicit
# rebuilds keep failures visible at import time rather than on first request.
for _model in (
    Release,
    ReleaseVideo,
    ReleaseStreamingPlatform,
    Episode,
    ReleaseComment,
    Article,
    ArticleCompact,
    ScheduleResponse,
):
    _model.model_rebuild()

del _model


__all__ = [
    "AgeRating",
    "AnixPlayerConfigResponse",
    "AnixartModel",
    "Article",
    "ArticleCompact",
    "ArticlePayload",
    "Badge",
    "BadgeAward",
    "BadgeCategory",
    "BadgeSection",
    "Category",
    "Channel",
    "ChannelPermission",
    "ChannelProfile",
    "ChannelResponse",
    "CheckLoginResponse",
    "CommentAddRequest",
    "CommentAddResponse",
    "CommentBase",
    "CommentCompact",
    "CommentDeleteResponse",
    "CommentEditRequest",
    "CommentEditResponse",
    "CommentProcessRequest",
    "CommentWeek",
    "ConfigUrlsResponse",
    "DeleteVoteReleaseResponse",
    "Episode",
    "EpisodeCompact",
    "EpisodeResponse",
    "EpisodeTargetResponse",
    "EpisodeUnwatchResponse",
    "EpisodeUpdate",
    "EpisodeWatchResponse",
    "FavoritesResponse",
    "FeedSearchResponse",
    "FilterRequest",
    "FirebaseResponse",
    "FriendStatus",
    "Genre",
    "GenreMode",
    "GoogleResponse",
    "HistoryResponse",
    "Interesting",
    "LatestArticleResponse",
    "NotificationCountResponse",
    "NotificationPreferenceResponse",
    "PageableResponse",
    "PopularComment",
    "Profile",
    "ProfileBadgePageableResponse",
    "ProfileBadgeSectionsResponse",
    "ProfileCompact",
    "ProfileDeletionResponse",
    "ProfileEnforcement",
    "ProfileEnforcementAppealRequest",
    "ProfileEnforcementResponse",
    "ProfileGenre",
    "ProfileHealthStatusResponse",
    "ProfileInfoResponse",
    "ProfileListResponse",
    "ProfileListStatus",
    "ProfileNotification",
    "ProfilePreferenceResponse",
    "ProfileResponse",
    "ProfileRole",
    "ProfileRoleLevel",
    "ProfileSlim",
    "ProfileSocialResponse",
    "ProfileToken",
    "ProfileWatchDynamics",
    "ProviderAuthResponse",
    "QrAuthResponse",
    "Related",
    "Release",
    "ReleaseComment",
    "ReleaseCompact",
    "ReleaseResponse",
    "ReleaseSearchResponse",
    "ReleaseStatus",
    "ReleaseStreamingPlatform",
    "ReleaseType",
    "ReleaseVideo",
    "ReleaseVideoAppealRequest",
    "ReleaseVideoBanner",
    "ReleaseVideoBlock",
    "ReleaseVideoCategoriesResponse",
    "ReleaseVideoCategory",
    "ReleaseVideoHosting",
    "ReleaseVideosResponse",
    "ResendResponse",
    "Response",
    "RestoreResendResponse",
    "RestoreResponse",
    "RestoreVerifyResponse",
    "RoleDto",
    "ScheduleResponse",
    "SearchRequest",
    "SignInResponse",
    "SignUpResponse",
    "SortOrder",
    "Source",
    "SourcesResponse",
    "TelegramResponse",
    "TogglesResponse",
    "TypesResponse",
    "UnsupportedProfileNotification",
    "VerifyResponse",
    "VkResponse",
    "VoteReleaseResponse",
    "YandexResponse",
]
