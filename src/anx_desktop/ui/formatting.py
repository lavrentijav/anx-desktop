"""Russian number/date formatting helpers used by the UI."""

from __future__ import annotations

from datetime import datetime, timedelta


def plural_ru(number: int, one: str, few: str, many: str) -> str:
    value = abs(int(number))
    if value % 10 == 1 and value % 100 != 11:
        return one
    if 2 <= value % 10 <= 4 and not 12 <= value % 100 <= 14:
        return few
    return many


def episodes(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'эпизод', 'эпизода', 'эпизодов')}"


def episodes_short(count: int) -> str:
    return f"{format_count(count)} эп."


def episodes_progress(released: int, total: int) -> str:
    """``5 из 12 эп.`` when the total is known, otherwise ``5 эп.``."""

    if released > 0 and total > released:
        return f"{format_count(released)} из {format_count(total)} эп."
    count = total or released
    return episodes_short(count) if count > 0 else ""


def collections(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'коллекция', 'коллекции', 'коллекций')}"


def releases(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'релиз', 'релиза', 'релизов')}"


def subscribers(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'подписчик', 'подписчика', 'подписчиков')}"


def users(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'пользователь', 'пользователя', 'пользователей')}"


def voices(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'голос', 'голоса', 'голосов')}"


def comments(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'комментарий', 'комментария', 'комментариев')}"


def friends(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'друг', 'друга', 'друзей')}"


def views(count: int) -> str:
    return f"{format_count(count)} {plural_ru(count, 'просмотр', 'просмотра', 'просмотров')}"


def format_count(value: int | float) -> str:
    if isinstance(value, float):
        return f"{value:,.1f}".replace(",", " ").replace(".", ",")
    return f"{int(value):,}".replace(",", " ")


def format_rating(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}".replace(".", ",")


def format_episode_number(index: int) -> str:
    return f"Серия {index}"


def format_duration_minutes(minutes: int) -> str:
    return f"{minutes} мин."


def format_watch_time(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} мин."
    hours, rest = divmod(minutes, 60)
    if rest:
        return f"{hours} ч. {rest} мин."
    return f"{hours} ч."


_MONTHS_SHORT = (
    "янв.",
    "февр.",
    "мар.",
    "апр.",
    "мая",
    "июн.",
    "июл.",
    "авг.",
    "сент.",
    "окт.",
    "нояб.",
    "дек.",
)


def format_date(ts: datetime | int | float, now: datetime | None = None) -> str:
    if isinstance(ts, (int, float)):
        date = datetime.fromtimestamp(ts)
    else:
        date = ts
    now = now or datetime.now()
    delta = now - date
    if delta < timedelta(minutes=1):
        return "только что"
    if date.date() == now.date():
        return f"сегодня в {date:%H:%M}"
    if date.date() == (now - timedelta(days=1)).date():
        return f"вчера в {date:%H:%M}"
    if date.year == now.year:
        return f"{date.day} {_MONTHS_SHORT[date.month - 1]} в {date:%H:%M}"
    return f"{date:%d.%m.%Y} в {date:%H:%M}"


def format_date_short(ts: datetime | int | float) -> str:
    date = datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else ts
    return f"{date.day} {_MONTHS_SHORT[date.month - 1]} {date.year}"


def format_timestamp(seconds: int | float) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
