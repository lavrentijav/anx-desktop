"""Poster-driven cards and list rows (8.5.2 proportions and radii)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Article, Channel, Collection, Release
from ..formatting import episodes_progress, format_date, format_rating
from ..strings import S
from ..theme import active_theme
from .common import Avatar, ClickableFrame, IconButton, TextBadge, paint_placeholder
from .images import images, paint_image


def _meta_label(text: str, parent: QWidget) -> QLabel:
    theme = active_theme()
    label = QLabel(text, parent)
    label.setProperty("role", "muted")
    label.setStyleSheet(
        f"font-size: {theme.px(float(theme.tokens.typography('caption')['size_sp']) + 1)}px;"
    )
    return label


_LIST_STATUS = {
    1: ("смотрю", "status_watching"),
    2: ("в планах", "status_planned"),
    3: ("просмотрено", "status_completed"),
    4: ("отложено", "status_on_hold"),
    5: ("брошено", "status_dropped"),
}


class PosterWidget(QWidget):
    """Fixed-ratio poster placeholder (no artwork is copied from the APK)."""

    def __init__(
        self,
        release: Release,
        *,
        width: int,
        height: int,
        radius_name: str = "poster_card",
        show_age: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.release = release
        self._width = width
        self._height = height
        self._radius_name = radius_name
        self._show_age = show_age
        self._pixmap = None
        self.setFixedSize(width, height)
        self.setAccessibleName(release.title)
        active_theme().changed.connect(self.update)
        images.load(release.image_url, self._on_image)

    def _on_image(self, pixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = theme.radius(self._radius_name)
        if self._pixmap is not None and not self._pixmap.isNull():
            paint_image(painter, rect, self._pixmap, radius)
        else:
            paint_placeholder(
                painter,
                rect,
                seed=self.release.seed,
                radius=radius,
            )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(theme.qcolor("border_image"), 1))
        painter.drawRoundedRect(rect, radius, radius)
        if self.release.is_favorite:
            size = max(14, self.width() // 7)
            painter.setBrush(theme.qcolor("rating_favorite"))
            painter.setPen(Qt.PenStyle.NoPen)
            star = icons.pixmap("star", "rating_favorite", size)
            painter.drawPixmap(self.width() - size - theme.space("xs"), theme.space("xs"), star)
        if self._show_age and self.release.age_rating:
            font = theme.font("caption")
            font.setPixelSize(max(10, int(self.width() * 0.09)))
            painter.setFont(font)
            metrics = painter.fontMetrics()
            text = self.release.age_rating
            badge_w = metrics.horizontalAdvance(text) + theme.space("sm")
            badge_h = metrics.height() + theme.space("xxs")
            badge = QRectF(
                theme.space("xs"),
                self.height() - badge_h - theme.space("xs"),
                badge_w,
                badge_h,
            )
            painter.setBrush(theme.qcolor("age_rating_background"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge, theme.radius("age_rating"), theme.radius("age_rating"))
            painter.setPen(theme.qcolor("age_rating_text"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, text)
        status = _LIST_STATUS.get(self.release.list_status)
        if status is not None and self.width() >= 80 and self.height() >= 60:
            label, role = status
            font = theme.font("caption")
            font.setPixelSize(max(10, int(self.width() * 0.075)))
            painter.setFont(font)
            metrics = painter.fontMetrics()
            margin = theme.space("xs")
            badge_h = metrics.height() + theme.space("xxs")
            badge = QRectF(
                margin,
                self.height() - badge_h - margin,
                self.width() - margin * 2,
                badge_h,
            )
            painter.setBrush(theme.qcolor(role))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge, theme.radius("age_rating"), theme.radius("age_rating"))
            painter.setPen(theme.qcolor("text_primary"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)


class _HoverCard(ClickableFrame):
    """Clickable frame with hover/selection feedback from tokens."""

    def __init__(self, radius_name: str = "collection_card", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._radius_name = radius_name
        self._hovered = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        if not self._hovered:
            return
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        radius = theme.radius(self._radius_name)
        painter.setBrush(theme.qcolor("accent_soft_10"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


class PosterCard(_HoverCard):
    """Grid release card: poster + 13 sp title + 12 sp meta."""

    def __init__(
        self,
        release: Release,
        *,
        poster_width: int,
        poster_height: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("poster_card", parent)
        theme = active_theme()
        self.release = release
        self.setMinimumWidth(poster_width)
        self.setMaximumWidth(poster_width + theme.space("l"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        self.poster = PosterWidget(release, width=poster_width, height=poster_height, parent=self)
        layout.addWidget(self.poster)
        title = QLabel(release.title, self)
        title.setProperty("role", "body")
        title.setFont(theme.font("card_title"))
        title.setWordWrap(True)
        title.setFixedHeight(title.fontMetrics().lineSpacing() * 2)
        title.setToolTip(release.title)
        layout.addWidget(title)
        meta_parts: list[str] = []
        episode_label = episodes_progress(
            release.episodes_released, release.episodes_total
        )
        if episode_label:
            meta_parts.append(episode_label)
        if release.grade > 0:
            meta_parts.append(f"★ {format_rating(release.grade)}")
        meta = _meta_label(" · ".join(meta_parts), self)
        meta.setVisible(bool(meta_parts))
        layout.addWidget(meta)
        self.setAccessibleName(f"{release.title}, {S.RELEASE_RATING} {format_rating(release.grade)}")


class CompactReleaseCard(_HoverCard):
    """114x153 poster used in horizontal carousels."""

    def __init__(self, release: Release, *, parent: QWidget | None = None) -> None:
        width, height = active_theme().tokens.compact_poster_size()
        super().__init__("poster_card", parent)
        theme = active_theme()
        self.release = release
        self.setFixedWidth(width + theme.space("sm"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        self.poster = PosterWidget(release, width=width, height=height, parent=self)
        layout.addWidget(self.poster)
        title = QLabel(release.title, self)
        title.setWordWrap(True)
        title.setFont(theme.font("card_title"))
        title.setFixedHeight(title.fontMetrics().lineSpacing() * 2)
        title.setToolTip(release.title)
        layout.addWidget(title)
        parts: list[str] = []
        if release.grade > 0:
            parts.append(f"★ {format_rating(release.grade)}")
        if release.year:
            parts.append(str(release.year))
        meta = _meta_label(" · ".join(parts), self)
        meta.setVisible(bool(parts))
        layout.addWidget(meta)
        layout.addStretch(1)
        self.setAccessibleName(release.title)


class ReleaseRow(_HoverCard):
    """List row with a 100x134 poster, title, meta and description."""

    favorite_toggled = Signal(int)
    more_clicked = Signal(int)

    def __init__(self, release: Release, *, parent: QWidget | None = None) -> None:
        super().__init__("poster_card", parent)
        theme = active_theme()
        self.release = release
        width, height = theme.tokens.list_poster_size()
        self.setMinimumHeight(height + theme.space("l"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            theme.semantic("list_row_padding_horizontal"),
            theme.semantic("list_row_padding_vertical"),
            theme.semantic("list_row_padding_end"),
            theme.semantic("list_row_padding_vertical"),
        )
        layout.setSpacing(theme.semantic("list_poster_to_text_gap"))
        self.poster = PosterWidget(release, width=width, height=height, parent=self)
        layout.addWidget(self.poster, 0, Qt.AlignmentFlag.AlignTop)
        content = QVBoxLayout()
        content.setSpacing(theme.space("xs"))
        title_row = QHBoxLayout()
        title_row.setSpacing(theme.space("sm"))
        title = QLabel(release.title, self)
        title.setProperty("role", "body")
        title.setFont(theme.font("list_title"))
        title.setWordWrap(True)
        title.setFixedHeight(title.fontMetrics().lineSpacing() * 2)
        title.setToolTip(release.title)
        title_row.addWidget(title, 1)
        favorite = IconButton(
            "heart" if release.is_favorite else "heart_outline",
            role="rating_favorite" if release.is_favorite else "icon",
            size=18,
            tooltip=S.RELEASE_FAVORITES,
            parent=self,
        )
        favorite.clicked.connect(lambda: self.favorite_toggled.emit(self.release.id))
        title_row.addWidget(favorite)
        more = IconButton("more", size=20, tooltip=S.TOOLTIP_MORE, parent=self)
        more.clicked.connect(lambda: self.more_clicked.emit(self.release.id))
        title_row.addWidget(more)
        content.addLayout(title_row)
        meta = QHBoxLayout()
        meta.setSpacing(theme.space("xs"))
        meta_parts: list[str] = []
        episode_label = episodes_progress(
            release.episodes_released, release.episodes_total
        )
        if episode_label:
            meta_parts.append(episode_label)
        if release.grade > 0:
            meta_parts.append(f"★ {format_rating(release.grade)}")
        meta_label = _meta_label(" · ".join(meta_parts), self)
        meta_label.setVisible(bool(meta_parts))
        meta.addWidget(meta_label)
        status = _meta_label(release.status, self)
        status.setVisible(bool(release.status))
        meta.addWidget(status)
        if release.is_favorite:
            star = QLabel(self)
            star.setPixmap(icons.pixmap("star", "rating_favorite", 14))
            meta.addWidget(star)
        meta.addStretch(1)
        content.addLayout(meta)
        description = QLabel(release.description, self)
        description.setProperty("role", "tertiary")
        description.setWordWrap(True)
        description.setMaximumHeight(theme.px(58))
        description.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('description')['size_sp']))}px;"
        )
        content.addWidget(description)
        content.addStretch(1)
        layout.addLayout(content, 1)
        self.setAccessibleName(release.title)


class CollectionCard(_HoverCard):
    """Collection cover with header strip, badges and a 20 sp overlay title."""

    def __init__(
        self,
        collection: Collection,
        *,
        width: int = 320,
        height: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        theme = active_theme()
        height = height or int(theme.tokens.layout("collection_card_height_dp"))
        super().__init__("collection_card", parent)
        self.collection = collection
        self._card_height = height
        self._strip = theme.radius("collection_header_strip_top")
        self.setMinimumWidth(260)
        self.setMaximumWidth(480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(height + self._strip + theme.space("xs"))
        self.setAccessibleName(collection.title)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        strip = QRectF(
            theme.space("m"),
            0,
            self.width() - theme.space("xl"),
            self._strip + theme.radius("collection_card"),
        )
        painter.setBrush(theme.qcolor("collection_card_header"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            strip, theme.radius("collection_card"), theme.radius("collection_card")
        )
        cover = QRectF(0, self._strip + theme.space("xxs"), self.width(), self._card_height)
        paint_placeholder(
            painter,
            cover,
            seed=self.collection.seed,
            radius=theme.radius("collection_card"),
            accent=self.collection.is_favorite,
        )
        # Bottom gradient for the title (colors derived from the poster tokens).
        from PySide6.QtGui import QLinearGradient

        gradient = QLinearGradient(cover.topLeft(), cover.bottomLeft())
        transparent = QColor(theme.color("text_primary"))
        transparent.setAlpha(0)
        opaque = QColor(theme.color("text_primary"))
        opaque.setAlpha(235)
        gradient.setColorAt(0.45, transparent)
        gradient.setColorAt(1.0, opaque)
        painter.setClipRect(cover)
        painter.fillRect(cover, gradient)
        # Badges: lock / comments / favorites.
        badge_font = theme.font("caption")
        badge_font.setPixelSize(theme.px(11))
        painter.setFont(badge_font)
        metrics = painter.fontMetrics()
        badges: list[tuple[str, str]] = []
        if self.collection.is_private:
            badges.append(("lock", ""))
        badges.append(("comment", str(self.collection.comments_count)))
        badges.append(("heart", str(self.collection.favorites_count)))
        x = cover.right() - theme.space("m")
        for icon_name, value in reversed(badges):
            text_width = metrics.horizontalAdvance(value) if value else 0
            badge_w = theme.space("xl") + text_width
            badge_h = theme.semantic("tag_height")
            x -= badge_w
            badge_rect = QRectF(x, cover.top() + theme.space("m"), badge_w, badge_h)
            badge_color = QColor(theme.color("surface_secondary"))
            badge_color.setAlpha(215)
            painter.setBrush(badge_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, theme.radius("tag"), theme.radius("tag"))
            painter.drawPixmap(
                int(badge_rect.left() + theme.space("xs")),
                int(badge_rect.center().y() - 8),
                icons.pixmap(icon_name, "text_primary", 16),
            )
            if value:
                painter.setPen(theme.qcolor("text_primary"))
                painter.drawText(
                    badge_rect.adjusted(theme.space("l"), 0, -theme.space("xs"), 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    value,
                )
            x -= theme.space("xs")
        # Title overlay.
        title_font = theme.font("card_collection_title")
        title_font.setWeight(QFont.Weight.Medium)
        painter.setFont(title_font)
        title_rect = QRectF(
            theme.space("m"),
            cover.bottom() - theme.px(78),
            cover.width() - theme.space("xl"),
            theme.px(66),
        )
        painter.setPen(theme.qcolor("background"))
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            self.collection.title,
        )
        if self._hovered:
            painter.setBrush(theme.qcolor("accent_soft_10"))
            painter.setPen(QPen(theme.qcolor("accent"), 1))
            painter.drawRoundedRect(
                QRectF(0.5, self._strip, self.width() - 1, self._card_height - 0.5),
                theme.radius("collection_card"),
                theme.radius("collection_card"),
            )


class ArticleCard(_HoverCard):
    """Feed card: channel header + title + preview + reaction counters."""

    channel_clicked = Signal(int)
    context_requested = Signal(int, object)

    def __init__(self, article: Article, channel: Channel, *, parent: QWidget | None = None) -> None:
        super().__init__("collection_card", parent)
        theme = active_theme()
        self.article = article
        self.channel = channel
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("l"), theme.space("m"), theme.space("l"), theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        header = QHBoxLayout()
        header.setSpacing(theme.space("sm"))
        avatar = Avatar(channel.title, size=theme.semantic("list_avatar_size") - 8, seed=channel.seed)
        header.addWidget(avatar)
        channel_label = QLabel(channel.title, self)
        channel_label.setProperty("role", "body")
        channel_label.setStyleSheet("font-weight: 500;")
        header.addWidget(channel_label)
        if channel.is_verified:
            verified = QLabel(self)
            verified.setPixmap(icons.pixmap("verified", "icon_alt", 16))
            header.addWidget(verified)
        header.addStretch(1)
        date = QLabel(format_date(article.created_ts), self)
        date.setProperty("role", "tertiary")
        header.addWidget(date)
        if article.is_pinned:
            pin = QLabel(S.PINNED, self)
            pin.setProperty("role", "tertiary")
            header.addWidget(pin)
        more = IconButton("more", size=18, tooltip=S.TOOLTIP_MORE, parent=self)
        more.clicked.connect(
            lambda: self.context_requested.emit(self.article.id, more.mapToGlobal(more.rect().bottomLeft()))
        )
        header.addWidget(more)
        layout.addLayout(header)
        title = QLabel(article.title, self)
        title.setProperty("role", "section")
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('screen_title')['size_sp']))}px;"
            " font-weight: 600;"
        )
        layout.addWidget(title)
        paragraph = next((block.text for block in article.blocks if block.kind == "paragraph"), "")
        preview = QLabel(paragraph, self)
        preview.setProperty("role", "muted")
        preview.setWordWrap(True)
        preview.setMaximumHeight(theme.px(60))
        layout.addWidget(preview)
        footer = QHBoxLayout()
        footer.setSpacing(theme.space("l"))
        for icon_name, value in (
            ("like", article.votes),
            ("comment", article.comments_count),
            ("repost", article.reposts),
        ):
            icon_label = QLabel(self)
            icon_label.setPixmap(icons.pixmap(icon_name, "icon", 16))
            footer.addWidget(icon_label)
            count = QLabel(str(value), self)
            count.setProperty("role", "tertiary")
            footer.addWidget(count)
        footer.addStretch(1)
        read = QLabel(S.ARTICLE_EXPAND, self)
        read.setProperty("role", "accent")
        footer.addWidget(read)
        layout.addLayout(footer)
        self.setAccessibleName(article.title)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(theme.qcolor("surface"))
        painter.setPen(
            QPen(theme.qcolor("accent") if self._hovered else theme.qcolor("border_soft"), 1)
        )
        radius = theme.radius("collection_card")
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)
