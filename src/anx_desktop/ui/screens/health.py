"""Здоровье аккаунта и удаление аккаунта."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import DeletionData, HealthData, HealthEntry
from ..formatting import format_date_short
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ChipRow,
    Divider,
    EmptyState,
    InfoBanner,
    SegmentedStatsBar,
    SkeletonList,
    TextBadge,
)
from ..widgets.dialogs import ConfirmDialog, MessageDialog, PasswordConfirmDialog
from .base import BaseScreen


class HealthScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.HEALTH_TITLE, subtitle=S.HEALTH_SUBTITLE)
        self._data: HealthData | None = None
        self._tab = S.HEALTH_TAB_ACCOUNT
        self._list_host: QWidget | None = None
        self._list_layout: QVBoxLayout | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def populate(self) -> None:
        self.reset_content()
        data = self.repo.fetch_health()
        self._data = data
        theme = active_theme()
        status = QFrame(self)
        status.setProperty("ui", "card")
        layout = QHBoxLayout(status)
        margin = theme.space("l")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("m"))
        icon = QLabel(status)
        icon.setPixmap(icons.pixmap("health", "success", 36))
        layout.addWidget(icon)
        text = QVBoxLayout()
        title = QLabel(data.status, status)
        title.setProperty("role", "section")
        text.addWidget(title)
        subtitle = QLabel(S.HEALTH_SUBTITLE, status)
        subtitle.setProperty("role", "muted")
        text.addWidget(subtitle)
        layout.addLayout(text, 1)
        info = QPushButton(S.HEALTH_INFO, status)
        info.setProperty("ui", "outlined")
        info.clicked.connect(
            lambda: MessageDialog(S.HEALTH_INFO, S.HEALTH_SUBTITLE, parent=self).exec()
        )
        layout.addWidget(info)
        self.add_content(status)

        tabs = ChipRow(
            (S.HEALTH_TAB_ACCOUNT, S.HEALTH_TAB_CONTENT),
            exclusive=True,
            checked=(self._tab,),
            parent=self,
        )
        tabs.changed.connect(lambda: self._switch_tab(tabs))
        tab_wrap = QWidget(self)
        tab_layout = QHBoxLayout(tab_wrap)
        tab_layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        tab_layout.addWidget(tabs, 0, Qt.AlignmentFlag.AlignLeft)
        tab_layout.addStretch(1)
        self.add_content(tab_wrap)
        title = QLabel(S.HEALTH_HISTORY, self)
        title.setProperty("role", "section")
        title.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), 0, theme.space("xs"))
        self.add_content(title)
        self._list_host = QWidget(self)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self.add_content(self._list_host, 1)
        self._render_entries()
        self.add_stretch(1)

    def _switch_tab(self, row: ChipRow) -> None:
        labels = row.checked_labels()
        self._tab = labels[0] if labels else S.HEALTH_TAB_ACCOUNT
        self._render_entries()

    def _render_entries(self) -> None:
        if self._list_layout is None or self._data is None:
            return
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        entries = (
            self._data.account_entries
            if self._tab == S.HEALTH_TAB_ACCOUNT
            else self._data.content_entries
        )
        if not entries:
            from ..widgets import EmptyState

            self._list_layout.addWidget(
                EmptyState(S.HEALTH_EMPTY, S.HEALTH_EMPTY_HINT, icon_name="health", parent=self)
            )
            return
        theme = active_theme()
        for entry in entries:
            card = QFrame(self._list_host)
            card.setProperty("ui", "card")
            layout = QVBoxLayout(card)
            margin = theme.space("m")
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(theme.space("xs"))
            header = QHBoxLayout()
            title = QLabel(entry.title, card)
            title.setStyleSheet("font-weight: 600;")
            header.addWidget(title)
            header.addStretch(1)
            badge = TextBadge(
                S.HEALTH_ACTIVE if entry.active else S.HEALTH_REVOKED,
                role="muted",
                background="surface_tertiary",
                parent=card,
            )
            header.addWidget(badge)
            layout.addLayout(header)
            reason = QLabel(f"{S.HEALTH_REASON} {entry.reason}", card)
            reason.setWordWrap(True)
            layout.addWidget(reason)
            date = QLabel(format_date_short(entry.timestamp), card)
            date.setProperty("role", "tertiary")
            layout.addWidget(date)
            buttons = QHBoxLayout()
            appeal = QPushButton(S.HEALTH_APPEAL, card)
            appeal.setProperty("ui", "outlined")
            appeal.clicked.connect(lambda: self.notify(S.HEALTH_APPEAL_SENT))
            buttons.addWidget(appeal)
            details = QPushButton(S.HEALTH_DETAILS, card)
            details.setProperty("ui", "text")
            details.clicked.connect(
                lambda _checked=False, e=entry: MessageDialog(S.HEALTH_DETAILS, e.reason, parent=self).exec()
            )
            buttons.addWidget(details)
            buttons.addStretch(1)
            layout.addLayout(buttons)
            wrapper = QWidget(self._list_host)
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm"))
            wrapper_layout.addWidget(card)
            self._list_layout.addWidget(wrapper)


class DeletionScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.DELETION_TITLE)
        self._data: DeletionData | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(4, parent=self)

    def populate(self) -> None:
        self.reset_content()
        data = self.repo.fetch_deletion()
        self._data = data
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("m"))
        warning = InfoBanner(S.DELETION_TEXT, icon_name="warning", title=S.DELETION_TITLE, parent=wrap)
        layout.addWidget(warning)
        if data.is_requested:
            banner = InfoBanner(
                S.DELETION_DELETE_AT.format(date=format_date_short(data.delete_at or 0)),
                icon_name="warning",
                title=S.DELETION_BANNER,
                parent=wrap,
            )
            layout.addWidget(banner)
            cancel = QPushButton(S.DELETION_CANCEL, wrap)
            cancel.setProperty("ui", "outlined")
            cancel.clicked.connect(self._cancel)
            layout.addWidget(cancel, 0, Qt.AlignmentFlag.AlignLeft)
        else:
            request = QPushButton(S.DELETION_REQUEST, wrap)
            request.setProperty("ui", "danger")
            request.clicked.connect(self._request)
            layout.addWidget(request, 0, Qt.AlignmentFlag.AlignLeft)
        timeline_title = QLabel(S.DELETION_TIMELINE, wrap)
        timeline_title.setProperty("role", "section")
        layout.addWidget(timeline_title)
        steps = (
            (S.DELETION_STEP_1, S.DELETION_STEP_1_TEXT),
            (S.DELETION_STEP_2, S.DELETION_STEP_2_TEXT),
            (S.DELETION_STEP_3, S.DELETION_STEP_3_TEXT),
            (S.DELETION_STEP_4, S.DELETION_STEP_4_TEXT),
        )
        for index, (title, description) in enumerate(steps):
            row = QHBoxLayout()
            row.setSpacing(theme.space("m"))
            marker = QLabel(str(index + 1), wrap)
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            marker.setFixedSize(theme.px(28), theme.px(28))
            marker.setStyleSheet(
                f"background-color: {theme.color('accent_soft_10')};"
                f"border-radius: {theme.px(14)}px; font-weight: 600;"
            )
            row.addWidget(marker, 0, Qt.AlignmentFlag.AlignTop)
            text_box = QVBoxLayout()
            step_title = QLabel(title, wrap)
            step_title.setStyleSheet("font-weight: 600;")
            text_box.addWidget(step_title)
            step_text = QLabel(description, wrap)
            step_text.setProperty("role", "muted")
            step_text.setWordWrap(True)
            text_box.addWidget(step_text)
            row.addLayout(text_box, 1)
            layout.addLayout(row)
        layout.addWidget(Divider(parent=wrap))
        tip = QFrame(wrap)
        tip.setProperty("ui", "tertiary")
        tip_layout = QHBoxLayout(tip)
        margin = theme.space("m")
        tip_layout.setContentsMargins(margin, margin, margin, margin)
        tip_text = QVBoxLayout()
        tip_title = QLabel(S.DELETION_TIP, tip)
        tip_title.setStyleSheet("font-weight: 600;")
        tip_text.addWidget(tip_title)
        tip_caption = QLabel(S.DELETION_TIP_TEXT, tip)
        tip_caption.setProperty("role", "muted")
        tip_caption.setWordWrap(True)
        tip_text.addWidget(tip_caption)
        tip_layout.addLayout(tip_text, 1)
        save = QPushButton(S.DELETION_SAVE_BOOKMARKS, tip)
        save.setProperty("ui", "outlined")
        save.clicked.connect(lambda: self.notify(S.SETTINGS_EXPORT_OK))
        tip_layout.addWidget(save)
        layout.addWidget(tip)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _request(self) -> None:
        dialog = PasswordConfirmDialog(S.DELETION_CONFIRM_TITLE, S.DELETION_CONFIRM_TEXT, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.repo.request_deletion()
            self.notify(S.DELETION_BANNER)
            self.reload()

    def _cancel(self) -> None:
        if ConfirmDialog(S.DELETION_CANCEL, S.DELETION_TEXT, confirm_text=S.DELETION_CANCEL, parent=self).exec() == QDialog.DialogCode.Accepted:
            self.repo.cancel_deletion()
            self.notify(S.DELETION_CANCELED)
            self.reload()
