"""Application bootstrap, main window, routing and the headless smoke test."""

from __future__ import annotations

import os
import sys
from typing import Any

from pathlib import Path

from PySide6.QtCore import QEvent, QStandardPaths, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .connector_adapter import create_repository
from .data import DemoRepository, DemoState, Repository
from .screens import (
    ArticleEditorScreen,
    ArticleScreen,
    ArticlesScreen,
    AuthScreen,
    BadgesScreen,
    BookmarksScreen,
    ChannelManageScreen,
    ChannelScreen,
    ChannelsScreen,
    CollectionScreen,
    CollectionsScreen,
    CommentsScreen,
    DeletionScreen,
    DiscoverScreen,
    EmailAuthScreen,
    EpisodesScreen,
    FilterScreen,
    HealthScreen,
    HistoryScreen,
    HomeScreen,
    ListScreen,
    NeedAuthScreen,
    NotificationsScreen,
    PlayerScreen,
    ProfileScreen,
    QrAuthScreen,
    RegistrationScreen,
    ReleaseScreen,
    RestoreScreen,
    ScheduleScreen,
    ScreenContext,
    SearchScreen,
    SettingsScreen,
    SocialFeedScreen,
    UpdatesScreen,
)
from .session_store import FileTokenStore
from .shell import Sidebar, SnackBar, TopBar
from .state import AppSettings
from .strings import S
from .theme import ThemeManager
from .timers import single_shot
from .tokens import Tokens
from .widgets.dialogs import ComposeArticleDialog, ComposeChannelDialog


def _search_focus_delay() -> int:
    return 0 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 250


