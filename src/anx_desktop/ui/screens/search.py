"""Search: history, grid results, filters and a command-palette entry point."""

from __future__ import annotations

import os
import traceback

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Channel, Profile, SearchResults
from ..formatting import subscribers
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ArticleCard,
    Avatar,
    CardGrid,
    ClickableFrame,
    CollectionCard,
    EmptyState,
    ErrorState,
    PosterCard,
    SearchField,
    SectionHeader,
    SkeletonList,
)
from ..widgets.dialogs import MessageDialog
from ..widgets.util import clear_layout
from .base import BaseScreen

# One page of releases is rendered inline; "show all" opens ListScreen.
RELEASE_GRID_LIMIT = 24
COLLECTION_GRID_LIMIT = 8


class HistoryRow(ClickableFrame):
    def __init__(self, query: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.query = query
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        layout.setSpacing(theme.space("m"))
        icon = QLabel(self)
        icon.setPixmap(icons.pixmap("history", "text_secondary", 20))
        layout.addWidget(icon)
        label = QLabel(query, self)
        label.setProperty("role", "body")
        layout.addWidget(label, 1)
        arrow = QLabel(self)
        arrow.setPixmap(icons.pixmap("chevron_right", "icon", 16))
        layout.addWidget(arrow)
        self.setMinimumHeight(theme.px(44))


class ChannelResultRow(ClickableFrame):
    subscribe_clicked = Signal(str)

    def __init__(self, channel: Channel, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        layout.setSpacing(theme.space("m"))
        layout.addWidget(Avatar(channel.title, size=theme.semantic("list_avatar_size") - 8, seed=channel.seed))
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        title = QLabel(channel.title, self)
        title.setProperty("role", "body")
        title.setStyleSheet("font-weight: 500;")
        text.addWidget(title)
        meta = QLabel(subscribers(channel.subscriber_count), self)
        meta.setProperty("role", "tertiary")
        text.addWidget(meta)
        layout.addLayout(text, 1)
        button = QPushButton(S.FEED_UNSUBSCRIBE if channel.is_subscribed else S.FEED_SUBSCRIBE, self)
        button.setProperty("ui", "outlined" if channel.is_subscribed else "primary")
        button.clicked.connect(lambda: self.subscribe_clicked.emit(channel.title))
        layout.addWidget(button)


class ProfileResultRow(ClickableFrame):
    def __init__(self, profile: Profile, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        layout.setSpacing(theme.space("m"))
        layout.addWidget(
            Avatar(profile.nick, size=theme.semantic("list_avatar_size") - 8, seed=profile.id, online=profile.is_online)
        )
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        name = QLabel(profile.nick, self)
        name.setProperty("role", "body")
        name.setStyleSheet("font-weight: 500;")
        text.addWidget(name)
        status = QLabel(profile.status or S.PROFILE_BIO_EMPTY, self)
        status.setProperty("role", "tertiary")
        text.addWidget(status)
        layout.addLayout(text, 1)


class SearchScreen(BaseScreen):
    """Search screen with a persistent toolbar and a re-renderable results area.

    Typing only refreshes the results host; the screen itself is never rebuilt
    on keystrokes, so the field keeps focus and the full query.
    """

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_SEARCH)
        self._query = ""
        self._pending = ""
        self._field: SearchField | None = None
        self._results_host: QWidget | None = None
        self._results_layout: QVBoxLayout | None = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 320)
        self._search_timer.timeout.connect(self._run_pending_search)

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(
            S.EMPTY_SEARCH_TITLE,
            S.EMPTY_SEARCH_HINT,
            action_text=S.NAV_HOME,
            icon_name="search",
            parent=self,
        )
        page.action_clicked.connect(lambda: self.open_route("home"))
        return page

    def focus_search(self) -> None:
        if self._field is not None:
            self._field.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self._field.selectAll()
            self.scroll_to_top()

    def is_empty_result(self) -> bool:
        # Empty results are rendered inline so the search field stays visible;
        # the full-screen empty page is reserved for demo states.
        return False

    def set_payload(self, payload) -> None:
        if isinstance(payload, str):
            query = payload
        elif isinstance(payload, dict):
            query = str(payload.get("query", ""))
        else:
            query = ""
        self._query = query
        self._pending = query
        self._sync_field()
        if self._results_layout is not None:
            self._render_results()

    def _sync_field(self) -> None:
        if self._field is None:
            return
        if self._field.text() != self._query:
            self._field.blockSignals(True)
            self._field.setText(self._query)
            self._field.blockSignals(False)
        self._field.set_filter_visible(bool(self._query))

    def _outlet(self) -> QVBoxLayout:
        layout = self._results_layout
        if layout is None:
            raise RuntimeError("search results area is not built")
        return layout

    # ------------------------------------------------------------------ build
    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        row.setSpacing(theme.space("sm"))
        field = SearchField(
            S.SEARCH_PLACEHOLDER,
            show_mic=True,
            show_filter=bool(self._query),
            parent=toolbar,
        )
        field.setMinimumWidth(theme.px(420))
        field.blockSignals(True)
        field.setText(self._query)
        field.blockSignals(False)
        field.set_filter_visible(bool(self._query))
        field.textChanged.connect(self._on_text)
        field.submitted.connect(self._on_submit)
        field.cleared.connect(self._on_cleared)
        field.filter_clicked.connect(lambda: self.open_route("filter"))
        field.mic_clicked.connect(lambda: self.notify(S.SEARCH_VOICE_STUB))
        row.addWidget(field, 1, Qt.AlignmentFlag.AlignLeft)
        self._field = field
        self.add_content(toolbar)

        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._results_host = host
        self._results_layout = layout
        self.add_content(host, 1)
        self._render_results()
        self.scroll_to_top()

    # ---------------------------------------------------------------- results
    def _render_results(self) -> None:
        if self._results_layout is None or self._results_host is None:
            return
        clear_layout(self._results_layout)
        query = self._query.strip()
        if not query:
            self._render_history()
            return
        try:
            results = self.repo.fetch_search(self._query)
        except Exception:  # pragma: no cover - defensive UI guard
            traceback.print_exc()
            state = ErrorState(parent=self._results_host)
            state.retry_clicked.connect(self._render_results)
            state.help_clicked.connect(self._show_help)
            self._outlet().addWidget(state)
            self._outlet().addStretch(1)
            return
        if not any(
            (results.releases, results.articles, results.channels, results.profiles, results.collections)
        ):
            state = EmptyState(
                S.EMPTY_SEARCH_TITLE,
                S.EMPTY_SEARCH_HINT,
                action_text=S.NAV_HOME,
                icon_name="search",
                parent=self._results_host,
            )
            state.action_clicked.connect(lambda: self.open_route("home"))
            self._outlet().addWidget(state)
            self._outlet().addStretch(1)
            return
        self._render_intro(query)
        if results.releases:
            self._release_group(results)
        if results.articles:
            self._article_group(results)
        if results.channels:
            self._channel_group(results)
        if results.profiles:
            self._profile_group(results)
        if results.collections:
            self._collection_group(results)
        self._render_actions()
        self._outlet().addStretch(1)

    def _render_intro(self, query: str) -> None:
        theme = active_theme()
        host = self._results_host or self
        intro = QWidget(host)
        layout = QVBoxLayout(intro)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        layout.setSpacing(theme.space("xxs"))
        title = QLabel(S.SEARCH_RESULTS, intro)
        title.setProperty("role", "section")
        layout.addWidget(title)
        subtitle = QLabel(f"«{query}»", intro)
        subtitle.setProperty("role", "muted")
        layout.addWidget(subtitle)
        self._outlet().addWidget(intro)

    def _render_history(self) -> None:
        theme = active_theme()
        host = self._results_host or self
        history = self.repo.search_history()
        header = SectionHeader(
            S.SEARCH_HISTORY,
            action_text=S.SEARCH_CLEAR_HISTORY,
            parent=host,
        )
        header.set_action_visible(bool(history))
        header.show_all.connect(self._clear_history)
        self._outlet().addWidget(header)
        if not history:
            hint = QLabel(S.EMPTY_HINT, host)
            hint.setProperty("role", "tertiary")
            hint.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), 0)
            hint.setWordWrap(True)
            self._outlet().addWidget(hint)
        else:
            for query in history:
                row = HistoryRow(query, parent=host)
                row.clicked.connect(lambda q=query: self._search_now(q))
                self._outlet().addWidget(row)
        self._outlet().addStretch(1)

    def _release_group(self, results: SearchResults) -> None:
        theme = active_theme()
        host = self._results_host or self
        header = SectionHeader(S.SEARCH_RELEASES, parent=host)
        header.show_all.connect(
            lambda: self.open_route("list", {"kind": "search", "query": self._query, "title": S.SEARCH_RELEASES})
        )
        self._outlet().addWidget(header)
        width, height = theme.tokens.grid_poster_size()
        cards = []
        for release in results.releases[:RELEASE_GRID_LIMIT]:
            card = PosterCard(release, poster_width=width, poster_height=height, parent=host)
            card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
            cards.append(card)
        grid = CardGrid(
            cards,
            min_card_width=width + theme.space("l"),
            max_columns=6,
            parent=host,
        )
        self._outlet().addWidget(grid)

    def _article_group(self, results: SearchResults) -> None:
        theme = active_theme()
        host = self._results_host or self
        header = SectionHeader(S.SEARCH_ARTICLES, parent=host)
        self._outlet().addWidget(header)
        for article in results.articles[:2]:
            channel = self.repo.fetch_channel(article.channel_id).channel
            card = ArticleCard(article, channel, parent=host)
            card.clicked.connect(lambda aid=article.id: self.open_route("article", aid))
            wrapper = QWidget(host)
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm"))
            layout.addWidget(card)
            self._outlet().addWidget(wrapper)

    def _channel_group(self, results: SearchResults) -> None:
        host = self._results_host or self
        header = SectionHeader(S.SEARCH_CHANNELS, parent=host)
        header.set_action_visible(False)
        self._outlet().addWidget(header)
        for channel in results.channels:
            row = ChannelResultRow(channel, parent=host)
            row.clicked.connect(lambda cid=channel.id: self.open_route("channel", cid))
            row.subscribe_clicked.connect(self._toggle_subscribe)
            self._outlet().addWidget(row)

    def _profile_group(self, results: SearchResults) -> None:
        host = self._results_host or self
        header = SectionHeader(S.SEARCH_PROFILES, parent=host)
        header.set_action_visible(False)
        self._outlet().addWidget(header)
        for profile in results.profiles:
            row = ProfileResultRow(profile, parent=host)
            row.clicked.connect(lambda: self.open_route("profile"))
            self._outlet().addWidget(row)

    def _collection_group(self, results: SearchResults) -> None:
        theme = active_theme()
        host = self._results_host or self
        header = SectionHeader(S.SEARCH_COLLECTIONS, parent=host)
        header.show_all.connect(lambda: self.open_route("collections"))
        self._outlet().addWidget(header)
        cards = []
        for collection in results.collections[:COLLECTION_GRID_LIMIT]:
            card = CollectionCard(
                collection,
                width=theme.px(320),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=host,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            cards.append(card)
        grid = CardGrid(cards, min_card_width=theme.px(280), max_columns=4, parent=host)
        self._outlet().addWidget(grid)

    def _render_actions(self) -> None:
        theme = active_theme()
        host = self._results_host or self
        actions = QWidget(host)
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("m")
        )
        layout.setSpacing(theme.space("sm"))
        other = QPushButton(S.SEARCH_OTHER, actions)
        other.setProperty("ui", "outlined")
        other.clicked.connect(lambda: self.notify(S.SEARCH_GLOBAL_STUB))
        layout.addWidget(other)
        global_button = QPushButton(S.SEARCH_GLOBAL, actions)
        global_button.setProperty("ui", "text")
        global_button.clicked.connect(
            lambda: MessageDialog(S.SEARCH_GLOBAL, S.SEARCH_GLOBAL_STUB, parent=self).exec()
        )
        layout.addWidget(global_button)
        layout.addStretch(1)
        self._outlet().addWidget(actions)

    def _clear_history(self) -> None:
        self.repo.clear_search_history()
        self._render_results()

    # ------------------------------------------------------------------ input
    def _on_text(self, text: str) -> None:
        self._pending = text.strip()
        if self._field is not None:
            self._field.set_filter_visible(bool(text))
        self._search_timer.start()

    def _run_pending_search(self) -> None:
        if self._pending == self._query:
            return
        self._search_now(self._pending)

    def _on_submit(self, text: str) -> None:
        self._search_timer.stop()
        self._search_now(text.strip(), remember=True)

    def _search_now(self, query: str, *, remember: bool = False) -> None:
        if remember and query and hasattr(self.repo, "remember_search"):
            self.repo.remember_search(query)  # type: ignore[attr-defined]
        self._query = query
        self._pending = query
        self._sync_field()
        self._render_results()
        self.scroll_to_top()

    def _on_cleared(self) -> None:
        self._search_timer.stop()
        if not self._query and not self._pending:
            return
        self._query = ""
        self._pending = ""
        self._render_results()

    def _toggle_subscribe(self, _name: str) -> None:
        self.notify(S.SUBSCRIBED)
