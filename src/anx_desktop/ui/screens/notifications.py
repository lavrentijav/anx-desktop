"""Уведомления: filters, read/delete actions and typed rows."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import NotificationItem
from ..formatting import format_date
from ..strings import S
from ..theme import active_theme
from ..widgets import Avatar, EmptyState, IconButton, SkeletonList, TextBadge
from ..widgets.dialogs import ConfirmDialog
from .base import BaseScreen


_ICON_FOR_KIND = {
    "episode": "list",
    "release": "star",
    "article": "article",
    "reply": "comment",
    "friend": "user",
    "achievement": "badge",
}
_FILTER_KEYS = ("all", "episodes", "releases", "articles", "friends", "replies")


class NotificationRow(QFrame):
    clicked = Signal(int)
    context_requested = Signal(int, object)

    def __init__(self, item: NotificationItem, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.item = item
        self._spoiler_open = False
        self.setProperty("ui", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(theme.px(78))
        layout = QHBoxLayout(self)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.semantic("notification_icon_gap"))
        icon_host = QFrame(self)
        icon_host.setFixedSize(theme.semantic("list_avatar_size"), theme.semantic("list_avatar_size"))
        icon_host.setStyleSheet(
            f"background-color: {theme.color('surface_tertiary')};"
            f"border-radius: {theme.radius('tag')}px;"
        )
        icon_layout = QVBoxLayout(icon_host)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon = QLabel(icon_host)
        icon.setPixmap(icons.pixmap(_ICON_FOR_KIND.get(item.kind, "bell"), "icon_alt", 22))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon)
        layout.addWidget(icon_host, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        title = QLabel(item.title, self)
        title.setStyleSheet("font-weight: 600;")
        title.setWordWrap(True)
        text.addWidget(title)
        if item.spoiler and not self._spoiler_open:
            spoiler = QFrame(self)
            spoiler.setProperty("ui", "tertiary")
            spoiler_layout = QVBoxLayout(spoiler)
            spoiler_layout.setContentsMargins(theme.space("sm"), theme.space("sm"), theme.space("sm"), theme.space("sm"))
            hint = QLabel(S.NOTIFICATIONS_SPOILER, spoiler)
            hint.setProperty("role", "tertiary")
            hint.setWordWrap(True)
            spoiler_layout.addWidget(hint)
            reveal = QPushButton(S.NOTIFICATIONS_SHOW, spoiler)
            reveal.setProperty("ui", "text")
            reveal.clicked.connect(self._open_spoiler)
            spoiler_layout.addWidget(reveal, 0, Qt.AlignmentFlag.AlignLeft)
            text.addWidget(spoiler)
        else:
            message = QLabel(item.message, self)
            message.setProperty("role", "muted")
            message.setWordWrap(True)
            text.addWidget(message)
        date = QLabel(format_date(item.timestamp), self)
        date.setProperty("role", "tertiary")
        text.addWidget(date)
        layout.addLayout(text, 1)
        if item.is_new:
            dot = QLabel(self)
            dot.setPixmap(icons.pixmap("dot", "badge", 8))
            layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
        more = IconButton("more", size=18, tooltip=S.TOOLTIP_MORE, parent=self)
        more.clicked.connect(lambda: self.context_requested.emit(item.id, more.mapToGlobal(more.rect().bottomLeft())))
        layout.addWidget(more, 0, Qt.AlignmentFlag.AlignTop)

    def _open_spoiler(self) -> None:
        self._spoiler_open = True
        # Rebuild by asking the screen to reload; simple and deterministic.
        self.clicked.emit(self.item.id)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item.id)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.context_requested.emit(self.item.id, event.globalPos())
        event.accept()


class NotificationsScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NOTIFICATIONS_TITLE)
        self._filter = ctx.settings.notification_filter
        self._items: tuple[NotificationItem, ...] = ()
        self._list_layout: QVBoxLayout | None = None
        self._count_label: QLabel | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        return EmptyState(
            S.EMPTY_NOTIFICATIONS,
            S.NOTIFICATIONS_EMPTY_HINT,
            icon_name="bell",
            parent=self,
        )

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        items = self.repo.fetch_notifications(self._filter)
        self._items = items
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("sm"))
        self._count_label = QLabel(S.HOME_COUNT.format(count=len(items)), toolbar)
        self._count_label.setProperty("role", "uppercase")
        row.addWidget(self._count_label)
        row.addStretch(1)
        filter_combo = QComboBox(toolbar)
        filter_combo.addItems(S.NOTIFICATION_FILTERS)
        index = _FILTER_KEYS.index(self._filter) if self._filter in _FILTER_KEYS else 0
        filter_combo.setCurrentIndex(index)
        filter_combo.currentIndexChanged.connect(self._on_filter)
        row.addWidget(filter_combo)
        settings = QPushButton(S.SETTINGS, toolbar)
        settings.setProperty("ui", "grey")
        settings.clicked.connect(lambda: self.open_route("settings", {"section": S.SETTINGS_NOTIFICATIONS}))
        row.addWidget(settings)
        clear = QPushButton(S.NOTIFICATIONS_DELETE_ALL, toolbar)
        clear.setProperty("ui", "danger")
        clear.clicked.connect(self._delete_all)
        row.addWidget(clear)
        self.add_content(toolbar)
        host = QWidget(self)
        self._list_layout = QVBoxLayout(host)
        self._list_layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        self._list_layout.setSpacing(theme.space("sm"))
        if not items:
            self._list_layout.addWidget(EmptyState(S.EMPTY_NOTIFICATIONS, S.NOTIFICATIONS_EMPTY_HINT, parent=host))
        for item in items:
            row_widget = NotificationRow(item, parent=host)
            row_widget.clicked.connect(self._open_item)
            row_widget.context_requested.connect(self._context)
            self._list_layout.addWidget(row_widget)
        self.add_content(host, 1)
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return not self._items

    def _on_filter(self, index: int) -> None:
        if 0 <= index < len(_FILTER_KEYS):
            self._filter = _FILTER_KEYS[index]
            self.settings.notification_filter = self._filter
            self.reload()

    def _open_item(self, item_id: int) -> None:
        item = next((item for item in self._items if item.id == item_id), None)
        if item is None:
            return
        if hasattr(self.repo, "mark_notification_read"):
            self.repo.mark_notification_read(item.id)  # type: ignore[attr-defined]
        target_routes = {
            "release": ("release", item.target_id),
            "article": ("article", item.target_id),
            "profile": ("profile", None),
        }
        route, payload = target_routes.get(item.target_kind, ("release", item.target_id))
        if item.kind == "achievement":
            route, payload = "badges", None
        self.open_route(route, payload)

    def _context(self, item_id: int, pos) -> None:
        menu = QMenu(self)
        read = menu.addAction(S.NOTIFICATIONS_MARK_READ)
        delete = menu.addAction(S.DELETE)
        chosen = menu.exec(pos)
        if chosen == read:
            if hasattr(self.repo, "mark_notification_read"):
                self.repo.mark_notification_read(item_id)  # type: ignore[attr-defined]
            self.reload()
        elif chosen == delete:
            if hasattr(self.repo, "delete_notification"):
                self.repo.delete_notification(item_id)  # type: ignore[attr-defined]
            self.notify(S.NOTIFICATION_DELETED)
            self.reload()

    def _delete_all(self) -> None:
        dialog = ConfirmDialog(
            S.DELETE_ALL_TITLE,
            S.DELETE_ALL_TEXT,
            confirm_text=S.NOTIFICATIONS_DELETE_ALL,
            destructive=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if hasattr(self.repo, "delete_all_notifications"):
                self.repo.delete_all_notifications()  # type: ignore[attr-defined]
            self.notify(S.NOTIFICATION_DELETED)
            self.reload()