class MainWindow(QMainWindow):
    """Shell that owns the sidebar, top bar, back stack and screen routing."""

    def __init__(
        self,
        repo: Repository,
        theme: ThemeManager,
        settings: AppSettings,
        tokens: Tokens,
    ) -> None:
        super().__init__()
        self.repo = repo
        self._demo = isinstance(repo, DemoRepository)
        self.theme = theme
        self.settings = settings
        self.tokens = tokens
        self._current_route: str | None = None
        self._current_payload: Any = None
        self._current_screen = None
        self._back: list[tuple[str, Any]] = []
        self._forward: list[tuple[str, Any]] = []
        self._player_fullscreen = False
        self._fullscreen_was_maximized = False
        self._fullscreen_geometry = None
        self.setWindowTitle(S.APP_NAME)
        self.setMinimumSize(1100, 700)
        self.resize(tokens.desktop("target_window_width_px"), 800)
        self.setWindowIcon(QIcon(icons.logo_pixmap(64)))

        central = QWidget(self)
        central.setProperty("ui", "appRoot")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = Sidebar(compact=settings.compact_sidebar, parent=central)
        self.sidebar.navigate.connect(self._on_sidebar_navigate)
        self.sidebar.compact_requested.connect(self._on_compact_requested)
        root.addWidget(self.sidebar, 0)
        right = QWidget(central)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.topbar = TopBar(repo, show_continue=settings.continue_watching, parent=right)
        self._wire_topbar()
        right_layout.addWidget(self.topbar, 0)
        self.content_stack = QStackedWidget(right)
        right_layout.addWidget(self.content_stack, 1)
        root.addWidget(right, 1)
        self.setCentralWidget(central)
        self.snackbar = SnackBar(self)
        self._install_shortcuts()
        if hasattr(repo, "subscribe_state"):
            repo.subscribe_state(self._on_demo_state)  # type: ignore[attr-defined]
        self._show("home" if self._has_session() else "auth_email", None)
        self._refresh_shell(fetch_notifications=False)

    # ------------------------------------------------------------------ AppHost
    def _has_session(self) -> bool:
        return self._demo or self.repo.is_authenticated

    def navigate(self, route: str, payload: Any = None, *, push: bool = True) -> None:
        if not self._demo and (not self._has_session() or self._current_route == "auth_email"):
            self._back.clear()
            self._forward.clear()
            push = False
            if not self._has_session():
                route, payload = "auth_email", None
                if route == self._current_route:
                    return
        if route == self._current_route and payload == self._current_payload:
            self.reload_current()
            return
        if push and self._current_route is not None:
            self._back.append((self._current_route, self._current_payload))
            self._forward.clear()
        self._show(route, payload)
        self._refresh_shell()

    def set_player_fullscreen(self, enabled: bool) -> None:
        """Full-screen playback: the player page fills the screen without shell."""

        if enabled == self._player_fullscreen:
            return
        self._player_fullscreen = enabled
        if enabled:
            self._fullscreen_was_maximized = self.isMaximized()
            self._fullscreen_geometry = self.geometry()
            self.topbar.hide()
            self.sidebar.hide()
            self.showFullScreen()
            return
        self.topbar.show()
        self.sidebar.show()
        self.showNormal()
        if self._fullscreen_geometry is not None:
            self.setGeometry(self._fullscreen_geometry)
            self._fullscreen_geometry = None
        if self._fullscreen_was_maximized:
            self.showMaximized()
        self._refresh_shell()

    def go_back(self) -> None:
        if not self._has_session():
            self.navigate("auth_email")
            return
        if not self._back:
            return
        target = self._back.pop()
        if self._current_route is not None:
            self._forward.append((self._current_route, self._current_payload))
        self._show(*target)
        self._refresh_shell()

    def go_forward(self) -> None:
        if not self._has_session():
            self.navigate("auth_email")
            return
        if not self._forward:
            return
        target = self._forward.pop()
        if self._current_route is not None:
            self._back.append((self._current_route, self._current_payload))
        self._show(*target)
        self._refresh_shell()

    def set_header(self, title: str, subtitle: str = "") -> None:
        self.topbar.set_header(title, subtitle)

    def show_snackbar(self, text: str) -> None:
        self.snackbar.show_message(text)
        self._position_snackbar()

    def reload_current(self) -> None:
        if self._current_screen is not None:
            self._current_screen.reload()
        self._refresh_shell()

    def apply_compact_sidebar(self, compact: bool) -> None:
        self.settings.compact_sidebar = compact
        self.sidebar.set_compact(compact)

    def apply_continue_watching(self, enabled: bool) -> None:
        self.settings.continue_watching = enabled
        self.topbar.refresh_continue(enabled)

    def open_theme_toggle(self) -> None:
        self.cycle_theme()

    # ---------------------------------------------------------------- internals
    def _wire_topbar(self) -> None:
        self.topbar.back_clicked.connect(self.go_back)
        self.topbar.forward_clicked.connect(self.go_forward)
        self.topbar.search_submitted.connect(self.open_search)
        self.topbar.refresh_clicked.connect(self.reload_current)
        self.topbar.theme_clicked.connect(self.cycle_theme)
        self.topbar.notifications_clicked.connect(lambda: self.navigate("notifications"))
        self.topbar.settings_clicked.connect(lambda: self.navigate("settings"))
        self.topbar.profile_clicked.connect(lambda: self.navigate("profile"))
        self.topbar.create_article.connect(self._create_article)
        self.topbar.create_channel.connect(self._create_channel)
        self.topbar.continue_play.connect(self._continue_watching)
        self.topbar.continue_hidden.connect(self._hide_continue)

    def _install_shortcuts(self) -> None:
        def bind(sequence: str, handler) -> None:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)

        bind("Ctrl+K", self._focus_global_search)
        bind("Ctrl+F", self._focus_global_search)
        bind("Esc", self._escape)
        bind("Alt+Left", self.go_back)
        bind("Alt+Right", self.go_forward)
        bind("F5", self.reload_current)
        bind("Ctrl+R", self.reload_current)
        bind("Ctrl+Shift+F", lambda: self.navigate("filter"))
        for index, route in enumerate(("home", "discover", "bookmarks", "feed"), start=1):
            bind(f"Ctrl+{index}", lambda _checked=False, r=route: self.navigate(r))

    def _escape(self) -> None:
        screen = self._current_screen
        if screen is not None and screen.handle_escape():
            return
        self.go_back()

    def _on_sidebar_navigate(self, route: str) -> None:
        self.navigate(route, push=True)

    def _on_compact_requested(self, compact: bool) -> None:
        self.settings.compact_sidebar = compact
        self._position_snackbar()

    def _focus_global_search(self) -> None:
        if self._current_route == "search" and self._current_screen is not None:
            self._current_screen.focus_search()
            return
        self.navigate("search", {"query": ""})
        single_shot(
            self,
            _search_focus_delay(),
            self._focus_search_screen,
        )

    def _focus_search_screen(self) -> None:
        if self._current_route == "search" and self._current_screen is not None:
            self._current_screen.focus_search()

    def open_search(self, query: str) -> None:
        self.topbar.set_search_text(query)
        if self._current_route == "search" and self._current_screen is not None:
            # set_payload refreshes only the results area; no screen rebuild.
            set_payload = getattr(self._current_screen, "set_payload", None)
            if callable(set_payload):
                set_payload({"query": query})
            single_shot(
                self,
                _search_focus_delay(),
                self._focus_search_screen,
            )
            return
        self.navigate("search", {"query": query})
        single_shot(
            self,
            _search_focus_delay(),
            self._focus_search_screen,
        )

    def cycle_theme(self) -> None:
        mode = "light" if self.theme.dark else "dark"
        self.settings.theme_mode = mode
        self.theme.set_mode(mode)
        self._refresh_shell()

    def _refresh_shell(self, *, fetch_notifications: bool = True) -> None:
        self.topbar.set_navigation(bool(self._back), bool(self._forward))
        if self._current_route:
            self.sidebar.set_active(self._current_route)
        if not self._has_session():
            return
        self.topbar.refresh_continue(self.settings.continue_watching)
        if not fetch_notifications:
            return
        try:
            self.topbar.refresh_notifications()
        except Exception:
            pass

    def _hide_continue(self) -> None:
        self.settings.continue_watching = False
        self.topbar.refresh_continue(False)
        self.show_snackbar(S.HOME_CONTINUE_HIDE)

    def _continue_watching(self) -> None:
        try:
            page = self.repo.fetch_history(1, 1)
        except Exception:
            return
        if not page.items:
            return
        entry = page.items[0]
        episodes = self.repo.fetch_episodes(entry.release.id)
        episode = next((item for item in episodes if item.title == entry.episode_name), episodes[0] if episodes else None)
        self.navigate(
            "player",
            {
                "release_id": entry.release.id,
                "episode_id": episode.id if episode else 0,
                "title": entry.release.title,
                "episode": entry.episode_name,
            },
        )

    def _create_article(self) -> None:
        self.navigate("article_editor")

    def _create_channel(self) -> None:
        dialog = ComposeChannelDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.show_snackbar(S.CHANNELS_CREATED)
            self.reload_current()

    def _on_demo_state(self, state: DemoState) -> None:
        self.settings.demo_state = state

    # ------------------------------------------------------------------ routing
    @staticmethod
    def _payload_id(payload: Any, default: int) -> int:
        if isinstance(payload, dict):
            value = payload.get("id", payload.get("release_id", default))
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        if isinstance(payload, (int, str)):
            try:
                return int(payload)
            except (TypeError, ValueError):
                return default
        return default

    def _create_screen(self, route: str, payload: Any):
        ctx = ScreenContext(repo=self.repo, theme=self.theme, host=self, settings=self.settings)
        if route == "home":
            return HomeScreen(ctx)
        if route == "discover":
            return DiscoverScreen(ctx)
        if route == "bookmarks":
            return BookmarksScreen(ctx)
        if route == "feed":
            return SocialFeedScreen(ctx)
        if route == "search":
            screen = SearchScreen(ctx)
            screen.set_payload(payload or {"query": ""})
            return screen
        if route == "filter":
            screen = FilterScreen(ctx)
            screen.set_payload(payload or {})
            return screen
        if route == "release":
            return ReleaseScreen(ctx, self._payload_id(payload, 1000))
        if route == "episodes":
            return EpisodesScreen(ctx, self._payload_id(payload, 1000))
        if route == "player":
            return PlayerScreen(ctx, payload if isinstance(payload, dict) else None)
        if route == "profile":
            return ProfileScreen(ctx, payload if isinstance(payload, int) else None)
        if route == "notifications":
            return NotificationsScreen(ctx)
        if route == "collections":
            return CollectionsScreen(ctx)
        if route == "collection":
            return CollectionScreen(ctx, self._payload_id(payload, 2000))
        if route == "history":
            return HistoryScreen(ctx)
        if route == "settings":
            screen = SettingsScreen(ctx)
            screen.set_payload(payload or {})
            return screen
        if route == "auth":
            screen = AuthScreen(ctx)
            screen.set_payload(payload or {})
            return screen
        if route == "auth_email":
            return EmailAuthScreen(ctx)
        if route == "auth_register":
            return RegistrationScreen(ctx)
        if route == "auth_restore":
            return RestoreScreen(ctx)
        if route == "auth_qr":
            return QrAuthScreen(ctx)
        if route == "badges":
            return BadgesScreen(ctx)
        if route == "release_badges":
            return BadgesScreen(ctx, self._payload_id(payload, 1000))
        if route == "health":
            return HealthScreen(ctx)
        if route == "deletion":
            return DeletionScreen(ctx)
        if route == "channels":
            return ChannelsScreen(ctx)
        if route == "channel":
            return ChannelScreen(ctx, self._payload_id(payload, 3000))
        if route == "channel_manage":
            return ChannelManageScreen(ctx, self._payload_id(payload, 3000))
        if route == "articles":
            return ArticlesScreen(ctx)
        if route == "article":
            return ArticleScreen(ctx, self._payload_id(payload, 4000))
        if route == "article_editor":
            return ArticleEditorScreen(ctx)
        if route == "schedule":
            return ScheduleScreen(ctx)
        if route == "updates":
            return UpdatesScreen(ctx)
        if route == "comments":
            return CommentsScreen(ctx, payload if isinstance(payload, dict) else None)
        if route == "list":
            return ListScreen(ctx, payload if isinstance(payload, dict) else None)
        if route == "need_auth":
            return NeedAuthScreen(ctx)
        return HomeScreen(ctx)

    def _show(self, route: str, payload: Any) -> None:
        if route != "player" and self._player_fullscreen:
            self.set_player_fullscreen(False)
        show_shell = self._has_session() and not self._player_fullscreen
        self.topbar.setVisible(show_shell)
        self.sidebar.setVisible(show_shell)
        screen = self._create_screen(route, payload)
        previous = self.content_stack.currentWidget()
        self.content_stack.addWidget(screen)
        self.content_stack.setCurrentWidget(screen)
        self._current_screen = screen
        self._current_route = route
        self._current_payload = payload
        self.topbar.set_search_visible(route != "search")
        if previous is not None:
            self.content_stack.removeWidget(previous)
            previous.deleteLater()
        self.sidebar.set_active(route)
        screen.on_enter()
        if route == "search":
            single_shot(
                self,
                _search_focus_delay(),
                self._focus_search_screen,
            )

    # ------------------------------------------------------------------ geometry
    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self.settings.compact_sidebar:
            self.sidebar.set_compact(self.width() < self.theme.px(1100))
        self._position_snackbar()

    def _position_snackbar(self) -> None:
        if not hasattr(self, "snackbar"):
            return
        bar = self.snackbar
        bar.adjustSize()
        x = max(0, (self.width() - bar.width()) // 2)
        y = max(0, self.height() - bar.height() - self.theme.space("xl"))
        bar.move(x, y)
        bar.raise_()


SMOKE_ROUTES: tuple[tuple[str, Any], ...] = (
    ("home", None),
    ("discover", None),
    ("bookmarks", None),
    ("feed", None),
    ("search", {"query": "лунный"}),
    ("filter", {}),
    ("release", 1000),
    ("episodes", 1000),
    ("player", {"release_id": 1000, "episode_id": 1, "title": "Лунный странник", "episode": "Серия 1"}),
    ("profile", None),
    ("badges", None),
    ("release_badges", 1000),
    ("notifications", None),
    ("collections", None),
    ("collection", 2000),
    ("history", None),
    ("channels", None),
    ("channel", 3000),
    ("channel_manage", 3000),
    ("articles", None),
    ("article", 4000),
    ("article_editor", None),
    ("schedule", None),
    ("updates", None),
    ("comments", {"kind": "release", "id": 1000, "title": "Лунный странник"}),
    ("list", {"kind": "recommended", "title": S.DISCOVER_RECOMMENDATIONS}),
    ("settings", None),
    ("auth", None),
    ("auth_email", None),
    ("auth_register", None),
    ("auth_restore", None),
    ("auth_qr", None),
    ("health", None),
    ("deletion", None),
    ("need_auth", None),
)


def run_smoke_test(window: MainWindow, app: QApplication) -> int:
    """Exercise every route and state without entering the event loop."""

    def drain() -> None:
        for _ in range(5):
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    window.show()
    drain()
    errors: list[str] = []
    for mode in ("light", "dark"):
        window.theme.set_mode(mode)
        drain()
        for route, payload in SMOKE_ROUTES:
            window.navigate(route, payload, push=False)
            drain()
            screen = window.content_stack.currentWidget()
            error = getattr(screen, "_last_load_error", None)
            if error is not None:
                errors.append(f"{mode}/{route}: {error!r}")
            if screen is None or not screen.isVisible() or screen.rect().isEmpty():
                errors.append(f"{mode}/{route}: no visible content")
    # Demo states.
    if hasattr(window.repo, "set_demo_state"):
        for state in (DemoState.EMPTY, DemoState.ERROR, DemoState.LOADING, DemoState.DATA):
            window.repo.set_demo_state(state)  # type: ignore[attr-defined]
            window._show("home", None)
            drain()
            error = getattr(window._current_screen, "_last_load_error", None)
            if error is not None:
                errors.append(f"state {state}: {error!r}")
    # Theme re-application.
    window.theme.set_mode("dark")
    drain()
    window.theme.set_mode("light")
    drain()
    window.close()
    drain()
    if errors:
        for message in errors:
            print("smoke-test error:", message, file=sys.stderr)
        return 1
    print(f"smoke-test OK: {len(SMOKE_ROUTES)} routes, light/dark themes, demo states")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    smoke = "--smoke-test" in args
    args = [arg for arg in args if arg != "--smoke-test"]
    if smoke:
        os.environ["ANX_UI_SMOKE_TEST"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(args)
    app.setOrganizationName("anx-desktop")
    legacy_directory = ""
    if not smoke:
        app.setApplicationName("Anixart")  # Discover the old Qt session path before renaming.
        legacy_directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    app.setApplicationName(S.APP_NAME)
    app.setApplicationDisplayName(S.APP_NAME)
    try:
        token_store = Tokens.load()
    except Exception as exc:
        print(f"anx-desktop: {exc}", file=sys.stderr)
        return 1
    theme = ThemeManager(app, token_store)
    settings = AppSettings()
    theme.set_mode(settings.theme_mode)
    try:
        if smoke:
            repo = DemoRepository()
        else:
            directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
            if not directory:
                raise RuntimeError("Не удалось определить папку для сохранения сессии")
            session = FileTokenStore(Path(directory) / "session.json")
            if legacy_directory:
                try:
                    session.migrate_from(Path(legacy_directory) / "session.json")
                except OSError as exc:
                    print(f"anx-desktop: не удалось перенести старую сессию ({type(exc).__name__})", file=sys.stderr)
            repo = create_repository(token_store=session)
            settings.home_tab = "home_1"
    except RuntimeError as exc:
        QMessageBox.critical(None, S.APP_NAME, str(exc))
        return 1
    window = MainWindow(repo, theme, settings, token_store)
    if smoke:
        return run_smoke_test(window, app)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
