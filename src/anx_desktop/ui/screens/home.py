"""Главная: nine scrollable tabs and poster grid/list catalog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QRunnable, QStandardPaths, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from ..data import DemoRepository, DemoState, Page, Release, TabSpec
from ..home_cache import HomeCache
from ..strings import S
from ..theme import active_theme

from ..widgets import (
    CardGrid,
    FooterLoader,
    PosterCard,
    ReleaseRow,
    SegmentedControl,
    SkeletonGrid,
    TabsBar,
)
from ..widgets.dialogs import MessageDialog
from .base import BaseScreen

PAGE_SIZE = 12


class _HomeFetchSignals(QObject):
    finished = Signal(int, int, object, object)


class _HomeFetch(QRunnable):
    def __init__(self, repo, tab: str, number: int, token: int) -> None:
        super().__init__()
        self.signals = _HomeFetchSignals()
        self.repo = repo
        self.tab = tab
        self.number = number
        self.token = token

    def run(self) -> None:
        try:
            page = self.repo.fetch_home(self.tab, self.number, PAGE_SIZE)
        except Exception as exc:
            self.signals.finished.emit(self.token, self.number, None, exc)
        else:
            self.signals.finished.emit(self.token, self.number, page, None)


class HomeScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_HOME)
        self._tab_key = ctx.settings.home_tab
        self._page = 1
        self._total_pages = 1
        self._cards_host: QWidget | None = None
        self._cards_layout = None
        self._grid: CardGrid | None = None
        self._footer: FooterLoader | None = None
        self._count_label: QLabel | None = None
        cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericCacheLocation)
        self._cache = (
            HomeCache(Path(cache_dir) / "anx-desktop" / "home.sqlite3")
            if cache_dir and not isinstance(self.repo, DemoRepository) else None
        )
        self._tabs: tuple[TabSpec, ...] = ()
        self._shown_page: Page[Release] | None = None
        self._fetching = False

    def create_loading_page(self) -> QWidget:
        return SkeletonGrid(columns=5, rows=2, parent=self)

    def create_empty_page(self) -> QWidget:
        page = super().create_empty_page()
        page.action_clicked.connect(lambda: self.open_route("search"))
        return page

    def reload(self) -> None:
        self._token += 1
        self._fetching = False
        self._last_load_error = None
        self._shown_page = None
        state = self._demo_state()
        if state == DemoState.LOADING:
            self.show_loading()
            return
        if state == DemoState.ERROR:
            self.show_error()
            return
        if state == DemoState.EMPTY:
            self.show_empty()
            return
        try:
            self._tabs = tuple(self.repo.home_tabs())
            if self._tab_key not in {tab.key for tab in self._tabs}:
                self._tab_key = self._tabs[0].key if self._tabs else "home_0"
            self.settings.home_tab = self._tab_key
            cached = self._cache.load(self._tab_key, PAGE_SIZE) if self._cache else None
        except Exception as exc:
            self._last_load_error = exc
            self.show_error()
            return
        if cached is None:
            self.show_loading()
        else:
            self._render_page(cached)
        self._request_page(1)

    def _request_page(self, number: int) -> None:
        self._fetching = True
        if self._shown_page is not None and self._footer is not None:
            if self._page < self._total_pages:
                self._footer.set_loading()
        job = _HomeFetch(self.repo, self._tab_key, number, self._token)
        job.signals.finished.connect(self._on_page_fetched, Qt.ConnectionType.QueuedConnection)
        QThreadPool.globalInstance().start(job)

    @Slot(int, int, object, object)
    def _on_page_fetched(
        self, token: int, number: int, page: Page[Release] | None, error: Exception | None
    ) -> None:
        if token != self._token:
            return
        self._fetching = False
        if number == 1:
            if page is None:
                self._last_load_error = error
                if self._shown_page is None:
                    self.show_error()
            elif page.items or self._shown_page is None:
                self._render_page(page)
                if self._cache is not None:
                    self._cache.store(self._tab_key, page)
        elif page is not None and page.items and page.page == number:
            self._append_page(page)
        if self._shown_page is not None and self._footer is not None:
            if self._page < self._total_pages:
                self._footer.set_idle()
            else:
                self._footer.set_hidden()

    def _render_page(self, page: Page[Release]) -> None:
        self.reset_content()
        self._shown_page = page
        tabs = self._tabs
        tabs_bar = TabsBar(tabs, current=self._tab_key, parent=self)
        tabs_bar.tab_changed.connect(self._on_tab_changed)
        tabs_bar.tab_context_requested.connect(self._on_tab_context)
        self.add_content(tabs_bar)

        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        theme = active_theme()
        row.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        row.setSpacing(theme.space("m"))
        current_spec = next((tab for tab in tabs if tab.key == self._tab_key), None)
        self._count_label = QLabel(toolbar)
        self._count_label.setProperty("role", "uppercase")
        row.addWidget(self._count_label)
        subtitle = QLabel(current_spec.subtitle if current_spec else "", toolbar)
        subtitle.setProperty("role", "tertiary")
        row.addWidget(subtitle)
        row.addStretch(1)
        view = SegmentedControl(
            (("list", S.SETTINGS_VIEW_LIST), ("grid", S.SETTINGS_VIEW_GRID)),
            current=self.settings.view_mode,
            parent=toolbar,
        )
        view.changed.connect(self._on_view_changed)
        row.addWidget(view)
        self.add_content(toolbar)


        self._page = page.page
        self._total_pages = page.total_pages
        if self._count_label is not None:
            self._count_label.setText(S.HOME_COUNT.format(count=page.total_count))
        self._cards_host = QWidget(self)
        if self.settings.view_mode == "list":
            self._cards_layout = QVBoxLayout(self._cards_host)
            self._cards_layout.setContentsMargins(0, 0, 0, 0)
            self._cards_layout.setSpacing(0)
            self._grid = None
            for release in page.items:
                self._cards_layout.addWidget(self._make_row(release))
        else:
            width, height = theme.tokens.grid_poster_size()
            cards = [self._make_card(release, width, height) for release in page.items]
            self._grid = CardGrid(cards, min_card_width=width + theme.space("l"), max_columns=6, parent=self._cards_host)
            self._cards_layout = QVBoxLayout(self._cards_host)
            self._cards_layout.setContentsMargins(0, 0, 0, 0)
            self._cards_layout.addWidget(self._grid)
        self.add_content(self._cards_host, 1)
        self._footer = FooterLoader(parent=self)
        self._footer.load_more.connect(self._load_more)
        self.add_content(self._footer)
        if page.has_more:
            self._footer.set_idle()
        else:
            self._footer.set_hidden()
        self.add_stretch(1)
        self._content_built = True
        self._has_content = True
        self.show_content()

    def _make_card(self, release: Release, width: int, height: int) -> PosterCard:
        card = PosterCard(release, poster_width=width, poster_height=height, parent=self)
        card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
        card.context_requested.connect(
            lambda pos, rel=release: self._release_context(rel, pos)
        )
        return card

    def _make_row(self, release: Release) -> ReleaseRow:
        row = ReleaseRow(release, parent=self)
        row.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
        row.favorite_toggled.connect(lambda rid: self.notify(S.MOVED_TO_FAVORITES))
        row.more_clicked.connect(
            lambda rid, rel=release: self._release_context(rel, self.mapToGlobal(QPoint(40, 40)))
        )
        row.context_requested.connect(lambda pos, rel=release: self._release_context(rel, pos))
        return row

    def _on_tab_changed(self, key: str) -> None:
        self._tab_key = key
        self.settings.home_tab = key
        self.reload()
        self.scroll_to_top()

    def _on_view_changed(self, mode: str) -> None:
        self.settings.view_mode = mode
        self.reload()

    def _on_tab_context(self, key: str, pos: QPoint) -> None:
        menu = QMenu(self)
        default_action = menu.addAction(S.HOME_DEFAULT_TAB)
        custom_action = menu.addAction(S.HOME_EDIT_TAB)
        settings_action = menu.addAction(S.HOME_TAB_SETTINGS)
        chosen = menu.exec(pos)
        if chosen == default_action:
            self.settings.home_tab = key
            self.notify(S.SET_DEFAULT_TAB)
        elif chosen == custom_action:
            self.open_route("filter", {"target": "my_tab"})
        elif chosen == settings_action:
            MessageDialog(S.HOME_TAB_SETTINGS, S.FILTER_SUBTITLE, parent=self).exec()

    def _release_context(self, release: Release, pos: QPoint) -> None:
        menu = QMenu(self)
        favorite = menu.addAction(S.RELEASE_FAVORITES)
        add_list = menu.addAction(S.RELEASE_ADD_COLLECTION)
        menu.addSeparator()
        report = menu.addAction(S.REPORT)
        chosen = menu.exec(pos)
        if chosen == favorite:
            self.notify(S.MOVED_TO_FAVORITES)
        elif chosen == add_list:
            self.open_route("collections")
        elif chosen == report:
            from ..widgets.dialogs import ReportDialog

            ReportDialog(release.title, parent=self).exec()

    def _load_more(self) -> None:
        if self._fetching or self._shown_page is None or self._page >= self._total_pages:
            return
        self._request_page(self._page + 1)

    def _append_page(self, page: Page[Release]) -> None:
        self._page = page.page
        self._total_pages = page.total_pages
        if self._grid is not None:
            width, height = active_theme().tokens.grid_poster_size()
            self._grid.add_cards([self._make_card(rel, width, height) for rel in page.items])
        elif self._cards_layout is not None:
            for release in page.items:
                self._cards_layout.addWidget(self._make_row(release))
        if self._count_label is not None:
            self._count_label.setText(S.HOME_COUNT.format(count=page.total_count))
