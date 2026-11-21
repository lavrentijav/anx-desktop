"""Domain-scoped endpoint facades used by :class:`~anx_desktop.api.client.AnixartClient`."""

from __future__ import annotations

from .comments import CommentEndpoints
from .config import ConfigEndpoints
from .episodes import EpisodeEndpoints
from .feed import FeedEndpoints
from .history import HistoryEndpoints
from .notifications import NotificationEndpoints
from .profile import ProfileEndpoints
from .releases import ReleaseEndpoints
from .search import SearchEndpoints

__all__ = [
    "CommentEndpoints",
    "ConfigEndpoints",
    "EpisodeEndpoints",
    "FeedEndpoints",
    "HistoryEndpoints",
    "NotificationEndpoints",
    "ProfileEndpoints",
    "ReleaseEndpoints",
    "SearchEndpoints",
]
