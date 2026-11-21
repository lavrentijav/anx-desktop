"""Закладки: eight user lists with sort, shuffle and list/grid view."""

from __future__ import annotations

import os
import random

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from ..data import Collection, Page, Release
from ..strings import S
from ..theme import active_theme
from ..timers import single_shot
from ..widgets import (
    CardGrid,
    CollectionCard,
    FooterLoader,
    PosterCard,
    ReleaseRow,
    SegmentedControl,
    SkeletonGrid,
    TabsBar,
)
from ..widgets.dialogs import ReportDialog, TextInputDialog
from .base import BaseScreen

PAGE_SIZE = 12


class BookmarksScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_BOOKMARKS)
        self._tab_key = ctx.settings.bookmarks_tab
        self._page = 1
        self._total_pages = 1
        self._cards_layout = None
        self._grid: CardGrid | None = None
        self._footer: FooterLoader | None = None
        self._count_label: QLabel | None = None
        self._sort_mode = "new"

    def create_loading_page(self) -> QWidget:
        return SkeletonGrid(columns=5, rows=2, parent=self)

    def create_empty_page(self) -> QWidget:
        page = super().create_empty_page()
        page.action_clicked.connect(lambda: self.open_route("search"))
        return page

    def populate(self) -> None:
        self.reset_content()
        tabs_method = getattr(self.repo, "bookmark_tabs", None)
        tabs = tabs_method() if tabs_method else ()
        keys = {tab.key for tab in tabs}
        if self._tab_key not in keys:
            self._tab_key = tabs[0].key if tabs else "bookmark_0"
        self.settings.bookmarks_tab = self._tab_key
        tabs_bar = TabsBar(tabs, current=self._tab_key, parent=self)
        tabs_bar.tab_changed.connect(self._on_tab_changed)
        self.add_content(tabs_bar)
        theme = active_theme()
        self._page = 1
        self._total_pages = 1
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        row.setSpacing(theme.space("sm"))
        self._count_label = QLabel(toolbar)
        self._count_label.setProperty("role", "uppercase")
        row.addWidget(self._count_label)
        row.addStretch(1)
        if self._is_collections_tab():
            create = QPushButton(S.COLLECTIONS_CREATE, toolbar)
            create.setProperty("ui", "outlined")
            create.setCursor(Qt.CursorShape.PointingHandCursor)
            create.clicked.connect(self._create_collection)
            row.addWidget(create)
        sort = QPushButton(toolbar)
        sort.setProperty("ui", "grey")
        sort.setText(S.BOOKMARK_SORT_NEW)
        sort.setIcon(self._icon("sort"))
        sort.clicked.connect(lambda: self._sort_menu(sort))
        row.addWidget(sort)
        shuffle = QPushButton(S.BOOKMARK_RANDOM, toolbar)
        shuffle.setProperty("ui", "grey")
        shuffle.setIcon(self._icon("shuffle"))
        shuffle.clicked.connect(self._open_random)
        row.addWidget(shuffle)
        view = SegmentedControl(
            (("list", S.SETTINGS_VIEW_LIST), ("grid", S.SETTINGS_VIEW_GRID)),
            current=self.settings.view_mode,
            parent=toolbar,
        )
        view.changed.connect(self._on_view_changed)
        row.addWidget(view)
        self.add_content(toolbar)
        self._cards_host = QWidget(self)
        self._cards_layout = QVBoxLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(0)
        self.add_content(self._cards_host, 1)
        self._footer = FooterLoader(parent=self)
        self._footer.load_more.connect(self._load_more)
        self.add_content(self._footer)
        self.add_stretch(1)
        if self._is_collections_tab():
            self._populate_collections()
        else:
            self._populate_releases(1, append=False)
        self._update_empty_hint()

    # ------------------------------------------------------------------ helpers
    def _is_collections_tab(self) -> bool:
        return self._tab_key.endswith("_0")

    def _tab_index(self) -> int:
        tail = self._tab_key.rsplit("_", 1)[-1]
        return int(tail) if tail.isdigit() else 0

    def _icon(self, name: str):
        from .. import icons

        return icons.icon(name, "icon", 18)

    def _update_empty_hint(self) -> None:
        hints = (
            S.BOOKMARK_EMPTY_COLLECTIONS,
            S.BOOKMARK_EMPTY_HISTORY,
            S.BOOKMARK_EMPTY_FAVORITES,
            S.BOOKMARK_EMPTY_WATCHING,
            S.BOOKMARK_EMPTY_PLANNED,
            S.BOOKMARK_EMPTY_COMPLETED,
            S.BOOKMARK_EMPTY_HOLD,
            S.BOOKMARK_EMPTY_DROPPED,
        )
        # Base empty page is generic; individual tab hints are shown in the
        # toolbar subtitle when the list becomes empty via demo state.
        hint = hints[min(self._tab_index(), len(hints) - 1)]
        self.subtitle = hint

    def _populate_collections(self) -> None:
        theme = active_theme()
        collections = self.repo.fetch_collections()
        sorted_collections = self._sort_collections(collections)
        if self._count_label is not None:
            self._count_label.setText(S.HOME_COUNT.format(count=len(sorted_collections)))
        cards = []
        for collection in sorted_collections:
            card = CollectionCard(
                collection,
                width=theme.px(320),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=self,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            cards.append(card)
        grid = CardGrid(cards, min_card_width=theme.px(280), parent=self)
        if self._cards_layout is not None:
            self._cards_layout.addWidget(grid)
        if self._footer is not None:
            self._footer.set_hidden()

    def _sort_collections(self, collections) -> list[Collection]:
        items = list(collections)
        if self._sort_mode == "old":
            items.sort(key=lambda item: item.created_ts)
        elif self._sort_mode == "title":
            items.sort(key=lambda item: item.title.lower())
        else:
            items.sort(key=lambda item: item.created_ts, reverse=True)
        return items

    def _sort_releases(self, releases: list[Release]) -> list[Release]:
        if self._sort_mode == "old":
            return sorted(releases, key=lambda item: item.year)
        if self._sort_mode == "new":
            return sorted(releases, key=lambda item: item.year, reverse=True)
        if self._sort_mode == "title":
            return sorted(releases, key=lambda item: item.title.lower())
        if self._sort_mode == "title_desc":
            return sorted(releases, key=lambda item: item.title.lower(), reverse=True)
        return releases

    def _populate_releases(self, page_number: int, *, append: bool) -> None:
        theme = active_theme()
        page: Page[Release] = self.repo.fetch_bookmarks(self._tab_key, page_number, PAGE_SIZE)
        self._page = page.page
        self._total_pages = page.total_pages
        if self._count_label is not None:
            self._count_label.setText(S.HOME_COUNT.format(count=page.total_count))
        releases = self._sort_releases(list(page.items))
        if not append and self._cards_layout is not None:
            while self._cards_layout.count():
                item = self._cards_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        if self.settings.view_mode == "grid" and not self._is_collections_tab():
            width, height = theme.tokens.grid_poster_size()
            cards = []
            for release in releases:
                card = PosterCard(release, poster_width=width, poster_height=height, parent=self)
                card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                card.context_requested.connect(lambda pos, rel=release: self._release_context(rel, pos))
                cards.append(card)
            if not append:
                self._grid = CardGrid(cards, min_card_width=width + theme.space("l"), max_columns=6, parent=self)
                if self._cards_layout is not None:
                    self._cards_layout.addWidget(self._grid)
            elif self._grid is not None:
                self._grid.add_cards(cards)
        else:
            for release in releases:
                row = ReleaseRow(release, parent=self)
                row.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                row.more_clicked.connect(lambda rid, rel=release: self._release_context(rel, self.mapToGlobal(QPoint(40, 80))))
                row.context_requested.connect(lambda pos, rel=release: self._release_context(rel, pos))
                if self._cards_layout is not None:
                    self._cards_layout.addWidget(row)
        if self._footer is not None:
            if page.has_more:
                self._footer.set_idle()
            else:
                self._footer.set_hidden()

    def _load_more(self) -> None:
        if self._footer is None or self._page >= self._total_pages:
            return
        self._footer.set_loading()
        single_shot(
            self,
            0 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 160,
            lambda: self._populate_releases(self._page + 1, append=True),
        )

    def _on_tab_changed(self, key: str) -> None:
        self._tab_key = key
        self.settings.bookmarks_tab = key
        self.reload()
        self.scroll_to_top()

    def _on_view_changed(self, mode: str) -> None:
        self.settings.view_mode = mode
        self.reload()

    def _sort_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        modes = (
            ("new", S.BOOKMARK_SORT_NEW),
            ("old", S.BOOKMARK_SORT_OLD),
            ("title", S.BOOKMARK_SORT_TITLE),
            ("title_desc", S.BOOKMARK_SORT_TITLE_DESC),
            ("year", S.BOOKMARK_SORT_YEAR),
        )
        actions = [(key, menu.addAction(label)) for key, label in modes]
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        for key, action in actions:
            if chosen == action:
                self._sort_mode = key
                anchor.setText(action.text())
                self.reload()
                break

    def _open_random(self) -> None:
        page = self.repo.fetch_bookmarks(self._tab_key, 1, PAGE_SIZE)
        if not page.items:
            self.notify(S.RANDOM_EMPTY)
            return
        release = random.choice(list(page.items))
        self.open_route("release", release.id)

    def _create_collection(self) -> None:
        dialog = TextInputDialog(S.COLLECTIONS_CREATE, S.ARTICLE_TITLE_FIELD, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.COLLECTIONS_CREATED)

    def _release_context(self, release: Release, pos) -> None:
        menu = QMenu(self)
        favorite = menu.addAction(S.RELEASE_FAVORITES)
        report = menu.addAction(S.REPORT)
        chosen = menu.exec(pos)
        if chosen == favorite:
            self.notify(S.MOVED_TO_FAVORITES)
        elif chosen == report:
            ReportDialog(release.title, parent=self).exec()
