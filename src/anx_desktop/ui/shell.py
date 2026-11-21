"""Desktop shell: sidebar, shared top bar and snackbar overlay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from PySide6.QtCore import QObject, QRunnable, QSize, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .data import DemoRepository, HistoryEntry, Repository
from .strings import S
from .theme import active_theme
from .widgets import Avatar, ClickableFrame, CountBadge, IconButton, LogoMark, PosterWidget, SearchField


@dataclass(frozen=True)
class NavEntry:
    key: str
    title: str
    icon: str
    route: str
    group: str


NAV_GROUPS = (S.NAV_MAIN_GROUP, S.NAV_LIBRARY_GROUP, S.NAV_ACCOUNT_GROUP)

NAV_ENTRIES: tuple[NavEntry, ...] = (
    NavEntry("home", S.NAV_HOME, "home", "home", S.NAV_MAIN_GROUP),
    NavEntry("discover", S.NAV_DISCOVER, "discover", "discover", S.NAV_MAIN_GROUP),
    NavEntry("bookmarks", S.NAV_BOOKMARKS, "bookmarks", "bookmarks", S.NAV_MAIN_GROUP),
    NavEntry("feed", S.NAV_FEED, "feed", "feed", S.NAV_MAIN_GROUP),
    NavEntry("search", S.NAV_SEARCH, "search", "search", S.NAV_LIBRARY_GROUP),
    NavEntry("collections", S.NAV_COLLECTIONS, "collection", "collections", S.NAV_LIBRARY_GROUP),
    NavEntry("history", S.NAV_HISTORY, "history", "history", S.NAV_LIBRARY_GROUP),
    NavEntry("channels", S.NAV_CHANNELS, "channel", "channels", S.NAV_LIBRARY_GROUP),
    NavEntry("articles", S.NAV_ARTICLES, "article", "articles", S.NAV_LIBRARY_GROUP),
    NavEntry("schedule", S.SCHEDULE_TITLE, "calendar", "schedule", S.NAV_LIBRARY_GROUP),
    NavEntry("profile", S.NAV_PROFILE, "user", "profile", S.NAV_ACCOUNT_GROUP),
    NavEntry("notifications", S.NAV_NOTIFICATIONS, "bell", "notifications", S.NAV_ACCOUNT_GROUP),
    NavEntry("settings", S.NAV_SETTINGS, "settings", "settings", S.NAV_ACCOUNT_GROUP),
)

# Detail routes highlight a parent section in the sidebar.
ROUTE_PARENT = {
    "release": "home",
    "episodes": "home",
    "player": "player",
    "release_badges": "badges",
    "collection": "collections",
    "channel": "channels",
    "channel_manage": "channels",
    "article": "articles",
    "article_editor": "articles",
    "comments": "home",
    "list": "home",
    "filter": "search",
    "updates": "schedule",
}


class Sidebar(QFrame):
    navigate = Signal(str)
    compact_requested = Signal(bool)

    def __init__(self, *, compact: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "sidebar")
        self._compact = compact
        self._buttons: dict[str, QPushButton] = {}
        self._labels: list[QLabel] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(theme.space("sm"), theme.space("m"), theme.space("sm"), theme.space("m"))
        root.setSpacing(theme.space("xxs"))
        self._header = QWidget(self)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(theme.space("xs"), 0, theme.space("xs"), theme.space("m"))
        header_layout.setSpacing(theme.space("sm"))
        self._logo = LogoMark(36, parent=self._header)
        header_layout.addWidget(self._logo)
        self._name = QLabel(S.APP_NAME, self._header)
        self._name.setProperty("role", "logo")
        header_layout.addWidget(self._name)
        header_layout.addStretch(1)
        root.addWidget(self._header)
        self._group_labels: dict[str, QLabel] = {}
        self._nav_host = QWidget(self)
        nav_layout = QVBoxLayout(self._nav_host)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(theme.space("xxs"))
        for group in NAV_GROUPS:
            group_label = QLabel(group, self._nav_host)
            group_label.setProperty("role", "uppercase")
            group_label.setContentsMargins(theme.space("sm"), theme.space("sm"), 0, theme.space("xs"))
            self._group_labels[group] = group_label
            self._labels.append(group_label)
            nav_layout.addWidget(group_label)
            for entry in NAV_ENTRIES:
                if entry.group != group:
                    continue
                button = QPushButton(entry.title, self._nav_host)
                button.setProperty("ui", "nav")
                button.setCheckable(True)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setIcon(icons.icon(entry.icon, "icon", 20))
                button.setIconSize(QSize(20, 20))
                button.setToolTip(entry.title)
                button.clicked.connect(lambda _checked=False, route=entry.route: self.navigate.emit(route))
                self._buttons[entry.key] = button
                nav_layout.addWidget(button)
        nav_layout.addStretch(1)
        self._nav_scroll = QScrollArea(self)
        self._nav_scroll.setWidgetResizable(True)
        self._nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._nav_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._nav_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._nav_scroll.viewport().setAutoFillBackground(False)
        self._nav_scroll.setWidget(self._nav_host)
        root.addWidget(self._nav_scroll, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(theme.space("xs"), theme.space("sm"), theme.space("xs"), 0)
        self._collapse = IconButton("chevron_left", size=20, tooltip=S.NAV_COLLAPSE, parent=self)
        self._collapse.clicked.connect(self._toggle_compact)
        footer.addWidget(self._collapse)
        footer.addStretch(1)
        root.addLayout(footer)
        self._apply_compact()
        active_theme().changed.connect(self._refresh_icons)

    def _refresh_icons(self) -> None:
        for entry in NAV_ENTRIES:
            button = self._buttons.get(entry.key)
            if button is not None:
                button.setIcon(icons.icon(entry.icon, "icon", 20))
        self._collapse.set_icon("chevron_right" if self._compact else "chevron_left")

    def _toggle_compact(self) -> None:
        self.set_compact(not self._compact)
        self.compact_requested.emit(self._compact)

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        self._apply_compact()

    def _apply_compact(self) -> None:
        theme = active_theme()
        width = theme.desktop("side_nav_collapsed_width_px") if self._compact else theme.desktop("side_nav_width_px")
        self.setFixedWidth(theme.px(width))
        self._name.setVisible(not self._compact)
        self._logo.setVisible(True)
        for group, label in self._group_labels.items():
            label.setVisible(not self._compact)
        for entry in NAV_ENTRIES:
            button = self._buttons[entry.key]
            button.setText("" if self._compact else entry.title)
            button.setToolTip(entry.title)
            if self._compact:
                button.setFixedHeight(theme.px(42))
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            else:
                button.setMaximumHeight(16777215)
                button.setMinimumHeight(theme.px(34))
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._collapse.set_icon("chevron_right" if self._compact else "chevron_left")
        self._collapse.setToolTip(S.NAV_EXPAND if self._compact else S.NAV_COLLAPSE)

    def set_active(self, route: str) -> None:
        target = ROUTE_PARENT.get(route, route)
        for key, button in self._buttons.items():
            button.setChecked(key == target)


class NotificationButton(QWidget):
    clicked = Signal()

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setFixedSize(theme.px(40), theme.px(40))
        self._button = IconButton("bell", size=22, tooltip=S.TOOLTIP_NOTIFICATIONS, parent=self)
        self._button.setGeometry(0, 0, theme.px(40), theme.px(40))
        self._button.clicked.connect(self.clicked)
        self._badge = CountBadge(0, parent=self)
        self._badge.move(theme.px(24), theme.px(2))

    def set_count(self, count: int) -> None:
        self._badge.set_count(count)
        self._badge.move(self.width() - self._badge.width() - 2, 2)


class AvatarButton(QWidget):
    clicked = Signal()

    def __init__(self, name: str = "nickname", *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setFixedSize(theme.px(40), theme.px(40))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(S.TOOLTIP_PROFILE)
        self._avatar = Avatar(name, size=theme.px(32), seed=42, online=True, parent=self)
        self._avatar.move(theme.px(4), theme.px(4))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ContinueChip(ClickableFrame):
    play_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, entry: HistoryEntry | None, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setFixedHeight(theme.px(48))
        self.setMaximumWidth(theme.px(290))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.space("xs"), theme.space("xs"), theme.space("xs"), theme.space("xs"))
        layout.setSpacing(theme.space("sm"))
        if entry is not None:
            poster = PosterWidget(entry.release, width=theme.px(28), height=theme.px(38), parent=self)
            layout.addWidget(poster)
            text = QVBoxLayout()
            text.setSpacing(0)
            title = QLabel(entry.release.title, self)
            title.setStyleSheet("font-weight: 500;")
            title.setMaximumWidth(theme.px(170))
            text.addWidget(title)
            subtitle = QLabel(f"{entry.episode_name} · {entry.source_name}", self)
            subtitle.setProperty("role", "tertiary")
            text.addWidget(subtitle)
            layout.addLayout(text, 1)
        else:
            layout.addWidget(QLabel(S.HOME_CONTINUE, self), 1)
        play = IconButton("play", role="icon_alt", size=18, tooltip=S.HOME_CONTINUE, parent=self)
        play.clicked.connect(self.play_clicked)
        layout.addWidget(play)
        close = IconButton("close", size=14, tooltip=S.TOOLTIP_CLOSE, parent=self)
        close.clicked.connect(self.close_clicked)
        layout.addWidget(close)
        self._refresh_style()
        active_theme().changed.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        theme = active_theme()
        self.setStyleSheet(
            f"QFrame {{ background-color: {theme.color('surface_secondary')};"
            f"border: 1px solid {theme.color('border_soft')};"
            f"border-radius: {theme.radius('button')}px; }}"
        )


class _HistorySignals(QObject):
    loaded = Signal(object)


class _HistoryJob(QRunnable):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.signals = _HistorySignals()

    def run(self) -> None:
        try:
            page = self.repo.fetch_history(1, 1)
            entry = page.items[0] if page.items else None
        except Exception:
            entry = None
        self.signals.loaded.emit(entry)


class TopBar(QFrame):
    back_clicked = Signal()
    forward_clicked = Signal()
    search_submitted = Signal(str)
    search_focus_requested = Signal()
    refresh_clicked = Signal()
    theme_clicked = Signal()
    notifications_clicked = Signal()
    settings_clicked = Signal()
    profile_clicked = Signal()
    create_article = Signal()
    create_channel = Signal()
    continue_play = Signal()
    continue_hidden = Signal()

    def __init__(
        self,
        repo: Repository,
        *,
        show_continue: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "topBar")
        self.setFixedHeight(theme.semantic("toolbar_height") + theme.space("xs"))
        self._repo = repo
        self._show_continue_setting = show_continue
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.space("m"), theme.space("xs"), theme.space("m"), theme.space("xs"))
        layout.setSpacing(theme.space("xs"))
        self._back = IconButton("back", size=20, tooltip=S.TOOLTIP_BACK, parent=self)
        self._back.clicked.connect(self.back_clicked)
        self._back.setEnabled(False)
        layout.addWidget(self._back)
        self._forward = IconButton("forward", size=20, tooltip=S.TOOLTIP_FORWARD, parent=self)
        self._forward.clicked.connect(self.forward_clicked)
        self._forward.setEnabled(False)
        layout.addWidget(self._forward)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self._title = QLabel(S.NAV_HOME, self)
        self._title.setStyleSheet(
            f"font-weight: 600; font-size: {theme.px(float(theme.tokens.typography('settings_title')['size_sp']))}px;"
        )
        title_box.addWidget(self._title)
        self._subtitle = QLabel("", self)
        self._subtitle.setProperty("role", "tertiary")
        self._subtitle.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('caption')['size_sp']))}px;"
        )
        self._subtitle.hide()
        title_box.addWidget(self._subtitle)
        layout.addLayout(title_box)
        layout.addStretch(1)
        self._search = SearchField(S.SEARCH_PLACEHOLDER, show_mic=False, parent=self)
        self._search.setMaximumWidth(theme.px(380))
        self._search.submitted.connect(self.search_submitted)
        layout.addWidget(self._search, 1)
        self._history_requested = isinstance(repo, DemoRepository)
        history = self._continue_entry() if self._history_requested else None
        self._has_continue = history is not None
        self._continue = ContinueChip(history, parent=self)
        self._continue.play_clicked.connect(self.continue_play)
        self._continue.close_clicked.connect(self._hide_continue)
        self._continue.setVisible(bool(show_continue and history))
        layout.addWidget(self._continue)
        self._create = IconButton("plus", size=20, tooltip=S.TOOLTIP_CREATE, parent=self)
        self._create.clicked.connect(self._create_menu)
        layout.addWidget(self._create)
        self._refresh = IconButton("refresh", size=20, tooltip=S.TOOLTIP_REFRESH, parent=self)
        self._refresh.clicked.connect(self.refresh_clicked)
        layout.addWidget(self._refresh)
        self._theme = IconButton("moon", size=20, tooltip=S.TOOLTIP_THEME, parent=self)
        self._theme.clicked.connect(self.theme_clicked)
        layout.addWidget(self._theme)
        self._notifications = NotificationButton(parent=self)
        self._notifications.set_count(0)
        self._notifications.clicked.connect(self.notifications_clicked)
        layout.addWidget(self._notifications)
        self._settings = IconButton("settings", size=20, tooltip=S.TOOLTIP_SETTINGS, parent=self)
        self._settings.clicked.connect(self.settings_clicked)
        layout.addWidget(self._settings)
        self._avatar = AvatarButton(parent=self)
        self._avatar.clicked.connect(self.profile_clicked)
        layout.addWidget(self._avatar)
        self._sync_theme_icon()
        active_theme().changed.connect(self._sync_theme_icon)

    def _continue_entry(self) -> HistoryEntry | None:
        try:
            page = self._repo.fetch_history(1, 1)
            return page.items[0] if page.items else None
        except Exception:
            return None

    def _hide_continue(self) -> None:
        self._continue.hide()
        self.continue_hidden.emit()

    def _create_menu(self) -> None:
        menu = QMenu(self)
        article = menu.addAction(S.FEED_CREATE_ARTICLE)
        channel = menu.addAction(S.FEED_CREATE_CHANNEL)
        chosen = menu.exec(self._create.mapToGlobal(self._create.rect().bottomLeft()))
        if chosen == article:
            self.create_article.emit()
        elif chosen == channel:
            self.create_channel.emit()

    def _sync_theme_icon(self) -> None:
        theme = active_theme()
        self._theme.set_icon("sun" if theme.dark else "moon")

    def set_header(self, title: str, subtitle: str = "") -> None:
        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._sync_responsive_visibility()

    def set_navigation(self, can_back: bool, can_forward: bool) -> None:
        self._back.setEnabled(can_back)
        self._forward.setEnabled(can_forward)

    def set_search_text(self, text: str) -> None:
        self._search.blockSignals(True)
        self._search.setText(text)
        self._search.blockSignals(False)

    def set_search_visible(self, visible: bool) -> None:
        self._search.setVisible(visible)

    def focus_search(self) -> None:
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()

    @Slot(object)
    def _set_continue_entry(self, entry: HistoryEntry | None) -> None:
        if entry is None or not self._repo.is_authenticated:
            return
        old = self._continue
        self._continue = ContinueChip(entry, parent=self)
        self.layout().replaceWidget(old, self._continue)
        old.hide()
        old.deleteLater()
        self._continue.play_clicked.connect(self.continue_play)
        self._continue.close_clicked.connect(self._hide_continue)
        self._has_continue = True
        self._sync_responsive_visibility()

    def refresh_continue(self, visible: bool) -> None:
        if visible and not self._history_requested and self._repo.is_authenticated:
            self._history_requested = True
            job = _HistoryJob(self._repo)
            job.signals.loaded.connect(self._set_continue_entry, Qt.ConnectionType.QueuedConnection)
            QThreadPool.globalInstance().start(job)
        self._show_continue_setting = visible
        self._sync_responsive_visibility()

    def refresh_notifications(self) -> None:
        try:
            count = sum(1 for item in self._repo.fetch_notifications("all") if item.is_new)
        except Exception:
            count = 0
        self._notifications.set_count(count)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_responsive_visibility()

    def _sync_responsive_visibility(self) -> None:
        theme = active_theme()
        self._continue.setVisible(
            self._show_continue_setting and self._has_continue and self.width() > theme.px(1350)
        )
        self._subtitle.setVisible(bool(self._subtitle.text()) and self.width() >= theme.px(1200))


class SnackBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setStyleSheet(
            f"background-color: {theme.color('snackbar_background')};"
            f"border-radius: {theme.radius('dialog')}px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.space("l"), theme.space("sm"), theme.space("l"), theme.space("sm"))
        self._label = QLabel("", self)
        self._label.setStyleSheet(f"color: {theme.color('badge_text')};")
        layout.addWidget(self._label)
        self._refresh_style()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.hide()
        active_theme().changed.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        theme = active_theme()
        self.setStyleSheet(
            f"background-color: {theme.color('snackbar_background')};"
            f"border-radius: {theme.radius('dialog')}px;"
        )
        self._label.setStyleSheet(f"color: {theme.color('badge_text')};")

    def show_message(self, text: str, duration: int = 2600) -> None:
        self._label.setText(text)
        self.adjustSize()
        self.setFixedWidth(min(560, max(260, self._label.sizeHint().width() + 48)))
        self.show()
        self.raise_()
        self._timer.start(duration)
