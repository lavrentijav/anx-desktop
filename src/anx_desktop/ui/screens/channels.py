"""Каналы: list, channel page, articles and management stub screens."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Article, Channel, ChannelDetails
from ..formatting import format_date, subscribers
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ArticleCard,
    Avatar,
    ChipRow,
    ClickableFrame,
    EmptyState,
    InfoBanner,
    SearchField,
    SectionHeader,
    SkeletonDetail,
    SkeletonList,
    Switch,
    TextBadge,
    paint_placeholder,
)
from ..widgets.dialogs import (
    ComposeArticleDialog,
    ComposeChannelDialog,
    MessageDialog,
    ReportDialog,
)
from .base import BaseScreen


class ChannelCover(QWidget):
    def __init__(self, seed: int, *, height: int = 160, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._seed = seed
        self.setFixedHeight(active_theme().px(height))

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        paint_placeholder(
            painter,
            QRectF(0, 0, self.width(), self.height()),
            seed=self._seed,
            radius=theme.radius("collection_card"),
            accent=True,
        )


class ChannelRow(ClickableFrame):
    subscribe_clicked = Signal(int)

    def __init__(self, channel: Channel, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.channel = channel
        self.setProperty("ui", "card")
        layout = QHBoxLayout(self)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("m"))
        layout.addWidget(Avatar(channel.title, size=theme.semantic("list_avatar_size"), seed=channel.seed))
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        header = QHBoxLayout()
        title = QLabel(channel.title, self)
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        if channel.is_verified:
            check = QLabel(self)
            check.setPixmap(icons.pixmap("verified", "icon_alt", 15))
            header.addWidget(check)
        if channel.is_blog:
            header.addWidget(TextBadge(S.SEARCH_ARTICLES, parent=self))
        header.addStretch(1)
        text.addLayout(header)
        meta = QLabel(
            f"{subscribers(channel.subscriber_count)} · {S.SEARCH_ARTICLES}: {channel.article_count}",
            self,
        )
        meta.setProperty("role", "tertiary")
        text.addWidget(meta)
        description = QLabel(channel.description, self)
        description.setProperty("role", "muted")
        description.setWordWrap(True)
        text.addWidget(description)
        layout.addLayout(text, 1)
        button = QPushButton(S.FEED_UNSUBSCRIBE if channel.is_subscribed else S.FEED_SUBSCRIBE, self)
        button.setProperty("ui", "outlined" if channel.is_subscribed else "primary")
        button.clicked.connect(lambda: self.subscribe_clicked.emit(channel.id))
        layout.addWidget(button)


class ChannelsScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.CHANNELS_TITLE)
        self._query = ""
        self._subscribed_only = False
        self._list_layout: QVBoxLayout | None = None
        self._count_label: QLabel | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(S.EMPTY_CHANNELS, S.EMPTY_HINT, icon_name="channel", parent=self)
        page.action_clicked.connect(self._create_channel)
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("sm"))
        search = SearchField(S.CHANNELS_SEARCH, show_mic=False, parent=toolbar)
        search.blockSignals(True)
        search.setText(self._query)
        search.blockSignals(False)
        search.textChanged.connect(self._on_search)
        row.addWidget(search, 1)
        filter_chips = ChipRow(
            (S.CHANNELS_ALL, S.CHANNELS_SUBSCRIBED),
            exclusive=True,
            checked=(S.CHANNELS_SUBSCRIBED if self._subscribed_only else S.CHANNELS_ALL,),
            parent=toolbar,
        )
        filter_chips.changed.connect(lambda: self._on_filter(filter_chips))
        row.addWidget(filter_chips)
        create = QPushButton(S.CHANNELS_CREATE, toolbar)
        create.setProperty("ui", "primary")
        create.clicked.connect(self._create_channel)
        row.addWidget(create)
        self.add_content(toolbar)
        self._count_label = QLabel(toolbar)
        self._count_label.setProperty("role", "uppercase")
        self._count_label.setContentsMargins(theme.semantic("screen_gutter"), 0, 0, theme.space("xs"))
        self.add_content(self._count_label)
        host = QWidget(self)
        self._list_layout = QVBoxLayout(host)
        self._list_layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        self._list_layout.setSpacing(theme.space("sm"))
        channels = self.repo.fetch_channels(self._query, self._subscribed_only)
        self._channel_count = len(channels)
        if self._count_label is not None:
            self._count_label.setText(S.HOME_COUNT.format(count=len(channels)))
        for channel in channels:
            row_widget = ChannelRow(channel, parent=host)
            row_widget.clicked.connect(lambda cid=channel.id: self.open_route("channel", cid))
            row_widget.subscribe_clicked.connect(self._toggle_subscription)
            self._list_layout.addWidget(row_widget)
        if not channels:
            self._list_layout.addWidget(
                EmptyState(S.EMPTY_CHANNELS, S.EMPTY_HINT, icon_name="channel", parent=host)
            )
        self.add_content(host, 1)
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return getattr(self, "_channel_count", 0) == 0 and (bool(self._query) or self._subscribed_only)

    def _on_search(self, text: str) -> None:
        self._query = text.strip()
        self.reload()

    def _on_filter(self, row: ChipRow) -> None:
        labels = row.checked_labels()
        self._subscribed_only = bool(labels and labels[0] == S.CHANNELS_SUBSCRIBED)
        self.reload()

    def _toggle_subscription(self, channel_id: int) -> None:
        self.notify(S.SUBSCRIBED)
        self.reload()

    def _create_channel(self) -> None:
        dialog = ComposeChannelDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.CHANNELS_CREATED)
            self.reload()


class ChannelScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, channel_id: int = 0) -> None:
        super().__init__(ctx, title=S.CHANNELS_TITLE)
        self.channel_id = channel_id
        self._details: ChannelDetails | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonDetail(parent=self)

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_channel(self.channel_id)
        self._details = details
        channel = details.channel
        self.ctx.host.set_header(channel.title, subscribers(channel.subscriber_count))
        theme = active_theme()
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("sm"))
        layout.addWidget(ChannelCover(channel.seed, height=180, parent=page))
        header = QFrame(page)
        header.setProperty("ui", "panel")
        header_layout = QHBoxLayout(header)
        margin = theme.space("l")
        header_layout.setContentsMargins(margin, margin, margin, margin)
        header_layout.setSpacing(theme.space("m"))
        header_layout.addWidget(Avatar(channel.title, size=theme.px(80), seed=channel.seed))
        info = QVBoxLayout()
        info.setSpacing(theme.space("xxs"))
        title_row = QHBoxLayout()
        title = QLabel(channel.title, header)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('profile_nickname')['size_sp']))}px;"
            " font-weight: 600;"
        )
        title_row.addWidget(title)
        if channel.is_verified:
            check = QLabel(header)
            check.setPixmap(icons.pixmap("verified", "icon_alt", 18))
            title_row.addWidget(check)
        title_row.addStretch(1)
        info.addLayout(title_row)
        meta = QLabel(
            f"{subscribers(channel.subscriber_count)} · {S.SEARCH_ARTICLES}: {channel.article_count}",
            header,
        )
        meta.setProperty("role", "tertiary")
        info.addWidget(meta)
        description = QLabel(channel.description, header)
        description.setProperty("role", "muted")
        description.setWordWrap(True)
        info.addWidget(description)
        header_layout.addLayout(info, 1)
        buttons = QVBoxLayout()
        subscribe = QPushButton(S.FEED_UNSUBSCRIBE if channel.is_subscribed else S.FEED_SUBSCRIBE, header)
        subscribe.setProperty("ui", "outlined" if channel.is_subscribed else "primary")
        subscribe.clicked.connect(lambda: self.notify(S.SUBSCRIBED))
        buttons.addWidget(subscribe)
        if channel.is_creator:
            manage = QPushButton(S.CHANNELS_MANAGE, header)
            manage.setProperty("ui", "outlined")
            manage.clicked.connect(lambda: self.open_route("channel_manage", channel.id))
            buttons.addWidget(manage)
        more = QPushButton(S.MORE, header)
        more.setProperty("ui", "text")
        more.clicked.connect(lambda: self._menu(more))
        buttons.addWidget(more)
        header_layout.addLayout(buttons)
        layout.addWidget(header)
        if channel.is_muted:
            layout.addWidget(InfoBanner(S.CHANNELS_HIDDEN_STATE, icon_name="lock", parent=page))
        header_row = QHBoxLayout()
        articles_title = QLabel(S.SEARCH_ARTICLES, page)
        articles_title.setProperty("role", "section")
        header_row.addWidget(articles_title)
        header_row.addStretch(1)
        if channel.is_creator:
            add_article = QPushButton(S.CHANNELS_ADD_ARTICLE, page)
            add_article.setProperty("ui", "primary")
            add_article.clicked.connect(self._add_article)
            header_row.addWidget(add_article)
        layout.addLayout(header_row)
        if details.articles:
            for article in details.articles:
                card = ArticleCard(article, channel, parent=page)
                card.clicked.connect(lambda aid=article.id: self.open_route("article", aid))
                layout.addWidget(card)
        else:
            layout.addWidget(EmptyState(S.EMPTY_ARTICLES, S.EMPTY_HINT, icon_name="article", parent=page))
        layout.addStretch(1)
        self.add_content(page, 1)

    def _menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        share = menu.addAction(S.SHARE)
        mute = menu.addAction(S.FEED_MUTE)
        report = menu.addAction(S.REPORT)
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == mute:
            self.notify(S.FEED_MUTE)
        elif chosen == report:
            channel = self._details.channel if self._details else None
            ReportDialog(channel.title if channel else S.CHANNELS_TITLE, parent=self).exec()

    def _add_article(self) -> None:
        self.open_route("article_editor")


class ChannelManageScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx, channel_id: int = 0) -> None:
        super().__init__(ctx, title=S.CHANNELS_EDIT)
        self.channel_id = channel_id
        self._details: ChannelDetails | None = None

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_channel(self.channel_id)
        self._details = details
        channel = details.channel
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("m"))
        title_label = QLabel(S.CHANNELS_EDIT, wrap)
        title_label.setProperty("role", "section")
        layout.addWidget(title_label)
        title_input = QLineEdit(channel.title, wrap)
        layout.addWidget(title_input)
        description_input = QLineEdit(channel.description, wrap)
        layout.addWidget(description_input)
        for label, checked, enabled in (
            (S.CHANNELS_COMMENTS, True, True),
            (S.CHANNELS_SUGGESTIONS, True, True),
            (S.CHANNELS_WIDGET, not self.settings.hide_channel_widgets, True),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label, wrap))
            row.addStretch(1)
            switch = Switch(checked, wrap)
            row.addWidget(switch)
            layout.addLayout(row)
        save = QPushButton(S.SAVE, wrap)
        save.setProperty("ui", "primary")
        save.clicked.connect(lambda: self.notify(S.CHANNELS_SAVED))
        layout.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(SectionHeader(S.CHANNELS_ADMINS, action_text="", parent=wrap))
        layout.addWidget(EmptyState(S.CHANNELS_EMPTY_ADMINS, "", icon_name="user", parent=wrap))
        layout.addWidget(SectionHeader(S.CHANNELS_SUBSCRIBERS, action_text="", parent=wrap))
        layout.addWidget(EmptyState(S.CHANNELS_EMPTY_SUBSCRIBERS, "", icon_name="user", parent=wrap))
        layout.addWidget(SectionHeader(S.CHANNELS_BLOCKS, action_text="", parent=wrap))
        layout.addWidget(EmptyState(S.CHANNELS_EMPTY_BLOCKS, "", icon_name="lock", parent=wrap))
        layout.addStretch(1)
        self.add_content(wrap, 1)
