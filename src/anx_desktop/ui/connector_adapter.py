"""Lazy bridge between the UI protocols and the clean-room API connector.

The connector (``anx_desktop.api``) is deliberately imported only when the
repository is created; importing this module must never require httpx/pydantic
or perform any network work.  Screens keep using the same ``Repository``
contract as before -- all wire-format translation lives here.

Known limitation (task 12 MVP): every repository method is synchronous and is
called from the UI thread by the existing screens.  Network calls can therefore
block the Qt event loop.  The next step is to move ``ConnectorRepository`` onto
a worker (``QThreadPool``/``QThread``) or make the screens await futures; that
is intentionally **not** done in this task so screen contracts stay untouched.

TODO(ui-thread): execute connector calls outside the UI thread and marshal the
mapped dataclasses back to Qt signals.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, ClassVar, TypeVar

from .data import (
    Article,
    ArticleDetails,
    Badge,
    Channel,
    ChannelDetails,
    Collection,
    CollectionDetails,
    Comment,
    DeletionData,
    DiscoverData,
    Episode,
    EpisodeSource,
    EpisodeType,
    FeedItem,
    HealthData,
    HistoryEntry,
    InterestingCard,
    NotificationItem,
    Page,
    Profile,
    ProfileCounters,
    ProfileData,
    ProfileStatsEntry,
    Release,
    ReleaseDetails,
    Repository,
    SearchResults,
    TabSpec,
)
from .strings import S

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_MISSING = object()


# ---------------------------------------------------------------------------
# Safe value helpers
# ---------------------------------------------------------------------------


def _value(source: Any, name: str, default: Any = None) -> Any:
    """Read a field from a pydantic model, dataclass or dict."""

    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value is _MISSING:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value is _MISSING:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "."))
        except ValueError:
            return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_text(value: Any, default: str = "") -> str:
    if value is None or value is _MISSING:
        return default
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    for attr in ("name", "title", "value"):
        candidate = getattr(value, attr, None)
        if isinstance(candidate, str):
            return candidate
    return default


def _as_seq(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    if isinstance(value, (str, bytes, Mapping)):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return ()


def _year(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    match = re.search(r"\d{4}", _as_text(value, ""))
    return int(match.group(0)) if match else 0


def _genres(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        parts: Sequence[Any] = value.split(",")
    else:
        parts = _as_seq(value)
    return tuple(text for part in parts if (text := _as_text(part).strip()))


def _status_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _as_text(_value(value, "name", None))


def _category_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _as_text(_value(value, "name", None))


_AGE_RATINGS = {1: "0+", 2: "6+", 3: "12+", 4: "16+", 5: "18+"}


def _age_rating(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return _AGE_RATINGS.get(value, "")
    if isinstance(value, float) and value.is_integer():
        return _AGE_RATINGS.get(int(value), "")
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return _AGE_RATINGS.get(int(text), text)
        return text
    for key in ("name", "title", "value"):
        text = _as_text(_value(value, key, None))
        if text:
            return text
    return ""


def _model_error_name(exc: Exception) -> str:
    # Never stringify connector exceptions here: their bodies can (in the
    # worst case) contain a session token.  The class name is enough context.
    return type(exc).__name__


# ---------------------------------------------------------------------------
# Public connector discovery / factory
# ---------------------------------------------------------------------------


def connector_module() -> Any | None:
    """Return the connector module only if it can be imported, else None."""

    try:
        return importlib.import_module("anx_desktop.api")
    except Exception:
        return None


def connector_available() -> bool:
    try:
        return connector_module() is not None
    except Exception:
        return False


def create_repository(*, token_store=None) -> ConnectorRepository:
    """Create the live repository, or raise if the connector cannot start."""

    try:
        module = connector_module()
        client_type = getattr(module, "AnixartClient", None)
        if not callable(client_type):
            raise RuntimeError("API client is unavailable")
        token = (os.environ.get("ANIXART_TOKEN") or "").strip()
        profile_id_raw = (os.environ.get("ANIXART_PROFILE_ID") or "").strip()
        client = client_type(token_store=token_store) if token_store is not None and not token else client_type()
        if token:
            profile_id = int(profile_id_raw) if profile_id_raw.isdecimal() else None
            if profile_id is None:
                client.set_token(token)
            else:
                client.set_token(token, profile_id=profile_id)
        return ConnectorRepository(client)
    except Exception as exc:
        raise RuntimeError("Could not initialise the live API repository") from exc


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ConnectorRepository(Repository):
    """``Repository`` backed by :class:`anx_desktop.api.AnixartClient`.

    The class is duck-typed on purpose: tests can pass a small fake client and
    the connector itself is imported lazily by :func:`create_repository`.

    Unavailable lists return empty results. Required detail objects are never
    fabricated when the API cannot supply them.
    """

    def __init__(self, client: Any) -> None:
        if not hasattr(client, "search") and callable(getattr(client, "AnixartClient", None)):
            client = client.AnixartClient()
        self._client = client
        self._search_history: list[str] = []
        self._episode_types_cache: dict[int, tuple[EpisodeType, ...]] = {}
        self._episode_sources_cache: dict[
            tuple[int, int], tuple[EpisodeSource, ...]
        ] = {}
        self._episodes_cache: dict[
            tuple[int, int, int], tuple[Episode, ...]
        ] = {}

    # -- diagnostics -------------------------------------------------------
    def _log_failure(self, operation: str, context: str, exc: Exception) -> None:
        logger.warning(
            "UI connector fallback: %s%s failed with %s",
            operation,
            f" ({context})" if context else "",
            _model_error_name(exc),
        )

    @property
    def is_authenticated(self) -> bool:
        return self._client.is_authenticated

    def login(self, login: str, password: str) -> Any:
        return self._client.auth.login(login, password)

    def logout(self) -> None:
        self._client.auth.logout()

    def _session_profile_id(self) -> int | None:
        try:
            session = getattr(self._client, "session", None)
        except Exception:
            return None
        profile_id = _as_int(_value(session, "profile_id", 0), 0)
        return profile_id or None

    # -- model mapping -----------------------------------------------------
    def _release_from_api(self, raw: Any) -> Release:
        status = _status_name(_value(raw, "status", None))
        category = _category_name(_value(raw, "category", None))
        release_id = _as_int(_value(raw, "id", 0), 0)
        title = (
            _as_text(_value(raw, "title_ru", None))
            or _as_text(_value(raw, "title", None))
            or _as_text(_value(raw, "title_original", None))
            or _as_text(_value(raw, "title_alt", None))
        )
        original_title = (
            _as_text(_value(raw, "title_original", None))
            or _as_text(_value(raw, "original_title", None))
            or _as_text(_value(raw, "title_alt", None))
        )
        votes = (
            _as_int(_value(raw, "vote_1_count", 0), 0),
            _as_int(_value(raw, "vote_2_count", 0), 0),
            _as_int(_value(raw, "vote_3_count", 0), 0),
            _as_int(_value(raw, "vote_4_count", 0), 0),
            _as_int(_value(raw, "vote_5_count", 0), 0),
        )
        category_key = category.casefold()
        is_movie = "фильм" in category_key or "movie" in category_key
        return Release(
            id=release_id,
            title=title,
            original_title=original_title,
            year=_year(_value(raw, "year", None)),
            grade=_as_float(_value(raw, "grade", 0.0)),
            episodes_total=_as_int(_value(raw, "episodes_total", 0), 0),
            episodes_released=_as_int(_value(raw, "episodes_released", 0), 0),
            description=_as_text(_value(raw, "description", None)),
            country=_as_text(_value(raw, "country", None)),
            studio=_as_text(_value(raw, "studio", None)),
            source=_as_text(_value(raw, "source", None)),
            genres=_genres(_value(raw, "genres", None)),
            status=status,
            age_rating=_age_rating(_value(raw, "age_rating", None)),
            is_adult=bool(_value(raw, "is_adult", False)),
            is_favorite=bool(_value(raw, "is_favorite", False)),
            seed=release_id,
            image_url=_as_text(_value(raw, "image", None))
            or _as_text(_value(raw, "poster", None)),
            screenshots=tuple(
                text
                for item in _as_seq(_value(raw, "screenshot_images", ()))
                if (text := _as_text(item, ""))
            ),
            list_status=_as_int(_value(raw, "profile_list_status", 0), 0),
            vote_count=_as_int(_value(raw, "vote_count", 0), 0),
            votes=votes,
            duration_minutes=_as_int(_value(raw, "duration", 0), 0),
            schedule=_as_text(_value(raw, "schedule", None)),
            is_movie=is_movie,
        )

    def _badge_from_api(self, raw: Any) -> Badge:
        award = _value(raw, "award", None)
        category = _value(raw, "category", None)
        return Badge(
            id=_as_int(_value(raw, "id", 0), 0),
            name=_as_text(_value(raw, "name", None)),
            description=_as_text(_value(raw, "description", None)),
            rarity=_as_text(_value(raw, "rarity", None)),
            is_owned=bool(_value(raw, "is_owned", False)),
            is_selected=bool(_value(raw, "is_selected", False)),
            is_showcased=bool(_value(raw, "is_showcased", False)),
            ownership_percent=_as_int(_value(raw, "ownership_percentage", 0), 0),
            award=_as_text(_value(award, "trigger", None)),
            category=_as_text(_value(category, "title", None)),
        )

    def _comment_from_api(self, raw: Any) -> Comment:
        profile = _value(raw, "profile", None)
        author = _as_text(_value(profile, "login", None))
        votes = _value(raw, "vote_count", None)
        if votes is None:
            votes = _value(raw, "likes_count", None)
        return Comment(
            id=_as_int(_value(raw, "id", 0), 0),
            author=author,
            text=_as_text(_value(raw, "message", None)),
            timestamp=_as_float(_value(raw, "timestamp", 0.0)),
            votes=_as_int(votes, 0),
            is_spoiler=bool(_value(raw, "is_spoiler", False)),
            is_deleted=bool(_value(raw, "is_deleted", False)),
            is_edited=bool(_value(raw, "is_edited", False)),
            is_verified=bool(_value(profile, "is_verified", False)),
            replies=_as_int(_value(raw, "reply_count", 0), 0),
            user_vote=_as_int(_value(raw, "vote", 0), 0),
        )

    def _episode_from_api(self, raw: Any) -> Episode:
        source = _value(raw, "source", None)
        source_type = _value(source, "type", None)
        return Episode(
            id=_as_int(_value(raw, "id", 0), 0),
            number=_as_int(_value(raw, "position", 0), 0),
            title=_as_text(_value(raw, "name", None)),
            duration_seconds=_as_int(_value(raw, "playback_duration", 0), 0),
            watched=bool(_value(raw, "is_watched", False)),
            filler=bool(_value(raw, "is_filler", False)),
            type_name=_as_text(_value(source_type, "name", None)),
            source_name=_as_text(_value(source, "name", None)),
            added_ts=_as_float(_value(raw, "added_date", 0)),
            stream_url=_as_text(_value(raw, "url", None)),
            iframe=bool(_value(raw, "iframe", False)),
        )

    def _episode_source_from_api(
        self, raw: Any, type_id: int = 0, is_sub: bool = False
    ) -> EpisodeSource:
        source_type = _value(raw, "type", None)
        return EpisodeSource(
            id=_as_int(_value(raw, "id", 0), 0),
            name=_as_text(_value(raw, "name", None)),
            kind=_as_text(_value(source_type, "name", None)),
            episodes_count=_as_int(_value(raw, "episodes_count", 0), 0),
            type_id=type_id,
            is_sub=is_sub,
        )

    def _channel_from_api(self, raw: Any) -> Channel:
        channel_id = _as_int(_value(raw, "id", 0), 0)
        permission = _value(raw, "permission", None)
        return Channel(
            id=channel_id,
            title=_as_text(_value(raw, "title", None)),
            description=_as_text(_value(raw, "description", None)),
            subscriber_count=_as_int(_value(raw, "subscriber_count", 0), 0),
            is_subscribed=bool(_value(raw, "is_subscribed", False)),
            is_verified=bool(_value(raw, "is_verified", False)),
            is_blog=bool(_value(raw, "is_blog", False)),
            is_muted=bool(_value(raw, "is_muted", False)),
            article_count=_as_int(_value(raw, "article_count", 0), 0),
            seed=channel_id,
            is_creator=bool(_value(raw, "is_creator", False)),
            permission=_as_text(permission, ""),
        )

    def _article_from_api(self, raw: Any) -> Article:
        channel = _value(raw, "channel", None)
        author = _value(raw, "author", None)
        channel_id = _as_int(_value(channel, "id", 0), 0)
        # ``Article`` has no title field in the documented payload and the
        # ArticleBlock wire schema is UNKNOWN (docs/api.md §6.8, U-19), so the
        # card gets safe empty values instead of a guessed title/body.
        return Article(
            id=_as_int(_value(raw, "id", 0), 0),
            channel_id=channel_id,
            channel_title=_as_text(_value(channel, "title", None)),
            title="",
            author=_as_text(_value(author, "login", None)),
            created_ts=_as_float(
                _value(raw, "creation_date", _value(raw, "last_update_date", 0))
            ),
            blocks=(),
            votes=_as_int(_value(raw, "vote_count", 0), 0),
            comments_count=_as_int(_value(raw, "comment_count", 0), 0),
            reposts=_as_int(_value(raw, "repost_count", 0), 0),
            is_pinned=bool(_value(raw, "is_pinned", False)),
            is_muted=bool(_value(raw, "is_muted", False)),
            is_deleted=bool(_value(raw, "is_deleted", False)),
            is_verified=bool(_value(channel, "is_verified", False)),
            is_signed=bool(_value(raw, "is_signed", False)),
            channel_seed=channel_id,
        )

    def _interesting_from_api(self, raw: Any) -> InterestingCard:
        card_id = _as_int(_value(raw, "id", 0), 0)
        return InterestingCard(
            id=card_id,
            title=_as_text(_value(raw, "title", None)),
            description=_as_text(_value(raw, "description", None)),
            seed=card_id,
            image_url=_as_text(_value(raw, "image", None))
            or _as_text(_value(raw, "poster", None)),
        )

    def _history_entry_from_api(self, raw: Any) -> HistoryEntry:
        last_episode = _value(raw, "last_view_episode", None)
        source = _value(last_episode, "source", None)
        episode_name = (
            _as_text(_value(raw, "last_view_episode_name", None))
            or _as_text(_value(last_episode, "name", None))
        )
        return HistoryEntry(
            release=self._release_from_api(raw),
            episode_name=episode_name,
            source_name=_as_text(_value(source, "name", None)),
            watch_ts=_as_float(_value(raw, "last_view_timestamp", 0)),
        )

    def _notification_from_api(self, raw: Any) -> NotificationItem:
        episode = _value(raw, "episode", None)
        article = _value(raw, "article", None)
        comment = _value(raw, "comment", None)
        release = _value(raw, "release", None)
        by_profile = _value(raw, "by_profile", None)

        kind = "unknown"
        if comment is not None:
            kind = "reply"
        elif episode is not None:
            kind = "episode"
        elif article is not None:
            kind = "article"
        elif _value(raw, "status", None) is not None:
            kind = "friend"
        elif release is not None:
            kind = "release"

        target_kind = "release"
        target_id = 0
        title = ""
        message = ""
        spoiler = False

        if kind == "episode":
            title = S.NOTIFICATIONS_NEW_EPISODE
            release_title = _as_text(_value(_value(episode, "release", None), "title_ru", None))
            episode_name = _as_text(_value(episode, "name", None))
            message = " · ".join(part for part in (release_title, episode_name) if part)
            target_id = _as_int(_value(_value(episode, "release", None), "id", 0), 0)
        elif kind == "article":
            title = S.NOTIFICATIONS_NEW_ARTICLE
            channel = _value(article, "channel", None)
            message = _as_text(_value(channel, "title", None))
            target_kind = "article"
            target_id = _as_int(_value(article, "id", 0), 0)
        elif kind == "reply":
            title = S.NOTIFICATIONS_REPLY
            message = _as_text(_value(comment, "message", None))
            spoiler = bool(_value(comment, "is_spoiler", False))
            target_kind = "profile"
            target_id = _as_int(_value(by_profile, "id", 0), 0)
        elif kind == "friend":
            title = S.NOTIFICATIONS_FRIEND
            message = _as_text(_value(by_profile, "login", None))
            target_kind = "profile"
            target_id = _as_int(_value(by_profile, "id", 0), 0)
        elif kind == "release":
            title = S.RELEASE_SCREEN_TITLE
            message = _as_text(_value(release, "title_ru", None))
            target_id = _as_int(_value(release, "id", 0), 0)

        return NotificationItem(
            id=_as_int(_value(raw, "id", 0), 0),
            kind=kind,
            title=title,
            message=message,
            timestamp=_as_float(_value(raw, "timestamp", 0)),
            is_new=bool(_value(raw, "is_new", False)),
            spoiler=spoiler,
            target_kind=target_kind,
            target_id=target_id,
        )

    def _profile_data_from_api(self, raw: Any, info: Any = None) -> ProfileData:
        profile_id = _as_int(_value(raw, "id", 0), 0)
        counters = ProfileCounters(
            watching=_as_int(_value(raw, "watching_count", 0), 0),
            planned=_as_int(_value(raw, "plan_count", 0), 0),
            completed=_as_int(_value(raw, "completed_count", 0), 0),
            on_hold=_as_int(_value(raw, "hold_on_count", 0), 0),
            dropped=_as_int(_value(raw, "dropped_count", 0), 0),
            favorites=_as_int(_value(raw, "favorite_count", 0), 0),
        )
        roles = tuple(
            role_name
            for role in _as_seq(_value(raw, "roles", ()))
            if (role_name := _as_text(_value(role, "name", None)))
        )
        rating = _as_float(_value(raw, "rating_score", None))
        if rating == 0.0:
            rating = _as_float(_value(info, "rating_score", 0.0))
        is_sponsor = bool(_value(raw, "is_sponsor", False)) or bool(
            _value(info, "is_sponsor", False)
        )

        stats = tuple(
            ProfileStatsEntry(label=label, count=count, color_role=role)
            for label, count, role in (
                (S.BOOKMARK_TABS[3], counters.watching, "status_watching"),
                (S.BOOKMARK_TABS[4], counters.planned, "status_planned"),
                (S.BOOKMARK_TABS[5], counters.completed, "status_completed"),
                (S.BOOKMARK_TABS[6], counters.on_hold, "status_on_hold"),
                (S.BOOKMARK_TABS[7], counters.dropped, "status_dropped"),
            )
        )

        votes = tuple(
            release
            for item in _as_seq(_value(raw, "votes", ()))
            if _value(item, "id", None) is not None
            and (release := self._release_from_api(item)) is not None
        )
        history = tuple(
            release
            for item in _as_seq(_value(raw, "history", ()))
            if _value(item, "id", None) is not None
            and (release := self._release_from_api(item)) is not None
        )
        dynamics = tuple(
            _as_int(_value(item, "count", 0), 0)
            for item in _as_seq(_value(raw, "watch_dynamics", ()))
        )
        badges = tuple(
            self._badge_from_api(item)
            for item in _as_seq(_value(raw, "badges_preview", ()))
        )
        genres = tuple(
            genre_name
            for genre in _as_seq(_value(raw, "preferred_genres", ()))
            if (genre_name := _as_text(_value(genre, "name", None)))
        )

        profile = Profile(
            id=profile_id,
            nick=_as_text(_value(raw, "login", None)) or f"id{profile_id}",
            status=_as_text(_value(raw, "status", None)),
            is_verified=bool(_value(raw, "is_verified", False)),
            is_sponsor=is_sponsor,
            is_online=bool(_value(raw, "is_online", False)),
            registered_ts=_as_float(
                _value(raw, "register_date", _value(raw, "added_date", 0))
            ),
            rating=rating,
            roles=roles,
            counters=counters,
            watched_episodes=_as_int(_value(raw, "watched_episode_count", 0), 0),
            watched_minutes=_as_int(_value(raw, "watched_time", 0), 0),
            comments=_as_int(_value(raw, "comment_count", 0), 0),
            videos=_as_int(_value(raw, "video_count", 0), 0),
            collections=_as_int(_value(raw, "collection_count", 0), 0),
            friends_count=_as_int(_value(raw, "friend_count", 0), 0),
            pinned_section="Статистика",
            is_hidden=bool(_value(raw, "is_stats_hidden", False))
            or bool(_value(raw, "is_counts_hidden", False)),
            is_incognito=bool(_value(raw, "is_incognito", False)),
        )
        return ProfileData(
            profile=profile,
            stats=stats,
            votes=votes,
            history=history,
            dynamics=dynamics,
            badges=badges,
            collections=(),
            comments=(),
            genres=genres,
        )

    # -- page mapping ------------------------------------------------------
    def _map_page(
        self,
        response: Any,
        page: int,
        page_size: int,
        mapper: Callable[[Any], _T],
    ) -> Page[_T]:
        requested_size = max(1, _as_int(page_size, 1))
        requested_page = max(1, _as_int(page, 1))
        items: list[_T] = []
        for raw in _as_seq(_value(response, "content", ())):
            if raw is None:
                continue
            try:
                items.append(mapper(raw))
            except Exception as exc:
                logger.debug("skipping unmappable connector item (%s)", _model_error_name(exc))
        return Page(
            items=tuple(items),
            page=_as_int(_value(response, "current_page", requested_page), requested_page),
            page_size=requested_size,
            total_count=_as_int(_value(response, "total_count", 0), 0),
            total_pages=_as_int(_value(response, "total_page_count", 0), 0),
        )

    def _empty_page(self, page: int, page_size: int) -> Page[_T]:
        return Page(
            items=(),
            page=max(1, _as_int(page, 1)),
            page_size=max(1, _as_int(page_size, 1)),
            total_count=0,
            total_pages=0,
        )

    # -- tabs (local UI contract; unchanged) -------------------------------
    def home_tabs(self) -> Sequence[TabSpec]:
        return tuple(
            TabSpec(title=title, key=f"home_{index}", subtitle=S.HOME_TAB_SUBTITLES[index])
            for index, title in enumerate(S.HOME_TABS)
        )

    def bookmark_tabs(self) -> Sequence[TabSpec]:
        return tuple(
            TabSpec(title=title, key=f"bookmark_{index}")
            for index, title in enumerate(S.BOOKMARK_TABS)
        )

    def feed_tabs(self) -> Sequence[TabSpec]:
        return tuple(
            TabSpec(title=title, key=f"feed_{index}")
            for index, title in enumerate(S.FEED_TABS)
        )

    # -- home --------------------------------------------------------------
    def _filter_request(self, **values: Any) -> Any:
        api = importlib.import_module("anx_desktop.api")
        return api.FilterRequest(**values)

    def _home_filter(self, **overrides: Any) -> Any:
        """Build the filter body used by the Android home tabs.

        The real client sends empty arrays and ``false`` explicitly; keeping
        the same shape avoids server-side differences for extended fields.
        Status/type ids below are taken from the verified tab requests
        (status 1/2/3 = ongoing/announcement/completed, category 2/3 =
        movies/OVA).
        """

        values: dict[str, Any] = {
            "sort": self._sort_order("DATE_UPDATE_DESC", 0),
            "types": [],
            "genres": [],
            "age_ratings": [],
            "profile_list_exclusions": [],
            "is_genres_exclude_mode_enabled": False,
        }
        values.update(overrides)
        return self._filter_request(**values)

    def fetch_home(self, tab_key: str, page: int, page_size: int) -> Page[Release]:
        try:
            if tab_key == "home_0":
                if self.is_authenticated:
                    response = self._client.feed.get_recommendations(page)
                    if not _as_seq(_value(response, "content", ())):
                        response = self._client.search.filter_releases(
                            page,
                            self._home_filter(
                                sort=self._sort_order("POPULAR_DESC", 3)
                            ),
                            extended_mode=True,
                        )
                else:
                    response = self._client.search.filter_releases(
                        page,
                        self._home_filter(
                            sort=self._sort_order("POPULAR_DESC", 3)
                        ),
                        extended_mode=True,
                    )
            elif tab_key == "home_1":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(country="Япония"),
                    extended_mode=True,
                )
            elif tab_key == "home_2":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(country="Китай"),
                    extended_mode=True,
                )
            elif tab_key == "home_3":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(),
                    extended_mode=True,
                )
            elif tab_key == "home_4":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(status_id=1),
                    extended_mode=True,
                )
            elif tab_key == "home_5":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(status_id=2),
                    extended_mode=True,
                )
            elif tab_key == "home_6":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(status_id=3),
                    extended_mode=True,
                )
            elif tab_key == "home_7":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(category_id=2),
                    extended_mode=True,
                )
            elif tab_key == "home_8":
                response = self._client.search.filter_releases(
                    page,
                    self._home_filter(category_id=3),
                    extended_mode=True,
                )
            else:
                return self._empty_page(page, page_size)
            return self._map_page(response, page, page_size, self._release_from_api)
        except Exception as exc:
            self._log_failure("fetch_home", tab_key, exc)
            return self._empty_page(page, page_size)

    @staticmethod
    def _sort_order(name: str, fallback: int) -> Any:
        try:
            api = importlib.import_module("anx_desktop.api")
            return getattr(api.SortOrder, name)
        except Exception:
            return fallback

    # -- search ------------------------------------------------------------
    def fetch_search(self, query: str) -> SearchResults:
        stripped = query.strip()
        if not stripped:
            return SearchResults(
                query=query, releases=(), articles=(), channels=(), profiles=(), collections=()
            )
        try:
            response = self._client.search.search_releases(1, stripped)
            releases = tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(response, "releases", ()))
            )
            return SearchResults(
                query=query,
                releases=releases,
                articles=(),
                channels=(),
                profiles=(),
                collections=(),
            )
        except Exception as exc:
            self._log_failure("fetch_search", "", exc)
            return SearchResults(
                query=query, releases=(), articles=(), channels=(), profiles=(), collections=()
            )

    def search_history(self) -> list[str]:
        return list(self._search_history)

    def clear_search_history(self) -> None:
        self._search_history.clear()

    def remember_search(self, query: str) -> None:
        query = query.strip()
        if query and query not in self._search_history:
            self._search_history.insert(0, query)
            del self._search_history[8:]

    # -- release -----------------------------------------------------------
    def _release_comments(self, release_id: int) -> tuple[Comment, ...]:
        try:
            response = self._client.comments.get_comments(release_id, 1)
            return tuple(self._comment_from_api(item) for item in _as_seq(_value(response, "content", ())))
        except Exception as exc:
            self._log_failure("fetch_release.comments", str(release_id), exc)
            return ()

    def _release_badges(self, release_id: int) -> tuple[Badge, ...]:
        try:
            response = self._client.releases.get_badges(release_id, 1)
            return tuple(self._badge_from_api(item) for item in _as_seq(_value(response, "content", ())))
        except Exception as exc:
            self._log_failure("fetch_release.badges", str(release_id), exc)
            return ()

    def _release_related(self, raw_release: Any, release_id: int) -> tuple[Release, ...]:
        direct = _as_seq(_value(raw_release, "related_releases", ()))
        if direct:
            return tuple(self._release_from_api(item) for item in direct)
        related = _value(raw_release, "related", None)
        related_id = _as_int(_value(related, "id", 0), 0)
        if not related_id:
            return ()
        try:
            response = self._client.releases.get_related(related_id, 1)
            return tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_release.related", str(release_id), exc)
            return ()

    def fetch_release(self, release_id: int) -> ReleaseDetails:
        try:
            response = self._client.releases.get_release(release_id)
            raw = _value(response, "release", None)
            if raw is None:
                raise ValueError("release payload is missing")
            release = self._release_from_api(raw)
            recommended = tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(raw, "recommended_releases", ()))
            )
            screenshots = len(_as_seq(_value(raw, "screenshot_images", ())))
            user_vote_raw = _value(raw, "your_vote", _value(raw, "my_vote", None))
            user_vote = None if user_vote_raw is None else _as_float(user_vote_raw)
            return ReleaseDetails(
                release=release,
                screenshots=screenshots,
                badges=self._release_badges(release_id),
                collections=(),
                related=self._release_related(raw, release_id),
                recommended=recommended,
                comments=self._release_comments(release_id),
                user_vote=user_vote,
            )
        except Exception as exc:
            self._log_failure("fetch_release", str(release_id), exc)
            raise RuntimeError("Could not load release") from exc

    # -- episodes ----------------------------------------------------------
    def episode_types(self, release_id: int) -> tuple[EpisodeType, ...]:
        if release_id in self._episode_types_cache:
            return self._episode_types_cache[release_id]
        types: tuple[EpisodeType, ...] = ()
        try:
            response = self._client.episodes.get_types(release_id)
            types = tuple(
                EpisodeType(
                    id=type_id,
                    name=_as_text(_value(item, "name", None)),
                    is_sub=bool(_value(item, "is_sub", False)),
                )
                for item in _as_seq(_value(response, "types", ()))
                if (type_id := _as_int(_value(item, "id", 0), 0))
            )
        except Exception as exc:
            self._log_failure("episode_types", str(release_id), exc)
        self._episode_types_cache[release_id] = types
        return types

    def _resolve_type_id(self, release_id: int, type_id: int | None) -> int | None:
        if type_id is not None:
            return type_id
        types = self.episode_types(release_id)
        return types[0].id if types else None

    def fetch_episodes(
        self,
        release_id: int,
        *,
        type_id: int | None = None,
        source_id: int | None = None,
    ) -> tuple[Episode, ...]:
        resolved_type = self._resolve_type_id(release_id, type_id)
        if resolved_type is None:
            return ()
        if source_id is None:
            sources = self.episode_sources(release_id, resolved_type)
            source_id = sources[0].id if sources else None
        if source_id is None:
            return ()
        key = (release_id, resolved_type, source_id)
        if key in self._episodes_cache:
            return self._episodes_cache[key]
        try:
            response = self._client.episodes.get_episodes(
                release_id, resolved_type, source_id
            )
            episodes = tuple(
                self._episode_from_api(item)
                for item in _as_seq(_value(response, "episodes", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_episodes", str(release_id), exc)
            return ()
        self._episodes_cache[key] = episodes
        return episodes

    def episode_sources(
        self, release_id: int, type_id: int | None = None
    ) -> tuple[EpisodeSource, ...]:
        resolved_type = self._resolve_type_id(release_id, type_id)
        if resolved_type is None:
            return ()
        key = (release_id, resolved_type)
        if key in self._episode_sources_cache:
            return self._episode_sources_cache[key]
        try:
            response = self._client.episodes.get_sources(release_id, resolved_type)
            type_info = next(
                (item for item in self.episode_types(release_id) if item.id == resolved_type),
                None,
            )
            sources = tuple(
                self._episode_source_from_api(
                    item,
                    resolved_type,
                    bool(type_info.is_sub) if type_info is not None else False,
                )
                for item in _as_seq(_value(response, "sources", ()))
            )
        except Exception as exc:
            self._log_failure("episode_sources", str(release_id), exc)
            return ()
        self._episode_sources_cache[key] = sources
        return sources

    # -- comments / related ------------------------------------------------
    def fetch_comments(self, target_kind: str, target_id: int) -> tuple[Comment, ...]:
        if target_kind not in {"release", ""}:
            return ()
        try:
            response = self._client.comments.get_comments(target_id, 1)
            return tuple(
                self._comment_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_comments", target_kind, exc)
            return ()

    def fetch_related(self, kind: str, release_id: int = 0) -> tuple[Release, ...]:
        try:
            if kind == "related" and release_id:
                response = self._client.releases.get_related(release_id, 1)
            elif kind == "recommended":
                response = self._client.feed.get_recommendations(1)
            elif kind == "watching":
                response = self._client.feed.get_watching(1)
            else:
                return ()
            return tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_related", kind, exc)
            return ()

    # -- profile -----------------------------------------------------------
    def fetch_profile(self, profile_id: int | None = None) -> ProfileData:
        if not self.is_authenticated:
            raise RuntimeError("Authentication is required to load the profile")
        info = None
        try:
            if profile_id is None:
                info = self._client.profile.get_info()
                profile_id = self._session_profile_id()
                if profile_id is None:
                    info_profile = _value(info, "profile", None)
                    if info_profile is not None:
                        return self._profile_data_from_api(info_profile, info)
            if profile_id is None:
                raise ValueError("profile payload is missing")
            response = self._client.profile.get_profile(profile_id)
            raw = _value(response, "profile", None)
            if raw is None:
                raise ValueError("profile payload is missing")
            return self._profile_data_from_api(raw, info)
        except Exception as exc:
            self._log_failure("fetch_profile", "" if profile_id is None else str(profile_id), exc)
            raise RuntimeError("Could not load profile") from exc

    # -- notifications -----------------------------------------------------
    _NOTIFICATION_KINDS: ClassVar[dict[str, frozenset[str]]] = {
        "episodes": frozenset({"episode"}),
        "releases": frozenset({"release"}),
        "articles": frozenset({"article"}),
        "friends": frozenset({"friend"}),
        "replies": frozenset({"reply"}),
    }

    def fetch_notifications(self, filter_key: str) -> tuple[NotificationItem, ...]:
        if not self.is_authenticated:
            return ()
        try:
            response = self._client.notifications.get_all(1)
            items = tuple(
                self._notification_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
            kinds = self._NOTIFICATION_KINDS.get(filter_key)
            if kinds is None:
                return items
            return tuple(item for item in items if item.kind in kinds)
        except Exception as exc:
            self._log_failure("fetch_notifications", filter_key, exc)
            return ()

    # -- bookmarks / history ----------------------------------------------
    def fetch_history(self, page: int, page_size: int) -> Page[HistoryEntry]:
        if not self.is_authenticated:
            return self._empty_page(page, page_size)
        try:
            response = self._client.history.get_history(page)
            return self._map_page(response, page, page_size, self._history_entry_from_api)
        except Exception as exc:
            self._log_failure("fetch_history", "", exc)
            return self._empty_page(page, page_size)

    def _profile_list_status(self, index: int) -> Any:
        names = {3: "WATCHING", 4: "PLAN", 5: "COMPLETED", 6: "HOLD_ON", 7: "DROPPED"}
        fallback = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5}
        try:
            api = importlib.import_module("anx_desktop.api")
            return getattr(api.ProfileListStatus, names[index])
        except Exception:
            return fallback[index]

    def fetch_bookmarks(self, tab_key: str, page: int, page_size: int) -> Page[Release]:
        if not self.is_authenticated:
            return self._empty_page(page, page_size)
        try:
            tail = tab_key.rsplit("_", 1)[-1]
            index = int(tail) if tail.isdigit() else 0
            if index == 0:
                # Collections are not exposed by the connector yet.
                return self._empty_page(page, page_size)
            if index == 1:
                response = self._client.history.get_history(page)
            elif index == 2:
                response = self._client.releases.get_favorites(page)
            elif index in {3, 4, 5, 6, 7}:
                response = self._client.profile.get_list(
                    self._profile_list_status(index), page
                )
            else:
                return self._empty_page(page, page_size)
            return self._map_page(response, page, page_size, self._release_from_api)
        except Exception as exc:
            self._log_failure("fetch_bookmarks", tab_key, exc)
            return self._empty_page(page, page_size)

    # -- feed / discover ---------------------------------------------------
    def fetch_feed(self, tab_key: str, page: int, page_size: int) -> Page[FeedItem]:
        try:
            response = self._client.feed.get_feed(page)

            def mapper(raw: Any) -> FeedItem:
                article = self._article_from_api(raw)
                channel = self._channel_from_api(_value(raw, "channel", None))
                return FeedItem(article=article, channel=channel)

            return self._map_page(response, page, page_size, mapper)
        except Exception as exc:
            self._log_failure("fetch_feed", tab_key, exc)
            return self._empty_page(page, page_size)

    def fetch_discover(self) -> DiscoverData:
        trending: tuple[InterestingCard, ...] = ()
        recommendations: tuple[Release, ...] = ()
        watching_now: tuple[Release, ...] = ()
        comments_week: tuple[Comment, ...] = ()

        try:
            response = self._client.feed.get_interesting()
            trending = tuple(
                self._interesting_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_discover.interesting", "", exc)

        try:
            response = self._client.feed.get_recommendations(1)
            recommendations = tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_discover.recommendations", "", exc)

        try:
            response = self._client.feed.get_discussing()
            # ``get_discussing`` returns releases, while the UI section is a
            # list of articles (``DiscoverData.discussed``).  The models do not
            # match, so the call is kept for parity but the section stays empty.
            _ = _as_seq(_value(response, "content", ()))
        except Exception as exc:
            self._log_failure("fetch_discover.discussing", "", exc)

        try:
            response = self._client.feed.get_watching(1)
            watching_now = tuple(
                self._release_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_discover.watching", "", exc)

        try:
            response = self._client.feed.get_comments_week()
            comments_week = tuple(
                self._comment_from_api(item)
                for item in _as_seq(_value(response, "content", ()))
            )
        except Exception as exc:
            self._log_failure("fetch_discover.comments", "", exc)

        return DiscoverData(
            trending=trending,
            quick_links=(),
            recommendations=recommendations,
            discussed=(),
            watching_now=watching_now,
            # Collections are not exposed by the connector yet.
            collections_week=(),
            comments_week=comments_week,
            social_links=(),
            sponsorship_text="",
        )

    # -- unsupported domains ----------------------------------------------
    def fetch_collections(self, query: str = "", sort_key: str = "popular") -> tuple[Collection, ...]:
        return ()

    def fetch_collection(self, collection_id: int) -> CollectionDetails:
        raise RuntimeError("Collection details are unavailable")

    def fetch_channels(self, query: str = "", subscribed_only: bool = False) -> tuple[Channel, ...]:
        return ()

    def fetch_channel(self, channel_id: int) -> ChannelDetails:
        raise RuntimeError("Channel details are unavailable")

    def fetch_articles(self, channel_id: int | None = None) -> tuple[Article, ...]:
        return ()

    def fetch_article(self, article_id: int) -> ArticleDetails:
        raise RuntimeError("Article details are unavailable")

    def fetch_badges(self, owner_kind: str = "profile", owner_id: int = 0) -> tuple[Badge, ...]:
        return ()

    def fetch_health(self) -> HealthData:
        raise RuntimeError("Account health is unavailable")

    def fetch_deletion(self) -> DeletionData:
        raise RuntimeError("Account deletion status is unavailable")

    def fetch_schedule(self) -> dict[str, tuple[Release, ...]]:
        return {}
