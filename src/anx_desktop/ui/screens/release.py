"""Релиз: two-column detail with rating, badges, collections and comments."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Badge, Comment, ReleaseDetails
from ..formatting import episodes_progress, format_date, format_rating, voices
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    Avatar,
    ClickableFrame,
    CollectionCard,
    CompactReleaseCard,
    HScrollArea,
    InfoBanner,
    PosterWidget,
    RatingSummary,
    SectionHeader,
    SkeletonDetail,
    StarRating,
    TextBadge,
    paint_placeholder,
)
from ..widgets.dialogs import MessageDialog, ReportDialog
from ..widgets.images import images, paint_image
from .base import BaseScreen


class FrameTile(ClickableFrame):
    def __init__(
        self,
        seed: int,
        *,
        image_url: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._seed = seed
        self._pixmap = None
        self.setFixedSize(theme.px(180), theme.px(101))
        if image_url:
            images.load(image_url, self._on_image)

    def _on_image(self, pixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        radius = theme.radius("poster_card")
        if self._pixmap is not None and not self._pixmap.isNull():
            paint_image(painter, rect, self._pixmap, radius)
        else:
            paint_placeholder(painter, rect, seed=self._seed, radius=radius)


class BadgeTile(QFrame):
    def __init__(self, badge: Badge, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "card")
        self.setFixedWidth(theme.px(190))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        icon = QLabel(self)
        icon.setPixmap(icons.pixmap("badge", "icon_alt", 32))
        layout.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        name = QLabel(badge.name, self)
        name.setStyleSheet("font-weight: 500;")
        text.addWidget(name)
        rarity = QLabel(badge.rarity.capitalize(), self)
        rarity.setProperty("role", "tertiary")
        text.addWidget(rarity)
        layout.addLayout(text, 1)


class CommentPreview(QFrame):
    def __init__(self, comment: Comment, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
        layout.setSpacing(theme.space("m"))
        layout.addWidget(Avatar(comment.author, size=theme.semantic("comment_avatar_size"), seed=comment.id), 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        header = QHBoxLayout()
        name = QLabel(comment.author, self)
        name.setStyleSheet("font-weight: 500;")
        header.addWidget(name)
        if comment.is_verified:
            check = QLabel(self)
            check.setPixmap(icons.pixmap("verified", "icon_alt", 14))
            header.addWidget(check)
        header.addStretch(1)
        date = QLabel(format_date(comment.timestamp), self)
        date.setProperty("role", "tertiary")
        header.addWidget(date)
        text.addLayout(header)
        body = QLabel(S.COMMENTS_SPOILER_WARNING if comment.is_spoiler else comment.text, self)
        body.setWordWrap(True)
        body.setProperty("role", "muted")
        text.addWidget(body)
        footer = QLabel(f"{comment.votes:+d} · {S.COMMENTS_REPLY}", self)
        footer.setProperty("role", "tertiary")
        text.addWidget(footer)
        layout.addLayout(text, 1)


class ReleaseScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, release_id: int = 0) -> None:
        super().__init__(ctx, title=S.RELEASE_SCREEN_TITLE)
        self.release_id = release_id
        self._details: ReleaseDetails | None = None
        self._expanded = False

    def create_loading_page(self) -> QWidget:
        return SkeletonDetail(parent=self)

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_release(self.release_id)
        self._details = details
        release = details.release
        self.title = release.title
        self.ctx.host.set_header(S.RELEASE_SCREEN_TITLE, release.title)
        theme = active_theme()
        page = QWidget(self)
        layout = QHBoxLayout(page)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter")
        )
        layout.setSpacing(theme.space("xxl"))
        layout.addWidget(self._build_left(release, details), 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._build_right(release, details), 1)
        self.add_content(page, 1)

    # -------------------------------------------------------------------- left
    def _build_left(self, release, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        left = QFrame(self)
        left.setProperty("ui", "panel")
        left.setFixedWidth(theme.px(310))
        layout = QVBoxLayout(left)
        layout.setContentsMargins(theme.space("l"), theme.space("l"), theme.space("l"), theme.space("l"))
        layout.setSpacing(theme.space("m"))
        poster_w, poster_h = 270, 382
        poster = PosterWidget(
            release,
            width=theme.px(poster_w),
            height=theme.px(poster_h),
            radius_name="release_detail_poster",
            show_age=True,
            parent=left,
        )
        layout.addWidget(poster, 0, Qt.AlignmentFlag.AlignHCenter)
        play = QPushButton(S.RELEASE_WATCH, left)
        play.setProperty("ui", "primary")
        play.setIcon(icons.icon("play", "on_accent", 20))
        play.setMinimumHeight(theme.semantic("button_height_tiny"))
        play.clicked.connect(lambda: self.open_route("episodes", release.id))
        layout.addWidget(play)
        secondary = QHBoxLayout()
        secondary.setSpacing(theme.space("sm"))
        favorite = QPushButton(S.RELEASE_FAVORITES, left)
        favorite.setProperty("ui", "outlined")
        favorite.setIcon(icons.icon("heart" if release.is_favorite else "heart_outline", "icon_alt", 16))
        favorite.clicked.connect(lambda: self.notify(S.MOVED_TO_FAVORITES))
        secondary.addWidget(favorite, 1)
        more = QPushButton(S.MORE, left)
        more.setProperty("ui", "outlined")
        more.setIcon(icons.icon("more", "icon", 16))
        more.clicked.connect(lambda: self._more_menu(more))
        secondary.addWidget(more)
        layout.addLayout(secondary)
        status = QPushButton(S.RELEASE_STATUS_NOT_WATCHING, left)
        status.setProperty("ui", "tag")
        status.setIcon(icons.icon("chevron_down", "icon", 14))
        status.clicked.connect(lambda: MessageDialog(S.RELEASE_ACTIONS, S.RELEASE_STATUS_NOT_WATCHING, parent=self).exec())
        layout.addWidget(status)
        rating = QLabel(f"★ {format_rating(release.grade)}  ·  {voices(release.vote_count)}", left)
        rating.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(rating)
        structure = QLabel(
            " · ".join(
                part
                for part in (
                    episodes_progress(release.episodes_released, release.episodes_total),
                    str(release.year) if release.year else "",
                    release.age_rating,
                )
                if part
            ),
            left,
        )
        structure.setProperty("role", "tertiary")
        structure.setWordWrap(True)
        layout.addWidget(structure)
        layout.addStretch(1)
        return left

    # ------------------------------------------------------------------- right
    def _build_right(self, release, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        right = QWidget(self)
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("m"))
        title = QLabel(release.title, right)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"font-size: {theme.px(28)}px; font-weight: 700;"
        )
        layout.addWidget(title)
        original = QLabel(release.original_title, right)
        original.setProperty("role", "muted")
        layout.addWidget(original)
        chips = QHBoxLayout()
        chips.setSpacing(theme.space("sm"))
        age = TextBadge(release.age_rating, role="muted", background="age_rating_background", radius=4, parent=right)
        age.setStyleSheet(
            f"background-color: {theme.color('age_rating_background')};"
            f"color: {theme.color('age_rating_text')};"
            f"border-radius: {theme.radius('age_rating')}px;"
            f"padding: {theme.space('xxs')}px {theme.space('xs')}px;"
        )
        chips.addWidget(age)
        for text in (release.status, release.country, f"{release.year}", release.studio):
            badge = TextBadge(text, parent=right)
            chips.addWidget(badge)
        chips.addStretch(1)
        layout.addLayout(chips)
        actions = QHBoxLayout()
        actions.setSpacing(theme.space("sm"))
        watch = QPushButton(S.RELEASE_WATCH, right)
        watch.setProperty("ui", "primary")
        watch.setIcon(icons.icon("play", "on_accent", 20))
        watch.clicked.connect(lambda: self.open_route("episodes", release.id))
        actions.addWidget(watch)
        actions_button = QPushButton(S.RELEASE_ACTIONS, right)
        actions_button.setProperty("ui", "outlined")
        actions_button.setIcon(icons.icon("chevron_down", "icon", 16))
        actions_button.clicked.connect(lambda: self._more_menu(actions_button))
        actions.addWidget(actions_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        if release.is_adult:
            warning = InfoBanner(S.ADULT_WARNING, icon_name="warning", title=release.age_rating, parent=right)
            layout.addWidget(warning)

        meta = QFrame(right)
        meta.setProperty("ui", "tertiary")
        meta_layout = QGridLayout(meta)
        margin = theme.space("m")
        meta_layout.setContentsMargins(margin, margin, margin, margin)
        meta_layout.setHorizontalSpacing(theme.space("xl"))
        meta_layout.setVerticalSpacing(theme.space("xs"))
        rows = (
            ("globe", S.RELEASE_COUNTRY, release.country),
            ("list", S.RELEASE_EPISODES, episodes_progress(release.episodes_released, release.episodes_total)),
            ("calendar", S.RELEASE_SCHEDULE, release.schedule),
            ("channel", S.RELEASE_STUDIO, release.studio),
            ("article", S.RELEASE_SOURCE, release.source),
            ("collection", S.RELEASE_GENRES, ", ".join(release.genres)),
            ("info", S.FILTER_STATUS, release.status),
        )
        rows = tuple(row for row in rows if str(row[2]).strip())
        for index, (icon_name, label, value) in enumerate(rows):
            cell = QWidget(meta)
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(theme.space("sm"))
            icon = QLabel(cell)
            icon.setPixmap(icons.pixmap(icon_name, "icon", 18))
            cell_layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
            text = QLabel(f"{label} · {value}", cell)
            text.setWordWrap(True)
            cell_layout.addWidget(text, 1)
            meta_layout.addWidget(cell, index // 2, index % 2)
        layout.addWidget(meta)

        description = QLabel(release.description, right)
        description.setWordWrap(True)
        description.setProperty("role", "body")
        description.setMaximumHeight(theme.px(76))
        self._description = description
        layout.addWidget(description)
        expand = QPushButton(S.RELEASE_EXPAND, right)
        expand.setProperty("ui", "text")
        expand.clicked.connect(lambda: self._toggle_description(expand))
        layout.addWidget(expand, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._rating_block(release, details))
        layout.addWidget(self._screenshots_block(release))
        layout.addWidget(self._badges_block(details))
        layout.addWidget(self._collections_block(details))
        layout.addWidget(self._related_block(details))
        layout.addWidget(self._recommended_block(details))
        layout.addWidget(self._comments_block(details))
        layout.addWidget(self._end_block(release, details))
        layout.addStretch(1)
        return right

    def _toggle_description(self, button: QPushButton) -> None:
        self._expanded = not self._expanded
        theme = active_theme()
        self._description.setMaximumHeight(16777215 if self._expanded else theme.px(76))
        button.setText(S.RELEASE_COLLAPSE if self._expanded else S.RELEASE_EXPAND)

    def _rating_block(self, release, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        header = SectionHeader(S.RELEASE_RATING, parent=host)
        header.set_action_visible(False)
        layout.addWidget(header)
        layout.addWidget(RatingSummary(release.grade, release.vote_count, release.votes, parent=host))
        vote_row = QHBoxLayout()
        vote_row.setSpacing(theme.space("m"))
        vote_label = QLabel(S.RELEASE_YOUR_VOTE if details.user_vote else S.RELEASE_VOTE_PROMPT, host)
        vote_label.setProperty("role", "muted")
        vote_row.addWidget(vote_label)
        stars = StarRating(details.user_vote, parent=host)
        vote_row.addWidget(stars)
        vote_row.addStretch(1)
        change = QPushButton(S.RELEASE_CHANGE_VOTE, host)
        change.setProperty("ui", "text")
        change.clicked.connect(lambda: self.notify(S.RELEASE_YOUR_VOTE))
        vote_row.addWidget(change)
        layout.addLayout(vote_row)

        def on_rate(value: float) -> None:
            vote_label.setText(f"{S.RELEASE_YOUR_VOTE} · {format_rating(value)}")
            self.notify(S.RELEASE_YOUR_VOTE)

        stars.rated.connect(on_rate)
        return host

    def _screenshots_block(self, release) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        if not release.screenshots:
            host.setVisible(False)
            return host
        header = SectionHeader(S.RELEASE_SCREENSHOTS, parent=host)
        header.set_action_visible(False)
        layout.addWidget(header)
        scroll = HScrollArea(host)
        scroll.setFixedHeight(theme.px(120))
        inner = QWidget()
        row = QHBoxLayout(inner)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(theme.space("sm"))
        for index, url in enumerate(release.screenshots[:6]):
            tile = FrameTile(release.seed + index, image_url=url, parent=inner)
            tile.clicked.connect(lambda idx=index: MessageDialog(S.RELEASE_SCREENSHOTS, f"{S.RELEASE_SCREENSHOTS} {idx + 1}", parent=self).exec())
            row.addWidget(tile)
        row.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return host

    def _badges_block(self, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        header = SectionHeader(S.RELEASE_BADGES, parent=host)
        header.show_all.connect(lambda: self.open_route("release_badges", self.release_id))
        layout.addWidget(header)
        scroll = HScrollArea(host)
        scroll.setFixedHeight(theme.px(110))
        inner = QWidget()
        row = QHBoxLayout(inner)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(theme.space("sm"))
        for badge in details.badges[:3]:
            row.addWidget(BadgeTile(badge, parent=inner))
        row.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return host

    def _collections_block(self, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        header = SectionHeader(S.RELEASE_COLLECTIONS, parent=host)
        header.show_all.connect(lambda: self.open_route("collections"))
        layout.addWidget(header)
        scroll = HScrollArea(host)
        scroll.setFixedHeight(theme.px(235))
        inner = QWidget()
        row = QHBoxLayout(inner)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(theme.semantic("grid_gap"))
        for collection in details.collections:
            card = CollectionCard(
                collection,
                width=theme.px(300),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=inner,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            row.addWidget(card)
        row.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return host

    def _related_block(self, details: ReleaseDetails) -> QWidget:
        return self._release_strip(S.RELEASE_RELATED, details.related)

    def _recommended_block(self, details: ReleaseDetails) -> QWidget:
        return self._release_strip(S.RELEASE_RECOMMENDED, details.recommended)

    def _release_strip(self, title: str, releases) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        header = SectionHeader(title, parent=host)
        header.set_action_visible(False)
        layout.addWidget(header)
        scroll = HScrollArea(host)
        scroll.setFixedHeight(theme.px(225))
        inner = QWidget()
        row = QHBoxLayout(inner)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(theme.semantic("grid_gap"))
        for release in releases:
            card = CompactReleaseCard(release, parent=inner)
            card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
            row.addWidget(card)
        row.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return host

    def _comments_block(self, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        header = SectionHeader(S.RELEASE_COMMENTS, parent=host)
        header.show_all.connect(
            lambda: self.open_route("comments", {"kind": "release", "id": self.release_id, "title": self.title})
        )
        layout.addWidget(header)
        for comment in details.comments[:2]:
            layout.addWidget(CommentPreview(comment, parent=host))
        all_comments = QPushButton(S.RELEASE_ALL_COMMENTS, host)
        all_comments.setProperty("ui", "text")
        all_comments.clicked.connect(
            lambda: self.open_route("comments", {"kind": "release", "id": self.release_id, "title": self.title})
        )
        layout.addWidget(all_comments, 0, Qt.AlignmentFlag.AlignLeft)
        return host

    def _end_block(self, release, details: ReleaseDetails) -> QWidget:
        theme = active_theme()
        host = QFrame(self)
        host.setProperty("ui", "tertiary")
        layout = QVBoxLayout(host)
        margin = theme.space("l")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("sm"))
        title = QLabel(S.RELEASE_END, host)
        title.setProperty("role", "section")
        layout.addWidget(title)
        hint = QLabel(S.RELEASE_END_HINT, host)
        hint.setProperty("role", "muted")
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        add = QPushButton(S.RELEASE_ADD_COLLECTION, host)
        add.setProperty("ui", "outlined")
        add.clicked.connect(lambda: self.open_route("collections"))
        buttons.addWidget(add)
        random_button = QPushButton(S.RELEASE_RANDOM, host)
        random_button.setProperty("ui", "outlined")
        random_button.clicked.connect(lambda: self.open_route("release", details.related[0].id if details.related else release.id, push=True))
        buttons.addWidget(random_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return host

    # ------------------------------------------------------------------- menus
    def _more_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        online = menu.addAction(S.RELEASE_ACTION_ONLINE)
        notifications = menu.addAction(S.RELEASE_ACTION_NOTIFICATIONS)
        share = menu.addAction(S.RELEASE_ACTION_SHARE)
        copy = menu.addAction(S.RELEASE_ACTION_COPY)
        home = menu.addAction(S.RELEASE_ACTION_HOME)
        menu.addSeparator()
        report = menu.addAction(S.RELEASE_ACTION_REPORT)
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == online:
            self.open_route("episodes", self.release_id)
        elif chosen == notifications:
            MessageDialog(S.RELEASE_ACTION_NOTIFICATIONS, S.SETTINGS_NOTIFICATIONS_SUMMARY, parent=self).exec()
        elif chosen == copy:
            QApplication.clipboard().setText(f"anixart://release/{self.release_id}")
            self.notify(S.LINK_COPIED)
        elif chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == home:
            self.notify(S.CREATE_DONE)
        elif chosen == report:
            ReportDialog(self.title, parent=self).exec()
