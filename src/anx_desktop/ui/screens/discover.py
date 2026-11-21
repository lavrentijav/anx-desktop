"""Обзор: trending banners, quick entries, recommendations and community blocks."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Article, Channel, Collection, Comment, DiscoverData, InterestingCard, Release
from ..formatting import format_count
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ArticleCard,
    Avatar,
    ClickableFrame,
    CollectionCard,
    CompactReleaseCard,
    HScrollArea,
    InfoBanner,
    SectionHeader,
    SkeletonSections,
    paint_placeholder,
)
from ..widgets.dialogs import MessageDialog
from ..widgets.images import images, paint_image
from .base import BaseScreen


class BannerCard(ClickableFrame):
    def __init__(self, card: InterestingCard, *, width: int, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.card = card
        self._pixmap = None
        self.setFixedSize(width, height)
        self.setAccessibleName(card.title)
        images.load(card.image_url, self._on_image)

    def _on_image(self, pixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        radius = theme.radius("collection_card")
        if self._pixmap is not None and not self._pixmap.isNull():
            paint_image(painter, rect, self._pixmap, radius)
        else:
            paint_placeholder(painter, rect, seed=self.card.seed, radius=radius)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        dark = QColor(theme.color("text_primary"))
        dark.setAlpha(35)
        darker = QColor(theme.color("text_primary"))
        darker.setAlpha(225)
        gradient.setColorAt(0.25, dark)
        gradient.setColorAt(1.0, darker)
        painter.setClipRect(rect)
        painter.fillRect(rect, gradient)
        painter.setPen(theme.qcolor("background"))
        title_font = theme.font("card_title")
        title_font.setPixelSize(theme.px(16))
        title_font.setWeight(QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.drawText(
            rect.adjusted(theme.space("l"), 0, -theme.space("l"), -theme.space("xxl")),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            self.card.title,
        )
        painter.setPen(theme.qcolor("background"))
        desc_font = theme.font("caption")
        desc_font.setPixelSize(theme.px(12))
        painter.setFont(desc_font)
        painter.drawText(
            rect.adjusted(theme.space("l"), 0, -theme.space("l"), -theme.space("m")),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            self.card.description,
        )
        if self.underMouse():
            painter.setBrush(theme.qcolor("accent_soft_20"))
            painter.setPen(QPen(theme.qcolor("accent"), 1))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), theme.radius("collection_card"), theme.radius("collection_card"))


class CommentMiniCard(QFrame):
    def __init__(self, comment: Comment, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "card")
        self.setFixedWidth(theme.px(300))
        self.setMinimumHeight(theme.px(130))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
        header = QHBoxLayout()
        header.setSpacing(theme.space("sm"))
        header.addWidget(Avatar(comment.author, size=theme.semantic("list_avatar_size") - 12, seed=comment.id))
        name = QLabel(comment.author, self)
        name.setProperty("role", "body")
        header.addWidget(name)
        header.addStretch(1)
        if comment.is_verified:
            check = QLabel(self)
            check.setPixmap(icons.pixmap("verified", "icon_alt", 14))
            header.addWidget(check)
        layout.addLayout(header)
        text = QLabel(comment.text, self)
        text.setWordWrap(True)
        text.setProperty("role", "muted")
        layout.addWidget(text)
        votes = QLabel(f"+{comment.votes} · {S.FEED_COMMENTS}", self)
        votes.setProperty("role", "tertiary")
        layout.addWidget(votes)
        layout.addStretch(1)


class DiscoverScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_DISCOVER)
        self._data: DiscoverData | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonSections(parent=self)

    def populate(self) -> None:
        self.reset_content()
        data = self.repo.fetch_discover()
        self._data = data
        theme = active_theme()
        banner_w = theme.px(float(theme.tokens.layout("discover_banner_width_dp")))
        banner_h = theme.px(float(theme.tokens.layout("discover_banner_height_dp")))
        trending = self._carousel(
            [self._banner(card, banner_w, banner_h) for card in data.trending],
            height=banner_h + theme.space("xl"),
        )
        self.add_content(self._section("discover_trending", S.DISCOVER_TRENDING))
        self.add_content(trending)

        quick_host = QWidget(self)
        quick_row = QHBoxLayout(quick_host)
        quick_row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        quick_row.setSpacing(theme.space("sm"))
        icons_for = {
            "discover_new": "star",
            "schedule": "calendar",
            "updates": "list",
            "collections": "collection",
            "filter": "filter",
        }
        routes = {
            "discover_new": ("home", None),
            "schedule": ("schedule", None),
            "updates": ("updates", None),
            "collections": ("collections", None),
            "filter": ("filter", None),
        }
        for key, label in data.quick_links:
            button = QPushButton(label, quick_host)
            button.setProperty("ui", "grey")
            button.setIcon(icons.icon(icons_for.get(key, "chevron_right"), "icon_alt", 18))
            button.setIconSize(QSize(18, 18))
            button.setMinimumHeight(theme.semantic("button_height_tiny"))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            route, payload = routes.get(key, ("home", None))
            button.clicked.connect(lambda _checked=False, r=route, p=payload: self.open_route(r, p))
            quick_row.addWidget(button)
        quick_row.addStretch(1)
        self.add_content(quick_host)

        recommendations = SectionHeader(
            S.DISCOVER_RECOMMENDATIONS,
            S.DISCOVER_BASED_ON_VOTES,
            S.SHOW_ALL,
            parent=self,
        )
        recommendations.show_all.connect(lambda: self.open_route("list", {"kind": "recommended", "title": S.DISCOVER_RECOMMENDATIONS}))
        self.add_content(recommendations)
        if data.recommendations:
            self.add_content(
                self._carousel(
                    [self._compact(release) for release in data.recommendations],
                    height=theme.px(235),
                )
            )
        else:
            info = InfoBanner(S.DISCOVER_EMPTY_RECOMMENDATIONS, parent=self)
            info.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm"))
            self.add_content(info)

        discussed = SectionHeader(S.DISCOVER_DISCUSSED, parent=self)
        self.add_content(discussed)
        article_cards = []
        for article in data.discussed:
            channel = self.repo.fetch_channel(article.channel_id).channel
            card = ArticleCard(article, channel, parent=self)
            card.setFixedWidth(theme.px(360))
            card.clicked.connect(lambda aid=article.id: self.open_route("article", aid))
            card.channel_clicked.connect(lambda cid=channel.id: self.open_route("channel", cid))
            article_cards.append(card)
        self.add_content(self._carousel(article_cards, height=theme.px(235)))

        social = SectionHeader(S.DISCOVER_SOCIAL, parent=self)
        social.set_action_visible(False)
        self.add_content(social)
        social_host = QWidget(self)
        social_row = QHBoxLayout(social_host)
        social_row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm"))
        social_row.setSpacing(theme.space("sm"))
        for label, _key in data.social_links:
            button = QPushButton(label, social_host)
            button.setProperty("ui", "grey")
            button.setIcon(icons.icon("globe", "icon_alt", 16))
            button.clicked.connect(lambda _checked=False, name=label: MessageDialog(name, S.ASSET_DISCLAIMER, parent=self).exec())
            social_row.addWidget(button)
        social_row.addStretch(1)
        self.add_content(social_host)

        watching = SectionHeader(S.DISCOVER_WATCHING_NOW, parent=self)
        watching.show_all.connect(lambda: self.open_route("list", {"kind": "watching", "title": S.DISCOVER_WATCHING_NOW}))
        self.add_content(watching)
        self.add_content(
            self._carousel(
                [self._compact(release) for release in data.watching_now],
                height=theme.px(235),
            )
        )

        collections = SectionHeader(S.DISCOVER_COLLECTIONS_WEEK, parent=self)
        collections.show_all.connect(lambda: self.open_route("collections"))
        self.add_content(collections)
        collection_cards = []
        for collection in data.collections_week[:4]:
            card = CollectionCard(
                collection,
                width=theme.px(320),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=self,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            collection_cards.append(card)
        self.add_content(self._carousel(collection_cards, height=theme.px(230)))

        comments = SectionHeader(S.DISCOVER_COMMENTS_WEEK, parent=self)
        comments.set_action_visible(False)
        self.add_content(comments)
        self.add_content(
            self._carousel([CommentMiniCard(comment, parent=self) for comment in data.comments_week], height=theme.px(160))
        )

        sponsor = QFrame(self)
        sponsor.setProperty("ui", "card")
        sponsor_layout = QHBoxLayout(sponsor)
        margin = theme.space("l")
        sponsor_layout.setContentsMargins(margin, margin, margin, margin)
        sponsor_layout.setSpacing(theme.space("m"))
        text = QVBoxLayout()
        title = QLabel(S.DISCOVER_SPONSORSHIP, sponsor)
        title.setProperty("role", "section")
        text.addWidget(title)
        description = QLabel(data.sponsorship_text or S.DISCOVER_SPONSORSHIP_TEXT, sponsor)
        description.setProperty("role", "muted")
        description.setWordWrap(True)
        text.addWidget(description)
        sponsor_layout.addLayout(text, 1)
        action = QPushButton(S.DISCOVER_SPONSORSHIP_ACTION, sponsor)
        action.setProperty("ui", "outlined")
        action.clicked.connect(lambda: MessageDialog(S.DISCOVER_SPONSORSHIP, S.DISCOVER_SPONSORSHIP_TEXT, parent=self).exec())
        sponsor_layout.addWidget(action)
        wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        wrapper_layout.addWidget(sponsor)
        self.add_content(wrapper)
        self.add_stretch(1)

    # ----------------------------------------------------------------- helpers
    def _section(self, key: str, title: str) -> SectionHeader:
        header = SectionHeader(title, parent=self)
        header.set_action_visible(key == "discover_recommendations")
        return header

    def _banner(self, card: InterestingCard, width: int, height: int) -> BannerCard:
        widget = BannerCard(card, width=width, height=height, parent=self)
        widget.clicked.connect(lambda: MessageDialog(card.title, card.description, parent=self).exec())
        return widget

    def _compact(self, release: Release) -> CompactReleaseCard:
        card = CompactReleaseCard(release, parent=self)
        card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
        card.context_requested.connect(lambda _pos, rid=release.id: self.open_route("release", rid))
        return card

    def _carousel(self, widgets: list[QWidget], *, height: int) -> HScrollArea:
        theme = active_theme()
        area = HScrollArea(self)
        area.setFixedHeight(height)
        host = QWidget()
        host.setProperty("ui", "scrollHost")
        row = QHBoxLayout(host)
        row.setContentsMargins(
            theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("xs")
        )
        row.setSpacing(theme.semantic("grid_gap"))
        for widget in widgets:
            row.addWidget(widget)
        row.addStretch(1)
        area.setWidget(host)
        return area
