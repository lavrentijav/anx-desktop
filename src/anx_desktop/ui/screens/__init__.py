"""Application screens."""

from .articles import ArticleEditorScreen, ArticleScreen, ArticlesScreen
from .auth import (
    AuthScreen,
    EmailAuthScreen,
    QrAuthScreen,
    RegistrationScreen,
    RestoreScreen,
)
from .badges import BadgesScreen
from .base import AppHost, BaseScreen, ScreenContext
from .bookmarks import BookmarksScreen
from .channels import ChannelManageScreen, ChannelScreen, ChannelsScreen
from .collections import CollectionScreen, CollectionsScreen
from .discover import DiscoverScreen
from .episodes import EpisodesScreen
from .filter import FilterScreen
from .health import DeletionScreen, HealthScreen
from .history import HistoryScreen
from .home import HomeScreen
from .misc import (
    CommentsScreen,
    ListScreen,
    NeedAuthScreen,
    ScheduleScreen,
    UpdatesScreen,
)
from .notifications import NotificationsScreen
from .player import PlayerScreen
from .profile import ProfileScreen
from .release import ReleaseScreen
from .search import SearchScreen
from .settings import SettingsScreen
from .social_feed import SocialFeedScreen

__all__ = [
    "AppHost",
    "ArticleEditorScreen",
    "ArticleScreen",
    "ArticlesScreen",
    "AuthScreen",
    "BadgesScreen",
    "BaseScreen",
    "BookmarksScreen",
    "ChannelManageScreen",
    "ChannelScreen",
    "ChannelsScreen",
    "CollectionScreen",
    "CollectionsScreen",
    "CommentsScreen",
    "DeletionScreen",
    "DiscoverScreen",
    "EmailAuthScreen",
    "EpisodesScreen",
    "FilterScreen",
    "HealthScreen",
    "HistoryScreen",
    "HomeScreen",
    "ListScreen",
    "NeedAuthScreen",
    "NotificationsScreen",
    "PlayerScreen",
    "ProfileScreen",
    "QrAuthScreen",
    "RegistrationScreen",
    "ReleaseScreen",
    "RestoreScreen",
    "ScheduleScreen",
    "ScreenContext",
    "SearchScreen",
    "SettingsScreen",
    "SocialFeedScreen",
    "UpdatesScreen",
]
