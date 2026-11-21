"""UI-side data contracts and a deterministic demo repository.

The real connector (`anx_desktop.api`) is written in parallel and is *not*
imported here at module import time.  Screens depend only on the protocols
below; `connector_adapter.py` contains the lazy bridge stub.

Field names in the dataclasses mirror the models documented in `docs/api.md`
(`title_ru`, `grade`, `is_favorite`, `status`, `episode` fields, etc.) while
keeping the UI free of wire-format concerns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Generic, Iterable, Protocol, Sequence, TypeVar

T = TypeVar("T")


# --------------------------------------------------------------------------
# Shared UI data models
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TabSpec:
    key: str
    title: str
    subtitle: str = ""


@dataclass(frozen=True)
class Badge:
    id: int
    name: str
    description: str
    rarity: str
    is_owned: bool = True
    is_selected: bool = False
    is_showcased: bool = False
    ownership_percent: int = 12
    award: str = ""
    category: str = "Прочие"


@dataclass(frozen=True)
class Release:
    id: int
    title: str
    original_title: str
    year: int
    grade: float
    episodes_total: int
    episodes_released: int
    description: str
    country: str = "Япония"
    studio: str = "Studio Demo"
    source: str = "Манга"
    genres: tuple[str, ...] = ()
    status: str = "Выходит"
    age_rating: str = "16+"
    is_adult: bool = False
    is_favorite: bool = False
    seed: int = 0
    image_url: str = ""
    screenshots: tuple[str, ...] = ()
    list_status: int = 0
    vote_count: int = 1200
    votes: tuple[int, int, int, int, int] = (10, 20, 40, 80, 120)
    duration_minutes: int = 24
    schedule: str = "Понедельник"
    is_movie: bool = False


@dataclass(frozen=True)
class Episode:
    id: int
    number: int
    title: str
    duration_seconds: int
    watched: bool
    filler: bool
    type_name: str
    source_name: str
    added_ts: float
    stream_url: str = ""
    iframe: bool = False


@dataclass(frozen=True)
class EpisodeSource:
    id: int
    name: str
    kind: str
    episodes_count: int
    type_id: int = 0
    is_sub: bool = False


@dataclass(frozen=True)
class EpisodeType:
    id: int
    name: str
    is_sub: bool = False


@dataclass(frozen=True)
class Comment:
    id: int
    author: str
    text: str
    timestamp: float
    votes: int
    is_spoiler: bool = False
    is_deleted: bool = False
    is_edited: bool = False
    is_verified: bool = False
    replies: int = 0
    user_vote: int = 0


@dataclass(frozen=True)
class Collection:
    id: int
    title: str
    description: str
    author: str
    created_ts: float
    releases_count: int
    favorites_count: int
    comments_count: int
    is_private: bool = False
    is_favorite: bool = False
    is_owner: bool = False
    seed: int = 0
    watching_count: int = 0
    plan_count: int = 0
    completed_count: int = 0
    hold_count: int = 0
    dropped_count: int = 0


@dataclass(frozen=True)
class CollectionDetails:
    collection: Collection
    releases: tuple[Release, ...]
    description: str
    comments: tuple[Comment, ...]
    is_available: bool = True
    is_deleted: bool = False
    is_private: bool = False


@dataclass(frozen=True)
class ProfileCounters:
    watching: int
    planned: int
    completed: int
    on_hold: int
    dropped: int
    favorites: int


@dataclass(frozen=True)
class Profile:
    id: int
    nick: str
    status: str
    is_verified: bool
    is_sponsor: bool
    is_online: bool
    registered_ts: float
    rating: float
    roles: tuple[str, ...]
    counters: ProfileCounters
    watched_episodes: int
    watched_minutes: int
    comments: int
    videos: int
    collections: int
    friends_count: int
    pinned_section: str = "Статистика"
    is_hidden: bool = False
    is_incognito: bool = False


@dataclass(frozen=True)
class ProfileStatsEntry:
    label: str
    count: int
    color_role: str


@dataclass(frozen=True)
class ProfileData:
    profile: Profile
    stats: tuple[ProfileStatsEntry, ...]
    votes: tuple[Release, ...]
    history: tuple[Release, ...]
    dynamics: tuple[int, ...]
    badges: tuple[Badge, ...]
    collections: tuple[Collection, ...]
    comments: tuple[Comment, ...]
    genres: tuple[str, ...]
    time_format: str = "hours"


@dataclass(frozen=True)
class NotificationItem:
    id: int
    kind: str
    title: str
    message: str
    timestamp: float
    is_new: bool
    spoiler: bool = False
    target_kind: str = "release"
    target_id: int = 0


@dataclass(frozen=True)
class HistoryEntry:
    release: Release
    episode_name: str
    source_name: str
    watch_ts: float


@dataclass(frozen=True)
class Channel:
    id: int
    title: str
    description: str
    subscriber_count: int
    is_subscribed: bool
    is_verified: bool
    is_blog: bool
    is_muted: bool
    article_count: int
    seed: int
    is_creator: bool = False
    permission: str = "Читатель"


@dataclass(frozen=True)
class ChannelDetails:
    channel: Channel
    articles: tuple["Article", ...]
    is_available: bool = True
    is_not_found: bool = False


@dataclass(frozen=True)
class ArticleBlock:
    kind: str
    text: str = ""
    items: tuple[str, ...] = ()
    media_count: int = 0


@dataclass(frozen=True)
class Article:
    id: int
    channel_id: int
    channel_title: str
    title: str
    author: str
    created_ts: float
    blocks: tuple[ArticleBlock, ...]
    votes: int
    comments_count: int
    reposts: int
    is_pinned: bool = False
    is_muted: bool = False
    is_deleted: bool = False
    is_verified: bool = False
    is_signed: bool = True
    channel_seed: int = 0


@dataclass(frozen=True)
class ArticleDetails:
    article: Article
    comments: tuple[Comment, ...]
    is_not_found: bool = False
    is_deleted: bool = False


@dataclass(frozen=True)
class FeedItem:
    article: Article
    channel: Channel


@dataclass(frozen=True)
class InterestingCard:
    id: int
    title: str
    description: str
    seed: int
    image_url: str = ""


@dataclass(frozen=True)
class DiscoverData:
    trending: tuple[InterestingCard, ...]
    quick_links: tuple[tuple[str, str], ...]
    recommendations: tuple[Release, ...]
    discussed: tuple[Article, ...]
    watching_now: tuple[Release, ...]
    collections_week: tuple[Collection, ...]
    comments_week: tuple[Comment, ...]
    social_links: tuple[tuple[str, str], ...]
    sponsorship_text: str


@dataclass(frozen=True)
class SearchResults:
    query: str
    releases: tuple[Release, ...]
    articles: tuple[Article, ...]
    channels: tuple[Channel, ...]
    profiles: tuple[Profile, ...]
    collections: tuple[Collection, ...]
    stale: bool = False


@dataclass(frozen=True)
class HealthEntry:
    title: str
    reason: str
    timestamp: float
    active: bool
    appeal_status: str = ""
    entity_type: str = "Аккаунт"


@dataclass(frozen=True)
class HealthData:
    status: str
    account_entries: tuple[HealthEntry, ...]
    content_entries: tuple[HealthEntry, ...]
    blog_mute_until: float | None = None


@dataclass(frozen=True)
class DeletionData:
    is_requested: bool
    requested_at: float | None = None
    delete_at: float | None = None


@dataclass(frozen=True)
class Page(Generic[T]):
    items: Sequence[T]
    page: int
    page_size: int
    total_count: int
    total_pages: int

    @property
    def has_more(self) -> bool:
        return self.page < self.total_pages


class DemoState(str, Enum):
    DATA = "data"
    EMPTY = "empty"
    ERROR = "error"
    LOADING = "loading"


class DemoRepositoryError(RuntimeError):
    """Raised by the demo repository when the error state is active."""


# --------------------------------------------------------------------------
# Protocols consumed by the screens
# --------------------------------------------------------------------------


class FeedSource(Protocol):
    def feed_tabs(self) -> Sequence[TabSpec]: ...

    def fetch_feed(self, tab_key: str, page: int, page_size: int) -> Page[FeedItem]: ...

    def fetch_discover(self) -> DiscoverData: ...


class Repository(FeedSource, Protocol):
    @property
    def is_authenticated(self) -> bool: ...

    def login(self, login: str, password: str) -> object: ...

    def logout(self) -> None: ...

    def home_tabs(self) -> Sequence[TabSpec]: ...

    def fetch_home(self, tab_key: str, page: int, page_size: int) -> Page[Release]: ...

    def fetch_bookmarks(self, tab_key: str, page: int, page_size: int) -> Page[Release]: ...

    def fetch_search(self, query: str) -> SearchResults: ...

    def search_history(self) -> list[str]: ...

    def clear_search_history(self) -> None: ...

    def fetch_release(self, release_id: int) -> ReleaseDetails: ...

    def fetch_episodes(
        self,
        release_id: int,
        *,
        type_id: int | None = None,
        source_id: int | None = None,
    ) -> tuple[Episode, ...]: ...

    def episode_types(self, release_id: int) -> tuple[EpisodeType, ...]: ...

    def episode_sources(
        self, release_id: int, type_id: int | None = None
    ) -> tuple[EpisodeSource, ...]: ...

    def fetch_comments(self, target_kind: str, target_id: int) -> tuple[Comment, ...]: ...

    def fetch_related(self, kind: str, release_id: int = 0) -> tuple[Release, ...]: ...

    def fetch_profile(self, profile_id: int | None = None) -> ProfileData: ...

    def fetch_notifications(self, filter_key: str) -> tuple[NotificationItem, ...]: ...

    def fetch_collections(self, query: str = "", sort_key: str = "popular") -> tuple[Collection, ...]: ...

    def fetch_collection(self, collection_id: int) -> CollectionDetails: ...

    def fetch_history(self, page: int, page_size: int) -> Page[HistoryEntry]: ...

    def fetch_channels(self, query: str = "", subscribed_only: bool = False) -> tuple[Channel, ...]: ...

    def fetch_channel(self, channel_id: int) -> ChannelDetails: ...

    def fetch_articles(self, channel_id: int | None = None) -> tuple[Article, ...]: ...

    def fetch_article(self, article_id: int) -> ArticleDetails: ...

    def fetch_badges(self, owner_kind: str = "profile", owner_id: int = 0) -> tuple[Badge, ...]: ...

    def fetch_health(self) -> HealthData: ...

    def fetch_deletion(self) -> DeletionData: ...

    def fetch_schedule(self) -> dict[str, tuple[Release, ...]]: ...


@dataclass(frozen=True)
class ReleaseDetails:
    release: Release
    screenshots: int
    badges: tuple[Badge, ...]
    collections: tuple[Collection, ...]
    related: tuple[Release, ...]
    recommended: tuple[Release, ...]
    comments: tuple[Comment, ...]
    user_vote: float | None = None


# --------------------------------------------------------------------------
# Deterministic demo data
# --------------------------------------------------------------------------


_TITLES = (
    "Лунный странник",
    "Сказание о звёздном ветре",
    "Тихий город у моря",
    "Хроники пепельного сада",
    "Девочка и бумажный журавль",
    "Последний рейс «Альбатроса»",
    "Академия северного света",
    "Песни забытых островов",
    "Солнечная мастерская",
    "Клинок под дождём",
    "Чайная на перекрёстке",
    "Небесный курьер",
    "Хранители стеклянной башни",
    "Летний лагерь «Комета»",
    "Искры над горизонтом",
    "Сказки старого трамвая",
    "Второе небо",
    "Повелительница снов",
    "Тропа белых лилий",
    "Механика сердца",
    "Дневник наблюдателя",
    "Королевство тёплых окон",
    "Сны о далёкой гавани",
    "Полночный оркестр",
)

_ORIGINALS = (
    "Tsuki no Wanderer",
    "Star Wind Saga",
    "Quiet Seaside Town",
    "Ash Garden Chronicles",
    "Paper Crane Girl",
    "Last Flight of Albatross",
    "Northern Light Academy",
    "Songs of Forgotten Isles",
    "Solar Workshop",
    "Blade in the Rain",
    "Crossroad Tea House",
    "Sky Courier",
    "Keepers of the Glass Tower",
    "Comet Summer Camp",
    "Sparks Above the Horizon",
    "Tales of the Old Tram",
    "The Second Sky",
    "Mistress of Dreams",
    "Path of White Lilies",
    "Heart Mechanics",
    "Observer's Diary",
    "Kingdom of Warm Windows",
    "Dreams of a Far Harbor",
    "Midnight Orchestra",
)

_STATUSES = ("Выходит", "Завершён", "Анонс", "Фильм", "OVA")
_COUNTRIES = ("Япония", "Япония", "Япония", "Китай")
_GENRES = (
    ("Фэнтези", "Приключения", "Драма"),
    ("Романтика", "Повседневность"),
    ("Фантастика", "Детектив"),
    ("Комедия", "Школа", "Спорт"),
    ("Мистика", "Триллер"),
    ("Музыка", "Драма"),
)
_STUDIOS = ("Studio Demo", "North Light", "Paper Plane", "Blue Harbor", "Kite Works")
_SOURCES = ("Манга", "Ранобэ", "Оригинал", "Игра", "Новелла")
_DESCRIPTIONS = (
    "История о путешествии, в котором герои учатся слышать друг друга и находить дом "
    "даже там, где его не ждали. Спокойный ритм, тёплые диалоги и внимание к деталям.",
    "Небольшой город хранит большую тайну. Двое подростков случайно находят старую "
    "карту и отправляются по следам исчезнувшего трамвая.",
    "После долгой разлуки друзья снова встречаются, чтобы завершить то, что когда-то "
    "начали. Их ждут новые испытания, старые обиды и неожиданные открытия.",
    "Мастерская на окраине города принимает необычные заказы. Каждая история здесь — "
    "о маленьком чуде, которое можно сделать своими руками.",
    "Героине предстоит разобраться в собственных снах и понять, почему один и тот же "
    "сюжет возвращается каждую ночь. Атмосферная мистика с медленным погружением.",
)


class DemoRepository:
    """In-memory repository used by default until the connector is ready.

    All calls are synchronous but cheap; screens schedule them through a
    ``QTimer`` so the UI thread never waits on a network operation.
    """

    def __init__(self) -> None:
        self._authenticated = True
        self._state = DemoState.DATA
        self._listeners: list[Callable[[DemoState], None]] = []
        self._search_history = ["лунный", "странник", "зима"]
        now = datetime.now()
        self._now = now
        self._releases = self._build_releases()
        self._collections = self._build_collections()
        self._channels = self._build_channels()
        self._articles = self._build_articles()
        self._badges = self._build_badges()
        self._profile = self._build_profile()
        self._notifications = self._build_notifications()
        self._history = self._build_history()
        self._health = self._build_health()
        self._deletion = DeletionData(is_requested=False)

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def login(self, login: str, password: str) -> None:
        if not login.strip() or not password:
            raise DemoRepositoryError("Заполните все поля")
        self._authenticated = True

    def logout(self) -> None:
        self._authenticated = False

    # ------------------------------------------------------------------ state
    @property
    def demo_state(self) -> DemoState:
        return self._state

    def set_demo_state(self, state: DemoState | str) -> None:
        self._state = DemoState(state)
        for listener in list(self._listeners):
            listener(self._state)

    def subscribe_state(self, listener: Callable[[DemoState], None]) -> None:
        self._listeners.append(listener)

    def _guard(self) -> None:
        if self._state == DemoState.ERROR:
            raise DemoRepositoryError("Демонстрационное состояние ошибки")

    @property
    def is_empty(self) -> bool:
        return self._state == DemoState.EMPTY

    # ---------------------------------------------------------------- builders
    def _build_releases(self) -> tuple[Release, ...]:
        releases: list[Release] = []
        for index in range(48):
            title_index = index % len(_TITLES)
            status = _STATUSES[index % len(_STATUSES)]
            is_movie = status == "Фильм"
            total = 1 if is_movie else 12 + (index % 3) * 12
            released = total if status in {"Завершён", "Фильм"} else max(1, total - (index % 5))
            grade = round(3.4 + (index * 7 % 26) / 10.0, 1)
            votes = (12 + index, 30 + index, 60 + index, 120 + index, 180 + index)
            releases.append(
                Release(
                    id=1000 + index,
                    title=_TITLES[title_index],
                    original_title=_ORIGINALS[title_index],
                    year=2016 + index % 9,
                    grade=min(grade + (0.4 if index % 4 == 0 else 0.0), 5.0),
                    episodes_total=total,
                    episodes_released=released,
                    description=_DESCRIPTIONS[index % len(_DESCRIPTIONS)],
                    country=_COUNTRIES[index % len(_COUNTRIES)],
                    studio=_STUDIOS[index % len(_STUDIOS)],
                    source=_SOURCES[index % len(_SOURCES)],
                    genres=_GENRES[index % len(_GENRES)],
                    status="Фильм" if is_movie else ("Завершён" if status == "Завершён" else status),
                    age_rating=("18+" if index % 11 == 0 else ("12+" if index % 3 == 0 else "16+")),
                    is_adult=index % 11 == 0,
                    is_favorite=index % 5 == 0,
                    seed=index * 37 + 11,
                    vote_count=850 + index * 73,
                    votes=votes,
                    duration_minutes=96 if is_movie else 24,
                    schedule=("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")[index % 7],
                    is_movie=is_movie,
                )
            )
        return tuple(releases)

    def _build_collections(self) -> tuple[Collection, ...]:
        now = self._now.timestamp()
        titles = (
            "Тёплые истории на вечер",
            "Лучшее фэнтези",
            "Коротко и атмосферно",
            "Романтика без спешки",
            "Детективы и тайны",
            "Смотрим вместе",
        )
        collections = []
        for index, title in enumerate(titles):
            collections.append(
                Collection(
                    id=2000 + index,
                    title=title,
                    description=(
                        "Подборка для спокойного просмотра: несколько историй, "
                        "которые хорошо идут одна за другой."
                    ),
                    author="nickname" if index % 2 else "demo_reader",
                    created_ts=now - 86400 * (7 + index * 3),
                    releases_count=4 + index * 2,
                    favorites_count=128 + index * 47,
                    comments_count=12 + index * 5,
                    is_private=index == 4,
                    is_favorite=index % 3 == 0,
                    is_owner=index == 0,
                    seed=index * 53 + 7,
                    watching_count=6 + index,
                    plan_count=10 + index,
                    completed_count=20 + index,
                    hold_count=2,
                    dropped_count=index,
                )
            )
        return tuple(collections)

    def _build_channels(self) -> tuple[Channel, ...]:
        titles = (
            "Северный ветер",
            "Чайная редакция",
            "Кинолента",
            "Тихие истории",
            "Аниме-кухня",
            "Наблюдатель",
        )
        channels = []
        for index, title in enumerate(titles):
            channels.append(
                Channel(
                    id=3000 + index,
                    title=title,
                    description=(
                        "Канал о спокойных историях, новых сериях и небольших "
                        "открытиях в мире анимации."
                    ),
                    subscriber_count=4200 + index * 1730,
                    is_subscribed=index < 3,
                    is_verified=index in {0, 2},
                    is_blog=index == 1,
                    is_muted=index == 5,
                    article_count=3,
                    seed=index * 67 + 19,
                    is_creator=index == 0,
                    permission="Администратор" if index == 0 else "Читатель",
                )
            )
        return tuple(channels)

    def _build_articles(self) -> tuple[Article, ...]:
        now = self._now.timestamp()
        titles = (
            "Что посмотреть в тихий вечер",
            "Итоги недели: новые серии",
            "Небольшая прогулка по саундтрекам",
            "Как выбрать озвучку",
            "Заметки о цвете и свете",
            "Возвращение к старым историям",
            "Разговор о филлерах",
            "Пять коротких впечатлений",
            "Календарь выходных серий",
            "О чём молчат титры",
            "Письмо редакции",
            "Летний список",
            "Коротко о летнем сезоне",
            "Сезон открытий",
            "Мы снова вместе",
            "Что нового в сообществе",
            "Маленький гид по жанрам",
            "Итоги месяца",
        )
        blocks = (
            ArticleBlock(
                kind="paragraph",
                text=(
                    "Иногда для хорошего вечера достаточно одной истории, которая "
                    "не торопится и оставляет место для собственных мыслей."
                ),
            ),
            ArticleBlock(kind="header", text="Что мы смотрели"),
            ArticleBlock(
                kind="list",
                items=(
                    "«Лунный странник» — спокойное фэнтези о поиске дома.",
                    "«Тихий город у моря» — детектив с мягким юмором.",
                    "«Чайная на перекрёстке» — повседневность без спешки.",
                ),
            ),
            ArticleBlock(
                kind="quote",
                text="«Хорошая история не обязана отвечать на все вопросы».",
            ),
            ArticleBlock(kind="media", media_count=2),
            ArticleBlock(
                kind="paragraph",
                text=(
                    "Делитесь своими находками в комментариях — редакция читает "
                    "каждую подборку и иногда добавляет лучшие в общий список."
                ),
            ),
        )
        articles = []
        for index in range(18):
            channel = self._channels[index % len(self._channels)]
            articles.append(
                Article(
                    id=4000 + index,
                    channel_id=channel.id,
                    channel_title=channel.title,
                    title=titles[index % len(titles)],
                    author="nickname" if index % 2 == 0 else "editor",
                    created_ts=now - 3600 * (3 + index * 7),
                    blocks=blocks,
                    votes=48 + index * 13,
                    comments_count=7 + index,
                    reposts=2 + index % 6,
                    is_pinned=index == 0,
                    is_muted=channel.is_muted,
                    is_verified=channel.is_verified,
                    is_signed=index % 3 != 2,
                    channel_seed=channel.seed,
                )
            )
        return tuple(articles)

    def _build_profile(self) -> ProfileData:
        now = self._now.timestamp()
        profile = Profile(
            id=42,
            nick="nickname",
            status="Смотрю тихие истории и собираю коллекции",
            is_verified=True,
            is_sponsor=True,
            is_online=True,
            registered_ts=now - 86400 * 920,
            rating=4.8,
            roles=("Пользователь", "Автор коллекций", "Спонсор"),
            counters=ProfileCounters(120, 40, 80, 12, 8, 64),
            watched_episodes=1240,
            watched_minutes=28_560,
            comments=12,
            videos=4,
            collections=8,
            friends_count=36,
            pinned_section="Статистика",
            is_hidden=False,
            is_incognito=False,
        )
        stats = (
            ProfileStatsEntry("Смотрю", 120, "status_watching"),
            ProfileStatsEntry("В планах", 40, "status_planned"),
            ProfileStatsEntry("Просмотрено", 80, "status_completed"),
            ProfileStatsEntry("Отложено", 12, "status_on_hold"),
            ProfileStatsEntry("Брошено", 8, "status_dropped"),
        )
        return ProfileData(
            profile=profile,
            stats=stats,
            votes=self._releases[2:8],
            history=self._releases[:5],
            dynamics=(2, 4, 3, 7, 5, 8, 6, 9, 4, 6, 11, 8, 7, 9),
            badges=self._badges,
            collections=self._collections[:4],
            comments=self._comments(5000, 4),
            genres=("Фэнтези", "Повседневность", "Драма", "Мистика"),
        )

    def _build_notifications(self) -> tuple[NotificationItem, ...]:
        now = self._now.timestamp()
        base = (
            ("episode", "Вышла новая серия", "Лунный странник · Серия 5", 180, True, False),
            ("release", "Новый релиз в расписании", "Тихий город у моря", 900, True, False),
            ("article", "Новая запись канала", "Северный ветер: что посмотреть в тихий вечер", 3600, True, False),
            ("reply", "Новый ответ", "nickname ответил на ваш комментарий", 5400, False, True),
            ("friend", "Заявка в друзья", "reader_2025 хочет добавить вас в друзья", 7200, False, False),
            ("achievement", "Получен значок", "«Первый отзыв» теперь в вашем профиле", 9000, False, False),
            ("article", "Новая запись канала", "Чайная редакция: итоги недели", 12000, True, False),
            ("episode", "Вышла новая серия", "Сказание о звёздном ветре · Серия 9", 15000, False, False),
        )
        items = []
        for index, (kind, title, message, age, is_new, spoiler) in enumerate(base):
            target_kind = "release" if kind in {"episode", "release"} else ("article" if kind == "article" else "profile")
            items.append(
                NotificationItem(
                    id=6000 + index,
                    kind=kind,
                    title=title,
                    message=message,
                    timestamp=now - age,
                    is_new=is_new,
                    spoiler=spoiler,
                    target_kind=target_kind,
                    target_id=1000 + index,
                )
            )
        return tuple(items)

    def _build_history(self) -> tuple[HistoryEntry, ...]:
        now = self._now.timestamp()
        entries = []
        sources = ("AniLibria", "Studio Band", "AniDUB", "Субтитры")
        for index in range(16):
            release = self._releases[index % len(self._releases)]
            entries.append(
                HistoryEntry(
                    release=release,
                    episode_name=f"Серия {1 + index % 12}",
                    source_name=sources[index % len(sources)],
                    watch_ts=now - 3600 * (2 + index * 5),
                )
            )
        return tuple(entries)

    def _build_badges(self) -> tuple[Badge, ...]:
        rarities = ("common", "uncommon", "rare", "epic", "legendary")
        names = (
            "Первый отзыв",
            "Ночной просмотр",
            "Коллекционер",
            "Тёплая история",
            "Верный друг",
            "Открытие сезона",
            "Ценитель тишины",
            "Автор недели",
            "Звёздный читатель",
            "Хранитель списков",
            "Ранний гость",
            "Легенда сообщества",
        )
        badges = []
        for index, name in enumerate(names):
            badges.append(
                Badge(
                    id=7000 + index,
                    name=name,
                    description="Выдаётся за активность в сообществе и просмотр релизов.",
                    rarity=rarities[index % len(rarities)],
                    is_owned=index < 9,
                    is_selected=index == 0,
                    is_showcased=index < 3,
                    ownership_percent=4 + index * 3,
                    award="Просмотр 100 серий" if index % 2 else "Участие в событии",
                    category="Активность" if index < 6 else "События",
                )
            )
        return tuple(badges)

    def _build_health(self) -> HealthData:
        now = self._now.timestamp()
        entries = (
            HealthEntry(
                title="Комментарий скрыт",
                reason="Нарушение правил сообщества: спойлер без пометки.",
                timestamp=now - 86400 * 48,
                active=False,
                appeal_status="Рассмотрена",
                entity_type="Комментарий",
            ),
        )
        return HealthData(
            status="Всё в порядке",
            account_entries=(),
            content_entries=entries,
        )

    def _comments(self, start: int, count: int) -> tuple[Comment, ...]:
        now = self._now.timestamp()
        texts = (
            "Спасибо за подборку — как раз искал что-то спокойное на вечер.",
            "Согласен, вторая серия получилась особенно атмосферной.",
            "Интересно, как дальше раскроют линию с картой.",
            "Добавил в закладки, посмотрю на выходных.",
            "Не совсем согласен с оценкой, но рад обсуждению.",
        )
        comments = []
        for index in range(count):
            comments.append(
                Comment(
                    id=start + index,
                    author=("reader_2025", "quiet_watcher", "paper_crane", "nickname")[index % 4],
                    text=texts[index % len(texts)],
                    timestamp=now - 3600 * (2 + index * 9),
                    votes=12 - index * 2,
                    is_spoiler=index % 5 == 3,
                    is_edited=index % 6 == 2,
                    is_verified=index % 3 == 0,
                    replies=index % 3,
                )
            )
        return tuple(comments)

    # --------------------------------------------------------------- entities
    def _release_by_id(self, release_id: int) -> Release:
        for release in self._releases:
            if release.id == release_id:
                return release
        return self._releases[0]

    def _channel_by_id(self, channel_id: int) -> Channel:
        for channel in self._channels:
            if channel.id == channel_id:
                return channel
        return self._channels[0]

    def _article_by_id(self, article_id: int) -> Article:
        for article in self._articles:
            if article.id == article_id:
                return article
        return self._articles[0]

    def _collection_by_id(self, collection_id: int) -> Collection:
        for collection in self._collections:
            if collection.id == collection_id:
                return collection
        return self._collections[0]

    @staticmethod
    def _paginate(items: Sequence[T], page: int, page_size: int) -> Page[T]:
        page = max(1, page)
        page_size = max(1, page_size)
        total = len(items)
        total_pages = max(1, math.ceil(total / page_size))
        start = (page - 1) * page_size
        return Page(
            items=tuple(items[start : start + page_size]),
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=total_pages,
        )

    # ------------------------------------------------------------------- tabs
    def home_tabs(self) -> Sequence[TabSpec]:
        from .strings import S

        return tuple(
            TabSpec(title=title, key=f"home_{index}", subtitle=S.HOME_TAB_SUBTITLES[index])
            for index, title in enumerate(S.HOME_TABS)
        )

    def bookmark_tabs(self) -> Sequence[TabSpec]:
        from .strings import S

        return tuple(
            TabSpec(title=title, key=f"bookmark_{index}")
            for index, title in enumerate(S.BOOKMARK_TABS)
        )

    def feed_tabs(self) -> Sequence[TabSpec]:
        from .strings import S

        return tuple(
            TabSpec(title=title, key=f"feed_{index}")
            for index, title in enumerate(S.FEED_TABS)
        )

    # ----------------------------------------------------------------- catalog
    def fetch_home(self, tab_key: str, page: int, page_size: int) -> Page[Release]:
        self._guard()
        if self.is_empty:
            return self._paginate((), page, page_size)
        index = int(tab_key.rsplit("_", 1)[-1]) if tab_key.rsplit("_", 1)[-1].isdigit() else 0
        items = list(self._releases)
        if index == 1:
            items = [r for r in items if r.country == "Япония"]
        elif index == 2:
            items = [r for r in items if r.country == "Китай"]
        elif index == 3:
            items = items[:24]
        elif index == 4:
            items = [r for r in items if r.status == "Выходит"]
        elif index == 5:
            items = [r for r in items if r.status == "Анонс"]
        elif index == 6:
            items = [r for r in items if r.status == "Завершён"]
        elif index == 7:
            items = [r for r in items if r.is_movie]
        elif index == 8:
            items = [r for r in items if r.status == "OVA"]
        return self._paginate(items, page, page_size)

    def fetch_bookmarks(self, tab_key: str, page: int, page_size: int) -> Page[Release]:
        self._guard()
        if self.is_empty:
            return self._paginate((), page, page_size)
        index = int(tab_key.rsplit("_", 1)[-1]) if tab_key.rsplit("_", 1)[-1].isdigit() else 0
        items = list(self._releases)
        if index == 0:
            items = []  # collections are shown by the dedicated screen
        elif index == 1:
            items = [entry.release for entry in self._history]
        elif index == 2:
            items = [r for r in items if r.is_favorite]
        elif index == 3:
            items = items[:20]
        elif index == 4:
            items = items[20:32]
        elif index == 5:
            items = items[32:40]
        elif index == 6:
            items = items[40:44]
        elif index == 7:
            items = items[44:]
        return self._paginate(items, page, page_size)

    def fetch_featured(self, kind: str = "recommendations") -> tuple[Release, ...]:
        self._guard()
        if self.is_empty:
            return ()
        if kind == "watching":
            return self._releases[6:16]
        if kind == "related":
            return self._releases[12:22]
        if kind == "recommended":
            return self._releases[20:30]
        return self._releases[0:12]

    # ------------------------------------------------------------------ search
    def fetch_search(self, query: str) -> SearchResults:
        self._guard()
        normalized = query.strip().lower()
        if self.is_empty or not normalized:
            return SearchResults(query=query, releases=(), articles=(), channels=(), profiles=(), collections=())
        releases = tuple(r for r in self._releases if normalized in r.title.lower() or normalized in r.original_title.lower())
        articles = tuple(a for a in self._articles if normalized in a.title.lower())
        channels = tuple(c for c in self._channels if normalized in c.title.lower())
        collections = tuple(c for c in self._collections if normalized in c.title.lower())
        profiles = tuple(p for p in (self._profile.profile,) if normalized in p.nick.lower())
        return SearchResults(
            query=query,
            releases=releases[:12],
            articles=articles[:4],
            channels=channels[:4],
            profiles=profiles,
            collections=collections[:4],
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

    # ----------------------------------------------------------------- release
    def fetch_release(self, release_id: int) -> ReleaseDetails:
        self._guard()
        release = self._release_by_id(release_id)
        collection = self._collections
        return ReleaseDetails(
            release=release,
            screenshots=6,
            badges=self._badges[:6],
            collections=collection[:4],
            related=self._releases[10:18],
            recommended=self._releases[24:32],
            comments=self._comments(8000, 3),
            user_vote=4.0 if release_id % 2 == 0 else None,
        )

    def fetch_episodes(
        self,
        release_id: int,
        *,
        type_id: int | None = None,
        source_id: int | None = None,
    ) -> tuple[Episode, ...]:
        self._guard()
        if self.is_empty:
            return ()
        release = self._release_by_id(release_id)
        sources = ("AniLibria", "Studio Band", "AniDUB")
        source_names = {1: "AniLibria", 2: "Studio Band", 3: "AniDUB", 4: "Субтитры"}
        episodes = []
        count = release.episodes_released
        for index in range(1, count + 1):
            episodes.append(
                Episode(
                    id=release_id * 100 + index,
                    number=index,
                    title=f"Серия {index}",
                    duration_seconds=release.duration_minutes * 60,
                    watched=index <= 3,
                    filler=index % 7 == 0,
                    type_name="Озвучка",
                    source_name=sources[index % len(sources)],
                    added_ts=self._now.timestamp() - 86400 * (count - index),
                )
            )
        if type_id == 2 or source_id == 4:
            return tuple(
                Episode(
                    id=episode.id + 5000,
                    number=episode.number,
                    title=episode.title,
                    duration_seconds=episode.duration_seconds,
                    watched=episode.watched,
                    filler=episode.filler,
                    type_name="Субтитры",
                    source_name="Субтитры",
                    added_ts=episode.added_ts,
                )
                for episode in episodes
            )
        name = source_names.get(source_id or 0)
        if name:
            return tuple(episode for episode in episodes if episode.source_name == name)
        return tuple(episodes)

    def episode_types(self, release_id: int) -> tuple[EpisodeType, ...]:
        self._guard()
        return (
            EpisodeType(1, "Озвучка", False),
            EpisodeType(2, "Субтитры", True),
        )

    def episode_sources(
        self, release_id: int, type_id: int | None = None
    ) -> tuple[EpisodeSource, ...]:
        self._guard()
        sources = (
            EpisodeSource(1, "AniLibria", "Озвучка", 12, type_id=1),
            EpisodeSource(2, "Studio Band", "Озвучка", 12, type_id=1),
            EpisodeSource(3, "AniDUB", "Озвучка", 12, type_id=1),
            EpisodeSource(4, "Субтитры", "Субтитры", 12, type_id=2, is_sub=True),
        )
        if type_id is not None:
            return tuple(source for source in sources if source.type_id == type_id)
        return sources

    def fetch_comments(self, target_kind: str, target_id: int) -> tuple[Comment, ...]:
        self._guard()
        if self.is_empty:
            return ()
        return self._comments(9000, 6)

    def fetch_related(self, kind: str, release_id: int = 0) -> tuple[Release, ...]:
        return self.fetch_featured(kind)

    # ----------------------------------------------------------------- profile
    def fetch_profile(self, profile_id: int | None = None) -> ProfileData:
        self._guard()
        return self._profile

    # ----------------------------------------------------------- notifications
    def fetch_notifications(self, filter_key: str) -> tuple[NotificationItem, ...]:
        self._guard()
        if self.is_empty:
            return ()
        mapping = {
            "episodes": {"episode"},
            "releases": {"release"},
            "articles": {"article"},
            "friends": {"friend"},
            "replies": {"reply"},
        }
        kinds = mapping.get(filter_key)
        if kinds is None:
            return self._notifications
        return tuple(item for item in self._notifications if item.kind in kinds)

    def mark_notification_read(self, notification_id: int) -> None:
        # Demo mutation: rebuild tuple with is_new=False.
        from dataclasses import replace

        self._notifications = tuple(
            replace(item, is_new=False) if item.id == notification_id else item
            for item in self._notifications
        )

    def delete_notification(self, notification_id: int) -> None:
        self._notifications = tuple(item for item in self._notifications if item.id != notification_id)

    def delete_all_notifications(self) -> None:
        self._notifications = ()

    # ------------------------------------------------------------- collections
    def fetch_collections(self, query: str = "", sort_key: str = "popular") -> tuple[Collection, ...]:
        self._guard()
        if self.is_empty:
            return ()
        items = list(self._collections)
        if query.strip():
            normalized = query.strip().lower()
            items = [item for item in items if normalized in item.title.lower()]
        if sort_key == "new":
            items.sort(key=lambda item: item.created_ts, reverse=True)
        elif sort_key == "favorites":
            items.sort(key=lambda item: item.favorites_count, reverse=True)
        return tuple(items)

    def fetch_collection(self, collection_id: int) -> CollectionDetails:
        self._guard()
        collection = self._collection_by_id(collection_id)
        return CollectionDetails(
            collection=collection,
            releases=self._releases[: collection.releases_count] if not collection.is_private else (),
            description=collection.description,
            comments=self._comments(9200, 3),
            is_available=not collection.is_private,
            is_deleted=False,
            is_private=collection.is_private,
        )

    # ----------------------------------------------------------------- history
    def fetch_history(self, page: int, page_size: int) -> Page[HistoryEntry]:
        self._guard()
        if self.is_empty:
            return self._paginate((), page, page_size)
        return self._paginate(self._history, page, page_size)

    # ---------------------------------------------------------------- channels
    def fetch_channels(self, query: str = "", subscribed_only: bool = False) -> tuple[Channel, ...]:
        self._guard()
        if self.is_empty:
            return ()
        items = list(self._channels)
        if query.strip():
            normalized = query.strip().lower()
            items = [item for item in items if normalized in item.title.lower()]
        if subscribed_only:
            items = [item for item in items if item.is_subscribed]
        return tuple(items)

    def fetch_channel(self, channel_id: int) -> ChannelDetails:
        self._guard()
        channel = self._channel_by_id(channel_id)
        articles = tuple(article for article in self._articles if article.channel_id == channel.id)
        return ChannelDetails(channel=channel, articles=articles)

    # ---------------------------------------------------------------- articles
    def fetch_articles(self, channel_id: int | None = None) -> tuple[Article, ...]:
        self._guard()
        if self.is_empty:
            return ()
        if channel_id is not None:
            return tuple(article for article in self._articles if article.channel_id == channel_id)
        return self._articles

    def fetch_article(self, article_id: int) -> ArticleDetails:
        self._guard()
        article = self._article_by_id(article_id)
        return ArticleDetails(
            article=article,
            comments=self._comments(9400, 4),
            is_not_found=self.is_empty,
        )

    def fetch_feed(self, tab_key: str, page: int, page_size: int) -> Page[FeedItem]:
        self._guard()
        if self.is_empty:
            return self._paginate((), page, page_size)
        index = int(tab_key.rsplit("_", 1)[-1]) if tab_key.rsplit("_", 1)[-1].isdigit() else 0
        articles = list(self._articles)
        if index == 0:
            articles = [article for article in articles if self._channel_by_id(article.channel_id).is_subscribed]
        elif index == 1:
            articles = articles[:12]
        else:
            articles = [article for article in articles if self._channel_by_id(article.channel_id).is_creator]
        items = tuple(
            FeedItem(article=article, channel=self._channel_by_id(article.channel_id))
            for article in articles
        )
        return self._paginate(items, page, page_size)

    def fetch_discover(self) -> DiscoverData:
        self._guard()
        if self.is_empty:
            return DiscoverData((), (), (), (), (), (), (), (), "")
        trending = tuple(
            InterestingCard(
                id=9000 + index,
                title=title,
                description=description,
                seed=index * 29 + 3,
            )
            for index, (title, description) in enumerate(
                (
                    ("Актуальное сегодня", "Подборка обновлений и новых серий"),
                    ("Коллекции недели", "Истории, которые советует сообщество"),
                    ("Разговоры", "Что обсуждают читатели прямо сейчас"),
                )
            )
        )
        quick = (
            ("discover_new", "Новинки"),
            ("schedule", "Расписание"),
            ("updates", "Обновления серий"),
            ("collections", "Коллекции"),
            ("filter", "Фильтр"),
        )
        socials = (
            ("ВКонтакте", "vk"),
            ("Telegram", "telegram"),
            ("Discord", "discord"),
            ("Instagram", "instagram"),
        )
        return DiscoverData(
            trending=trending,
            quick_links=quick,
            recommendations=self._releases[3:15],
            discussed=self._articles[:4],
            watching_now=self._releases[18:30],
            collections_week=self._collections,
            comments_week=self._comments(9600, 4),
            social_links=socials,
            sponsorship_text="Поддержите проект и помогите делать интерфейс лучше.",
        )

    # ------------------------------------------------------------------ badges
    def fetch_badges(self, owner_kind: str = "profile", owner_id: int = 0) -> tuple[Badge, ...]:
        self._guard()
        if self.is_empty:
            return ()
        if owner_kind == "release":
            return self._badges[:6]
        return self._badges

    # ------------------------------------------------------------------ health
    def fetch_health(self) -> HealthData:
        self._guard()
        if self.is_empty:
            return HealthData(status="Всё в порядке", account_entries=(), content_entries=())
        return self._health

    def fetch_deletion(self) -> DeletionData:
        self._guard()
        return self._deletion

    def request_deletion(self) -> DeletionData:
        now = datetime.now().timestamp()
        self._deletion = DeletionData(
            is_requested=True,
            requested_at=now,
            delete_at=now + 86400 * 30,
        )
        return self._deletion

    def cancel_deletion(self) -> DeletionData:
        self._deletion = DeletionData(is_requested=False)
        return self._deletion

    # ---------------------------------------------------------------- schedule
    def fetch_schedule(self) -> dict[str, tuple[Release, ...]]:
        self._guard()
        days = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")
        return {
            day: tuple(release for release in self._releases if release.schedule == day)[:6]
            for day in days
        }


__all__ = [
    "Article",
    "ArticleBlock",
    "ArticleDetails",
    "Badge",
    "Channel",
    "ChannelDetails",
    "Collection",
    "CollectionDetails",
    "Comment",
    "DeletionData",
    "DemoRepository",
    "DemoRepositoryError",
    "DemoState",
    "DiscoverData",
    "Episode",
    "EpisodeSource",
    "FeedItem",
    "FeedSource",
    "HealthData",
    "HealthEntry",
    "HistoryEntry",
    "InterestingCard",
    "NotificationItem",
    "Page",
    "Profile",
    "ProfileCounters",
    "ProfileData",
    "ProfileStatsEntry",
    "Release",
    "ReleaseDetails",
    "Repository",
    "SearchResults",
    "TabSpec",
]
