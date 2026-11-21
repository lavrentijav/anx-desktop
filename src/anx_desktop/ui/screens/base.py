"""Base screen: top-level header context plus loading/empty/error/content states."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..data import DemoRepositoryError, Repository, DemoState
from ..state import AppSettings
from ..strings import S
from ..theme import ThemeManager, active_theme
from ..widgets.empty_state import EmptyState, ErrorState, LoadingState
from ..widgets.util import clear_layout


class AppHost(Protocol):
    settings: AppSettings

    def navigate(self, route: str, payload: Any = None, *, push: bool = True) -> None: ...

    def go_back(self) -> None: ...

    def set_header(self, title: str, subtitle: str = "") -> None: ...

    def show_snackbar(self, text: str) -> None: ...

    def reload_current(self) -> None: ...

    def set_player_fullscreen(self, enabled: bool) -> None: ...

    def apply_compact_sidebar(self, compact: bool) -> None: ...

    def apply_continue_watching(self, enabled: bool) -> None: ...

    def open_theme_toggle(self) -> None: ...


@dataclass
class ScreenContext:
    repo: Repository
    theme: ThemeManager
    host: AppHost
    settings: AppSettings


class BaseScreen(QWidget):
    """Shared scaffold for both dynamic and static screens."""

    auto_load = True
    supports_empty = True

    def __init__(
        self,
        ctx: ScreenContext,
        *,
        title: str = "",
        subtitle: str = "",
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.theme = ctx.theme
        self.repo = ctx.repo
        self.settings = ctx.settings
        self.title = title
        self.subtitle = subtitle
        self._activated = False
        self._token = 0
        self._loading_page: QWidget | None = None
        self._empty_page: QWidget | None = None
        self._error_page: QWidget | None = None
        self._content_built = False
        self._has_content = False
        self._last_load_error: Exception | None = None
        self._pending_token = 0
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._finish_pending_load)
        self.setProperty("ui", "screen")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.stack = QStackedWidget(self)
        root.addWidget(self.stack, 1)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_host = QWidget()
        self.content_host.setProperty("ui", "scrollHost")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.scroll.setWidget(self.content_host)
        self.stack.addWidget(self.scroll)

    # --------------------------------------------------------------- lifecycle
    def activate(self) -> None:
        self.ctx.host.set_header(self.title, self.subtitle)
        if not self._activated:
            self._activated = True
            self.reload()
        elif not self._content_built and self.auto_load:
            self.reload()

    def on_enter(self) -> None:
        """Called by the router each time the screen becomes visible."""

        if not self._activated:
            self.activate()
        else:
            self.ctx.host.set_header(self.title, self.subtitle)

    def reload(self) -> None:
        self._token += 1
        token = self._token
        self._last_load_error = None
        if not self.auto_load:
            try:
                self.populate()
            except DemoRepositoryError:
                self.show_error()
                return
            except Exception as exc:  # pragma: no cover - defensive UI guard
                self._last_load_error = exc
                traceback.print_exc()
                self.show_error()
                return
            self.show_content()
            return
        self.show_loading()
        state = self._demo_state()
        if state == DemoState.LOADING:
            delay = 60_000
        else:
            delay = 0 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 180
        self._pending_token = token
        self._load_timer.stop()
        self._load_timer.start(delay)

    def _finish_pending_load(self) -> None:
        # The timer is parented to the screen, so it cannot fire after the
        # screen's C++ object has been deleted during a fast route change.
        self._finish_load(self._pending_token)

    def _finish_load(self, token: int) -> None:
        if token != self._token:
            return
        if self._demo_state() == DemoState.LOADING:
            return
        if self._demo_state() == DemoState.ERROR:
            self.show_error()
            return
        try:
            self.populate()
        except DemoRepositoryError:
            self.show_error()
            return
        except Exception as exc:  # pragma: no cover - defensive UI guard
            self._last_load_error = exc
            traceback.print_exc()
            self.show_error()
            return
        self._content_built = True
        self._has_content = True
        if (self.supports_empty and self._demo_state() == DemoState.EMPTY) or self.is_empty_result():
            self.show_empty()
        else:
            self.show_content()

    def _demo_state(self) -> DemoState:
        getter = getattr(self.repo, "demo_state", DemoState.DATA)
        if isinstance(getter, DemoState):
            return getter
        return DemoState(getter)

    # ------------------------------------------------------------------- pages
    def show_loading(self) -> None:
        page = self._ensure_loading_page()
        self.stack.setCurrentWidget(page)

    def show_content(self) -> None:
        self.stack.setCurrentWidget(self.scroll)

    def show_empty(self) -> None:
        page = self._ensure_empty_page()
        self.stack.setCurrentWidget(page)

    def show_error(self) -> None:
        page = self._ensure_error_page()
        self.stack.setCurrentWidget(page)

    def _ensure_loading_page(self) -> QWidget:
        if self._loading_page is None:
            self._loading_page = self.create_loading_page()
            self.stack.addWidget(self._loading_page)
        return self._loading_page

    def _ensure_empty_page(self) -> QWidget:
        if self._empty_page is None:
            self._empty_page = self.create_empty_page()
            self.stack.addWidget(self._empty_page)
        return self._empty_page

    def _ensure_error_page(self) -> QWidget:
        if self._error_page is None:
            self._error_page = self.create_error_page()
            self.stack.addWidget(self._error_page)
        return self._error_page

    # --------------------------------------------------------------- overrides
    def create_loading_page(self) -> QWidget:
        return LoadingState(parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(parent=self)
        return page

    def create_error_page(self) -> QWidget:
        page = ErrorState(parent=self)
        page.retry_clicked.connect(self.reload)
        page.help_clicked.connect(self._show_help)
        return page

    def populate(self) -> None:
        """Rebuild content.  Must be idempotent."""

    def is_empty_result(self) -> bool:
        """Return True when successfully loaded data should show the empty state."""

        return False

    def focus_search(self) -> None:
        pass

    def handle_escape(self) -> bool:
        """Return True if the screen consumed Escape (e.g. exits fullscreen)."""

        return False

    # ----------------------------------------------------------------- helpers
    def reset_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            layout = item.layout()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif layout is not None:
                clear_layout(layout)
        self._content_built = False

    def add_content(self, widget: QWidget, stretch: int = 0) -> None:
        self.content_layout.addWidget(widget, stretch)

    def add_layout(self, layout, stretch: int = 0) -> None:
        self.content_layout.addLayout(layout, stretch)

    def add_stretch(self, stretch: int = 1) -> None:
        self.content_layout.addStretch(stretch)

    def scroll_to_top(self) -> None:
        self.scroll.verticalScrollBar().setValue(0)

    def make_intro(
        self,
        title: str,
        subtitle: str = "",
        *,
        actions: list[QWidget] | None = None,
    ) -> QWidget:
        """Content intro block (screen title already lives in the top bar)."""

        theme = self.theme
        host = QWidget()
        layout = QHBoxLayout(host)
        h = theme.semantic("screen_gutter")
        layout.setContentsMargins(h, theme.space("xl"), h, theme.space("m"))
        layout.setSpacing(theme.space("m"))
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        title_label = QLabel(title)
        title_label.setProperty("role", "title")
        title_label.setWordWrap(True)
        text.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("role", "muted")
            subtitle_label.setWordWrap(True)
            text.addWidget(subtitle_label)
        layout.addLayout(text, 1)
        for action in actions or []:
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)
        return host

    def make_action_button(self, text: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("ui", "primary" if primary else "outlined")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def notify(self, text: str) -> None:
        self.ctx.host.show_snackbar(text)

    def open_route(self, route: str, payload: Any = None, *, push: bool = True) -> None:
        self.ctx.host.navigate(route, payload, push=push)

    def _show_help(self) -> None:
        from ..widgets.dialogs import MessageDialog

        MessageDialog(S.HELP, S.HELP_TEXT, parent=self).exec()

    def section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "section")
        label.setContentsMargins(
            self.theme.semantic("screen_gutter"), self.theme.space("m"), 0, self.theme.space("sm")
        )
        return label

    def muted_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "muted")
        label.setWordWrap(True)
        return label
