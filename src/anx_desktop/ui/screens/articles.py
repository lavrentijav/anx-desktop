"""Записи каналов: list, reader with block rendering, editor stub."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QDialog,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Article, ArticleBlock, ArticleDetails, Channel
from ..formatting import comments as comments_plural, format_date
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ArticleCard,
    Avatar,
    ClickableFrame,
    EmptyState,
    HScrollArea,
    InfoBanner,
    SearchField,
    SectionHeader,
    SkeletonDetail,
    SkeletonList,
    TextBadge,
    paint_placeholder,
)
from ..widgets.dialogs import ComposeArticleDialog, ConfirmDialog, MessageDialog, ReportDialog
from .base import BaseScreen


class MediaTile(QWidget):
    def __init__(self, seed: int, *, width: int = 220, height: int = 140, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._seed = seed
        self.setFixedSize(width, height)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        paint_placeholder(
            painter,
            QRectF(0, 0, self.width(), self.height()),
            seed=self._seed,
            radius=theme.radius("collection_card"),
        )


class ArticlesScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.ARTICLES_TITLE)
        self._query = ""
        self._count = 0

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(S.EMPTY_ARTICLES, S.EMPTY_HINT, icon_name="article", parent=self)
        page.action_clicked.connect(self._create)
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("sm"))
        search = SearchField(S.ARTICLE_TITLE, show_mic=False, parent=toolbar)
        search.blockSignals(True)
        search.setText(self._query)
        search.blockSignals(False)
        search.textChanged.connect(self._on_query)
        row.addWidget(search, 1)
        create = QPushButton(S.ARTICLE_CREATE, toolbar)
        create.setProperty("ui", "primary")
        create.setMaximumWidth(theme.px(220))
        create.clicked.connect(self._create)
        row.addWidget(create)
        self.add_content(toolbar)
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("sm"))
        articles = self.repo.fetch_articles()
        if self._query:
            needle = self._query.lower()
            articles = tuple(article for article in articles if needle in article.title.lower())
        self._count = len(articles)
        count = QLabel(S.HOME_COUNT.format(count=len(articles)), host)
        count.setProperty("role", "uppercase")
        layout.addWidget(count)
        for article in articles:
            channel = self.repo.fetch_channel(article.channel_id).channel
            card = ArticleCard(article, channel, parent=host)
            card.clicked.connect(lambda aid=article.id: self.open_route("article", aid))
            card.channel_clicked.connect(lambda cid=channel.id: self.open_route("channel", cid))
            layout.addWidget(card)
        if not articles:
            layout.addWidget(EmptyState(S.EMPTY_ARTICLES, S.EMPTY_HINT, icon_name="article", parent=host))
        layout.addStretch(1)
        self.add_content(host, 1)
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return self._count == 0 and bool(self._query)

    def _on_query(self, text: str) -> None:
        self._query = text.strip()
        self.reload()

    def _create(self) -> None:
        self.open_route("article_editor")


class ArticleScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, article_id: int = 0) -> None:
        super().__init__(ctx, title=S.ARTICLE_TITLE)
        self.article_id = article_id
        self._details: ArticleDetails | None = None
        self._expanded = False
        self._blocks_layout: QVBoxLayout | None = None
        self._blocks: tuple[ArticleBlock, ...] = ()
        self._vote = 0

    def create_loading_page(self) -> QWidget:
        return SkeletonDetail(parent=self)

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_article(self.article_id)
        self._details = details
        theme = active_theme()
        if details.is_not_found or details.article.is_deleted:
            self.ctx.host.set_header(S.ARTICLE_TITLE, S.ARTICLE_NOT_FOUND)
            wrapper = QWidget(self)
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("xl"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
            layout.addWidget(
                EmptyState(
                    S.ARTICLE_NOT_FOUND,
                    S.ARTICLE_DELETED if details.article.is_deleted else S.EMPTY_HINT,
                    icon_name="article",
                    parent=wrapper,
                )
            )
            layout.addStretch(1)
            self.add_content(wrapper, 1)
            return
        article = details.article
        channel = self.repo.fetch_channel(article.channel_id).channel
        self.ctx.host.set_header(S.ARTICLE_TITLE, channel.title)
        outer = QWidget(self)
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addStretch(1)
        column = QWidget(outer)
        column.setMaximumWidth(theme.px(780))
        column.setMinimumWidth(theme.px(520))
        layout = QVBoxLayout(column)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter")
        )
        layout.setSpacing(theme.space("m"))
        layout.addWidget(self._channel_header(article, channel))
        title = QLabel(article.title, column)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('episode_type_heading')['size_sp']))}px;"
            " font-weight: 700;"
        )
        layout.addWidget(title)
        byline = QLabel(
            f"{article.author} · {format_date(article.created_ts)}" + (" · " + S.PINNED if article.is_pinned else ""),
            column,
        )
        byline.setProperty("role", "tertiary")
        layout.addWidget(byline)
        self._blocks = article.blocks
        self._blocks_layout = QVBoxLayout()
        self._blocks_layout.setSpacing(theme.space("m"))
        self._render_blocks()
        layout.addLayout(self._blocks_layout)
        self._expand_button = QPushButton(S.ARTICLE_EXPAND, column)
        self._expand_button.setProperty("ui", "text")
        self._expand_button.clicked.connect(self._toggle_expand)
        self._expand_button.setVisible(len(self._blocks) > 4)
        layout.addWidget(self._expand_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._reaction_row(article, column))
        layout.addWidget(SectionHeader(S.ARTICLE_COMMENTS, action_text=S.SHOW_ALL, parent=column))
        for comment in details.comments[:3]:
            layout.addWidget(self._comment_preview(comment, column))
        layout.addWidget(self._comment_box(column))
        layout.addStretch(1)
        outer_layout.addWidget(column)
        outer_layout.addStretch(1)
        self.add_content(outer, 1)

    def _channel_header(self, article: Article, channel: Channel) -> QWidget:
        theme = active_theme()
        host = QFrame(self)
        host.setProperty("ui", "panel")
        layout = QHBoxLayout(host)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("m"))
        avatar = Avatar(channel.title, size=theme.semantic("list_avatar_size") - 8, seed=channel.seed)
        layout.addWidget(avatar)
        info = QVBoxLayout()
        title = QLabel(channel.title, host)
        title.setStyleSheet("font-weight: 600;")
        info.addWidget(title)
        meta = QLabel(format_date(article.created_ts), host)
        meta.setProperty("role", "tertiary")
        info.addWidget(meta)
        layout.addLayout(info, 1)
        subscribe = QPushButton(S.FEED_SUBSCRIBE, host)
        subscribe.setProperty("ui", "primary")
        subscribe.clicked.connect(lambda: self.notify(S.SUBSCRIBED))
        layout.addWidget(subscribe)
        more = QPushButton(S.MORE, host)
        more.setProperty("ui", "text")
        more.setIcon(icons.icon("more", "icon", 16))
        more.clicked.connect(lambda: self._article_menu(more))
        layout.addWidget(more)
        return host

    def _render_blocks(self) -> None:
        if self._blocks_layout is None:
            return
        while self._blocks_layout.count():
            item = self._blocks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        theme = active_theme()
        visible = self._blocks if self._expanded else self._blocks[:4]
        for block in visible:
            if block.kind == "paragraph":
                label = QLabel(block.text)
                label.setWordWrap(True)
                label.setProperty("role", "body")
                self._blocks_layout.addWidget(label)
            elif block.kind == "header":
                label = QLabel(block.text)
                label.setProperty("role", "section")
                label.setWordWrap(True)
                self._blocks_layout.addWidget(label)
            elif block.kind == "list":
                text = "\n".join(f"•  {item}" for item in block.items)
                label = QLabel(text)
                label.setWordWrap(True)
                label.setProperty("role", "body")
                self._blocks_layout.addWidget(label)
            elif block.kind == "quote":
                quote = QFrame()
                quote.setProperty("ui", "tertiary")
                quote_layout = QHBoxLayout(quote)
                margin = theme.space("m")
                quote_layout.setContentsMargins(margin, margin, margin, margin)
                bar = QFrame(quote)
                bar.setFixedWidth(theme.px(3))
                bar.setStyleSheet(f"background-color: {theme.color('accent')};")
                quote_layout.addWidget(bar)
                label = QLabel(block.text)
                label.setWordWrap(True)
                label.setProperty("role", "muted")
                quote_layout.addWidget(label, 1)
                self._blocks_layout.addWidget(quote)
            elif block.kind == "media":
                scroll = HScrollArea()
                scroll.setFixedHeight(theme.px(150))
                inner = QWidget()
                row = QHBoxLayout(inner)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(theme.space("sm"))
                for index in range(max(1, block.media_count)):
                    row.addWidget(MediaTile(index * 3 + 1, parent=inner))
                row.addStretch(1)
                scroll.setWidget(inner)
                self._blocks_layout.addWidget(scroll)
            elif block.kind == "embed":
                self._blocks_layout.addWidget(InfoBanner(S.ARTICLE_UNSUPPORTED, icon_name="warning"))
            else:
                self._blocks_layout.addWidget(InfoBanner(S.ARTICLE_UNSUPPORTED, icon_name="warning"))

    def _toggle_expand(self) -> None:
        self._expanded = not self._expanded
        if hasattr(self, "_expand_button"):
            self._expand_button.setText(S.ARTICLE_COLLAPSE if self._expanded else S.ARTICLE_EXPAND)
        self._render_blocks()

    def _reaction_row(self, article: Article, parent: QWidget) -> QWidget:
        theme = active_theme()
        host = QWidget(parent)
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        like = QPushButton(f"▲ {article.votes}", host)
        like.setProperty("ui", "outlined")
        dislike = QPushButton(f"▼ {max(0, article.votes // 5)}", host)
        dislike.setProperty("ui", "outlined")
        like.clicked.connect(lambda: self._vote_article(1))
        dislike.clicked.connect(lambda: self._vote_article(-1))
        layout.addWidget(like)
        layout.addWidget(dislike)
        comments = QLabel(comments_plural(article.comments_count), host)
        comments.setProperty("role", "muted")
        layout.addWidget(comments)
        reposts = QLabel(f"{S.ARTICLE_REPOSTS}: {article.reposts}", host)
        reposts.setProperty("role", "muted")
        layout.addWidget(reposts)
        layout.addStretch(1)
        return host

    def _vote_article(self, value: int) -> None:
        self._vote = value
        self.notify(S.ARTICLE_LIKE if value > 0 else S.ARTICLE_DISLIKE)

    def _comment_preview(self, comment, parent: QWidget) -> QWidget:
        theme = active_theme()
        host = QFrame(parent)
        host.setProperty("ui", "card")
        layout = QHBoxLayout(host)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("m"))
        layout.addWidget(Avatar(comment.author, size=theme.semantic("comment_avatar_size"), seed=comment.id))
        text = QVBoxLayout()
        header = QLabel(f"{comment.author} · {format_date(comment.timestamp)}", host)
        header.setProperty("role", "tertiary")
        text.addWidget(header)
        body = QLabel(S.COMMENTS_SPOILER_WARNING if comment.is_spoiler else comment.text, host)
        body.setWordWrap(True)
        text.addWidget(body)
        layout.addLayout(text, 1)
        return host

    def _comment_box(self, parent: QWidget) -> QWidget:
        theme = active_theme()
        host = QFrame(parent)
        host.setProperty("ui", "tertiary")
        layout = QVBoxLayout(host)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("xs"))
        top = QHBoxLayout()
        top.addWidget(QLabel(S.ARTICLE_SPOILER, host))
        top.addStretch(1)
        rules = QPushButton(S.ARTICLE_RULES, host)
        rules.setProperty("ui", "text")
        top.addWidget(rules)
        layout.addLayout(top)
        editor = QPlainTextEdit(host)
        editor.setPlaceholderText(S.ARTICLE_COMMENT_HINT)
        editor.setMaximumHeight(theme.px(90))
        layout.addWidget(editor)
        row = QHBoxLayout()
        row.addStretch(1)
        send = QPushButton(S.ARTICLE_WRITE_COMMENT, host)
        send.setProperty("ui", "primary")
        send.clicked.connect(lambda: self._send_comment(editor))
        row.addWidget(send)
        layout.addLayout(row)
        return host

    def _send_comment(self, editor: QPlainTextEdit) -> None:
        if editor.toPlainText().strip():
            editor.clear()
            self.notify(S.ARTICLE_COMMENT_SENT)

    def _article_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        share = menu.addAction(S.SHARE)
        hide = menu.addAction(S.ARTICLE_HIDE)
        report = menu.addAction(S.REPORT)
        menu.addSeparator()
        delete = menu.addAction(S.DELETE)
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == hide:
            self.notify(S.ARTICLE_HIDE)
        elif chosen == report:
            ReportDialog(S.ARTICLE_TITLE, parent=self).exec()
        elif chosen == delete:
            dialog = ConfirmDialog(S.ARTICLE_DELETE, S.DELETE_ALL_TEXT, confirm_text=S.DELETE, destructive=True, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.notify(S.ARTICLE_DELETED)
                self.ctx.host.go_back()


class ArticleEditorScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.ARTICLE_EDIT)
        self._title: QLineEdit | None = None
        self._body: QPlainTextEdit | None = None
        self._preview: QLabel | None = None

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("m"))
        toolbar = QHBoxLayout()
        title = QLabel(S.ARTICLE_EDIT, wrap)
        title.setProperty("role", "section")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        draft = QPushButton(S.ARTICLE_DRAFT, wrap)
        draft.setProperty("ui", "outlined")
        draft.clicked.connect(lambda: self.notify(S.ARTICLE_DRAFT_SAVED))
        toolbar.addWidget(draft)
        preview = QPushButton(S.ARTICLE_PREVIEW, wrap)
        preview.setProperty("ui", "outlined")
        preview.clicked.connect(self._preview_article)
        toolbar.addWidget(preview)
        publish = QPushButton(S.ARTICLE_SEND, wrap)
        publish.setProperty("ui", "primary")
        publish.clicked.connect(self._publish)
        toolbar.addWidget(publish)
        layout.addLayout(toolbar)
        self._title = QLineEdit(wrap)
        self._title.setPlaceholderText(S.ARTICLE_TITLE_FIELD)
        layout.addWidget(self._title)
        split = QHBoxLayout()
        split.setSpacing(theme.space("m"))
        self._body = QPlainTextEdit(wrap)
        self._body.setPlaceholderText(S.ARTICLE_TEXT_FIELD)
        self._body.setMinimumHeight(theme.px(320))
        split.addWidget(self._body, 1)
        side = QVBoxLayout()
        cover = QFrame(wrap)
        cover.setFixedSize(theme.px(260), theme.px(160))
        cover.setStyleSheet(
            f"background-color: {theme.color('surface_tertiary')};"
            f"border-radius: {theme.radius('collection_card')}px;"
        )
        side.addWidget(cover)
        self._preview = QLabel(S.ARTICLE_ALMOST_READY, wrap)
        self._preview.setWordWrap(True)
        self._preview.setProperty("role", "muted")
        side.addWidget(self._preview)
        side.addStretch(1)
        split.addLayout(side, 0)
        layout.addLayout(split, 1)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _preview_article(self) -> None:
        if self._preview is not None:
            title = self._title.text().strip() if self._title else ""
            body = self._body.toPlainText().strip() if self._body else ""
            self._preview.setText(f"{S.ARTICLE_ALMOST_READY}\n\n{title}\n{body[:240]}")

    def _publish(self) -> None:
        if self._title and self._title.text().strip():
            self.notify(S.ARTICLE_PUBLISHED)
            self.ctx.host.go_back()
        else:
            MessageDialog(S.ARTICLE_PREVIEW, S.AUTH_ERROR_EMPTY, parent=self).exec()
