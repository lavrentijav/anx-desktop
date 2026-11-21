"""Лента: social feed of channels and articles with a subscriptions rail."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Article, Channel, FeedItem, Page
from ..formatting import subscribers
from ..strings import S
from ..theme import active_theme
from ..timers import single_shot
from ..widgets import (
    ArticleCard,
    Avatar,
    EmptyState,
    FooterLoader,
    SkeletonList,
    TabsBar,
)
from ..widgets.dialogs import ComposeArticleDialog, ComposeChannelDialog, MessageDialog
from .base import BaseScreen

PAGE_SIZE = 8


class ChannelSidebarRow(QFrame):
    def __init__(self, channel: Channel, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.channel = channel
        self.setProperty("ui", "card")
        layout = QHBoxLayout(self)
        margin = theme.space("sm")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("sm"))
        layout.addWidget(Avatar(channel.title, size=theme.px(34), seed=channel.seed))
        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(channel.title, self)
        name.setStyleSheet("font-weight: 500;")
        text.addWidget(name)
        meta = QLabel(subscribers(channel.subscriber_count), self)
        meta.setProperty("role", "tertiary")
        text.addWidget(meta)
        layout.addLayout(text, 1)
        button = QPushButton(S.FEED_UNSUBSCRIBE if channel.is_subscribed else S.FEED_SUBSCRIBE, self)
        button.setProperty("ui", "text")
        button.clicked.connect(lambda: MessageDialog(channel.title, S.SUBSCRIBED if not channel.is_subscribed else S.UNSUBSCRIBED, parent=self).exec())
        layout.addWidget(button)


class SocialFeedScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_FEED)
        self._tab_key = "feed_0"
        self._page = 1
        self._total_pages = 1
        self._feed_layout: QVBoxLayout | None = None
        self._footer: FooterLoader | None = None
        self._items: tuple[FeedItem, ...] = ()

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(
            S.FEED_EMPTY_TITLE,
            S.FEED_EMPTY_TEXT,
            action_text=S.NAV_CHANNELS,
            icon_name="channel",
            parent=self,
        )
        page.action_clicked.connect(lambda: self.open_route("channels"))
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        tabs = self.repo.feed_tabs()
        keys = {tab.key for tab in tabs}
        if self._tab_key not in keys:
            self._tab_key = tabs[0].key if tabs else "feed_0"
        tabs_bar = TabsBar(tabs, current=self._tab_key, parent=self)
        tabs_bar.tab_changed.connect(self._on_tab)
        self.add_content(tabs_bar)
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("sm"))
        new_articles = QPushButton(S.HOME_NEW_ARTICLES, toolbar)
        new_articles.setProperty("ui", "grey")
        new_articles.clicked.connect(self.reload)
        row.addWidget(new_articles)
        row.addStretch(1)
        create = QPushButton(S.CREATE, toolbar)
        create.setProperty("ui", "primary")
        create.setIcon(icons.icon("plus", "on_accent", 16))
        create.clicked.connect(lambda: self._create_menu(create))
        row.addWidget(create)
        self.add_content(toolbar)
        page: Page[FeedItem] = self.repo.fetch_feed(self._tab_key, 1, PAGE_SIZE)
        self._page = page.page
        self._total_pages = page.total_pages
        self._items = tuple(page.items)
        body = QWidget(self)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(
            theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.semantic("screen_gutter")
        )
        body_layout.setSpacing(theme.space("xl"))
        left = QWidget(body)
        left.setMaximumWidth(theme.px(900))
        self._feed_layout = QVBoxLayout(left)
        self._feed_layout.setContentsMargins(0, 0, 0, 0)
        self._feed_layout.setSpacing(theme.space("m"))
        for item in self._items:
            self._feed_layout.addWidget(self._make_article(item))
        self._folders_stub = None
        self._footer = FooterLoader(parent=left)
        self._footer.load_more.connect(self._load_more)
        self._feed_layout.addWidget(self._footer)
        if page.has_more:
            self._footer.set_idle()
        else:
            self._footer.set_hidden()
        if not self._items:
            self._feed_layout.insertWidget(
                0,
                EmptyState(S.FEED_EMPTY_TITLE, S.FEED_EMPTY_TEXT, action_text=S.NAV_CHANNELS, icon_name="channel", parent=left),
            )
        self._feed_layout.addStretch(1)
        body_layout.addWidget(left, 1)
        body_layout.addWidget(self._build_sidebar(body), 0, Qt.AlignmentFlag.AlignTop)
        self.add_content(body, 1)
        self.add_stretch(1)

    def _make_article(self, item: FeedItem) -> QWidget:
        card = ArticleCard(item.article, item.channel, parent=self)
        card.clicked.connect(lambda aid=item.article.id: self.open_route("article", aid))
        card.channel_clicked.connect(lambda cid=item.channel.id: self.open_route("channel", cid))
        card.context_requested.connect(lambda aid, pos, article=item.article: self._article_menu(article, pos))
        return card

    def _build_sidebar(self, parent: QWidget) -> QWidget:
        theme = active_theme()
        sidebar = QWidget(parent)
        sidebar.setFixedWidth(theme.px(300))
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        title = QLabel(S.NAV_CHANNELS, sidebar)
        title.setProperty("role", "section")
        layout.addWidget(title)
        for channel in self.repo.fetch_channels()[:5]:
            layout.addWidget(ChannelSidebarRow(channel, parent=sidebar))
        all_channels = QPushButton(S.SHOW_ALL, sidebar)
        all_channels.setProperty("ui", "text")
        all_channels.clicked.connect(lambda: self.open_route("channels"))
        layout.addWidget(all_channels, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(theme.space("m"))
        ready = QFrame(sidebar)
        ready.setProperty("ui", "tertiary")
        ready_layout = QVBoxLayout(ready)
        margin = theme.space("m")
        ready_layout.setContentsMargins(margin, margin, margin, margin)
        ready_layout.setSpacing(theme.space("xs"))
        subtitle = QLabel(S.FEED_READY_TITLE, ready)
        subtitle.setStyleSheet("font-weight: 600;")
        ready_layout.addWidget(subtitle)
        text = QLabel(S.FEED_READY_TEXT, ready)
        text.setProperty("role", "muted")
        text.setWordWrap(True)
        ready_layout.addWidget(text)
        layout.addWidget(ready)
        layout.addStretch(1)
        return sidebar

    def _on_tab(self, key: str) -> None:
        self._tab_key = key
        self.reload()
        self.scroll_to_top()

    def _load_more(self) -> None:
        if self._footer is None or self._page >= self._total_pages:
            return
        self._footer.set_loading()

        def finish() -> None:
            page = self.repo.fetch_feed(self._tab_key, self._page + 1, PAGE_SIZE)
            self._page = page.page
            self._total_pages = page.total_pages
            self._items = self._items + tuple(page.items)
            if self._feed_layout is not None:
                index = self._feed_layout.count() - 2
                for item in page.items:
                    self._feed_layout.insertWidget(index, self._make_article(item))
                    index += 1
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

    def _article_menu(self, article: Article, pos) -> None:
        menu = QMenu(self)
        share = menu.addAction(S.SHARE)
        hide = menu.addAction(S.ARTICLE_HIDE)
        report = menu.addAction(S.REPORT)
        chosen = menu.exec(pos)
        if chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == hide:
            self.notify(S.ARTICLE_HIDE)
        elif chosen == report:
            MessageDialog(S.REPORT_TITLE, article.title, parent=self).exec()

    def _create_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        article = menu.addAction(S.FEED_CREATE_ARTICLE)
        channel = menu.addAction(S.FEED_CREATE_CHANNEL)
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == article:
            self.open_route("article_editor")
        elif chosen == channel:
            dialog = ComposeChannelDialog(parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.notify(S.CHANNELS_CREATED)
                self.reload()
