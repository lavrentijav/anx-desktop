"""История просмотра: release rows with episode, source and time."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..data import HistoryEntry, Page
from ..formatting import format_date, format_rating
from ..strings import S
from ..theme import active_theme
from ..timers import single_shot
from ..widgets import (
    ClickableFrame,
    FooterLoader,
    PosterWidget,
    SkeletonList,
)
from ..widgets.dialogs import ConfirmDialog
from .base import BaseScreen

PAGE_SIZE = 12


class HistoryRow(ClickableFrame):
    def __init__(self, entry: HistoryEntry, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.entry = entry
        width, height = theme.tokens.list_poster_size()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            theme.semantic("list_row_padding_horizontal"),
            theme.semantic("list_row_padding_vertical"),
            theme.semantic("list_row_padding_end"),
            theme.semantic("list_row_padding_vertical"),
        )
        layout.setSpacing(theme.semantic("list_poster_to_text_gap"))
        layout.addWidget(PosterWidget(entry.release, width=width, height=height, parent=self))
        content = QVBoxLayout()
        content.setSpacing(theme.space("xs"))
        title = QLabel(entry.release.title, self)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('list_title')['size_sp']))}px;"
            " font-weight: 500;"
        )
        title.setWordWrap(True)
        content.addWidget(title)
        episode = QLabel(S.HISTORY_EPISODE.format(episode=entry.episode_name, type=entry.source_name), self)
        episode.setProperty("role", "muted")
        content.addWidget(episode)
        time = QLabel(format_date(entry.watch_ts), self)
        time.setProperty("role", "tertiary")
        content.addWidget(time)
        meta = QLabel(
            f"★ {format_rating(entry.release.grade)} · {entry.release.year} · {entry.release.status}",
            self,
        )
        meta.setProperty("role", "tertiary")
        content.addWidget(meta)
        content.addStretch(1)
        layout.addLayout(content, 1)
        self.setAccessibleName(entry.release.title)


class HistoryScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.HISTORY_TITLE, subtitle=S.HISTORY_SUBTITLE)
        self._page = 1
        self._total_pages = 1
        self._list_layout: QVBoxLayout | None = None
        self._footer: FooterLoader | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        from ..widgets import EmptyState

        page = EmptyState(
            S.HISTORY_EMPTY,
            S.HISTORY_EMPTY_HINT,
            action_text=S.NAV_HOME,
            parent=self,
        )
        page.action_clicked.connect(lambda: self.open_route("home"))
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        row.setSpacing(theme.space("sm"))
        page: Page[HistoryEntry] = self.repo.fetch_history(1, PAGE_SIZE)
        self._page = page.page
        self._total_pages = page.total_pages
        count = QLabel(S.HOME_COUNT.format(count=page.total_count), toolbar)
        count.setProperty("role", "uppercase")
        row.addWidget(count)
        row.addStretch(1)
        clear = QPushButton(S.HISTORY_CLEAR, toolbar)
        clear.setProperty("ui", "grey")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(self._clear_history)
        row.addWidget(clear)
        self.add_content(toolbar)
        host = QWidget(self)
        self._list_layout = QVBoxLayout(host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        for entry in page.items:
            self._list_layout.addWidget(self._make_row(entry))
        self.add_content(host, 1)
        self._footer = FooterLoader(parent=self)
        self._footer.load_more.connect(self._load_more)
        self.add_content(self._footer)
        if page.has_more:
            self._footer.set_idle()
        else:
            self._footer.set_hidden()
        self.add_stretch(1)

    def _make_row(self, entry: HistoryEntry) -> HistoryRow:
        row = HistoryRow(entry, parent=self)
        row.clicked.connect(lambda: self.open_route("release", entry.release.id))
        return row

    def _load_more(self) -> None:
        if self._footer is None or self._page >= self._total_pages:
            return
        self._footer.set_loading()

        def finish() -> None:
            page = self.repo.fetch_history(self._page + 1, PAGE_SIZE)
            self._page = page.page
            self._total_pages = page.total_pages
            if self._list_layout is not None:
                for entry in page.items:
                    self._list_layout.addWidget(self._make_row(entry))
            if self._footer is not None:
                if page.has_more:
                    self._footer.set_idle()
                else:
                    self._footer.set_hidden()

        single_shot(
            self,
            0 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 160,
            finish,
        )

    def _clear_history(self) -> None:
        dialog = ConfirmDialog(
            S.HISTORY_CLEAR_TITLE,
            S.HISTORY_CLEAR_TEXT,
            confirm_text=S.CLEAR,
            destructive=True,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.HISTORY_CLEAR)
            self.reload()
