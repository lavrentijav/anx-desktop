"""Профиль: dashboard header, counters, pinned section and content chips."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
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
from ..data import Badge, ProfileData
from ..formatting import format_count, format_date_short, format_rating, format_watch_time, friends, users as users_plural
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    Avatar,
    ClickableFrame,
    CollectionCard,
    CompactReleaseCard,
    HScrollArea,
    InfoBanner,
    RatingBadge,
    ReleaseRow,
    SegmentedStatsBar,
    SkeletonList,
    SparkBars,
    TabsBar,
    TextBadge,
    paint_placeholder,
)
from ..widgets.dialogs import MessageDialog, ReportDialog, TextInputDialog
from .base import BaseScreen


class CoverWidget(QWidget):
    def __init__(self, seed: int, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._seed = seed
        self.setFixedHeight(theme.px(160))

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        paint_placeholder(painter, rect, seed=self._seed, radius=theme.radius("collection_card"))


class PieChart(QWidget):
    def __init__(self, values: tuple[tuple[int, str], ...], *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values = tuple(item for item in values if item[0] > 0)
        theme = active_theme()
        self.setFixedSize(theme.px(138), theme.px(138))
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)
        total = sum(count for count, _role in self._values) or 1
        start = 90 * 16
        painter.setPen(Qt.PenStyle.NoPen)
        for count, role in self._values:
            span = -int(360 * 16 * count / total)
            painter.setBrush(theme.qcolor(role))
            painter.drawPie(rect, start, span)
            start += span
        painter.setBrush(theme.qcolor("surface"))
        painter.setPen(QPen(theme.qcolor("border_soft"), 1))
        painter.drawEllipse(rect.adjusted(24, 24, -24, -24))


class StatSquare(QWidget):
    def __init__(self, role: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._role = role
        self.setFixedSize(theme.px(14), theme.px(14))
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setBrush(theme.qcolor(self._role))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), theme.radius("small_badge"), theme.radius("small_badge"))


class ProfileScreen(BaseScreen):
    def __init__(self, ctx, profile_id: int | None = None) -> None:
        super().__init__(ctx, title=S.PROFILE)
        self.profile_id = profile_id
        self._data: ProfileData | None = None
        self._section = S.PROFILE_SECTIONS[0]
        self._section_host: QWidget | None = None
        self._section_layout: QVBoxLayout | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonList(7, parent=self)

    def populate(self) -> None:
        self.reset_content()
        data = self.repo.fetch_profile(self.profile_id)
        self._data = data
        profile = data.profile
        self.ctx.host.set_header(S.PROFILE, profile.nick)
        theme = active_theme()
        self.add_content(CoverWidget(profile.id, parent=self))
        self.add_content(self._build_header(data))
        self.add_content(self._build_counters(data))
        if profile.is_hidden:
            self.add_content(InfoBanner(S.PROFILE_PRIVATE, icon_name="lock", parent=self))
        tabs = tuple(
            type("_Tab", (), {"key": f"section_{index}", "title": name, "subtitle": ""})()
            for index, name in enumerate(S.PROFILE_SECTIONS)
        )
        for index, name in enumerate(S.PROFILE_SECTIONS):
            if name == self._section:
                current = f"section_{index}"
                break
        else:
            current = "section_0"
            self._section = S.PROFILE_SECTIONS[0]
        tabs_bar = TabsBar(tabs, current=current, parent=self)
        tabs_bar.tab_changed.connect(self._on_section_changed)
        self.add_content(tabs_bar)
        self._section_host = QWidget(self)
        self._section_layout = QVBoxLayout(self._section_host)
        self._section_layout.setContentsMargins(0, 0, 0, 0)
        self._section_layout.setSpacing(0)
        self.add_content(self._section_host, 1)
        self._render_section()
        self.add_stretch(1)

    def _build_header(self, data: ProfileData) -> QWidget:
        theme = active_theme()
        profile = data.profile
        host = QFrame(self)
        host.setProperty("ui", "card")
        layout = QVBoxLayout(host)
        margin = theme.space("l")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("sm"))
        top = QHBoxLayout()
        top.setSpacing(theme.space("l"))
        avatar = Avatar(profile.nick, size=theme.px(120), seed=profile.id, online=profile.is_online, parent=host)
        top.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(theme.space("xs"))
        name_row = QHBoxLayout()
        name = QLabel(profile.nick, host)
        name.setStyleSheet(
            f"font-family: \"{theme.family('section_title')}\";"
            f"font-size: {theme.px(float(theme.tokens.typography('profile_nickname')['size_sp']))}px;"
            " font-weight: 600;"
        )
        name_row.addWidget(name)
        if profile.is_verified:
            verified = QLabel(host)
            verified.setPixmap(icons.pixmap("verified", "icon_alt", 18))
            name_row.addWidget(verified)
        if profile.is_sponsor:
            crown = QLabel(host)
            crown.setPixmap(icons.pixmap("crown", "rating_favorite", 18))
            name_row.addWidget(crown)
        name_row.addStretch(1)
        rating = QLabel(f"★ {format_rating(profile.rating)}", host)
        rating.setProperty("role", "muted")
        name_row.addWidget(rating)
        info.addLayout(name_row)
        status = QLabel(profile.status or S.PROFILE_BIO_EMPTY, host)
        status.setWordWrap(True)
        info.addWidget(status)
        online = QLabel(
            (S.ONLINE if profile.is_online else S.OFFLINE)
            + " · "
            + S.PROFILE_REGISTERED.format(date=format_date_short(profile.registered_ts)),
            host,
        )
        online.setProperty("role", "tertiary")
        info.addWidget(online)
        roles = QHBoxLayout()
        roles.setSpacing(theme.space("xs"))
        for role in profile.roles:
            roles.addWidget(TextBadge(role, parent=host))
        roles.addStretch(1)
        info.addLayout(roles)
        top.addLayout(info, 1)
        buttons = QVBoxLayout()
        buttons.setSpacing(theme.space("xs"))
        edit = QPushButton(S.PROFILE_EDIT, host)
        edit.setProperty("ui", "primary")
        edit.clicked.connect(self._edit_profile)
        buttons.addWidget(edit)
        message = QPushButton(S.PROFILE_MESSAGE, host)
        message.setProperty("ui", "outlined")
        message.clicked.connect(lambda: MessageDialog(S.PROFILE_MESSAGE, profile.nick, parent=self).exec())
        buttons.addWidget(message)
        more = QPushButton(S.MORE, host)
        more.setProperty("ui", "outlined")
        more.setIcon(icons.icon("more", "icon", 16))
        more.clicked.connect(lambda: self._profile_menu(more))
        buttons.addWidget(more)
        top.addLayout(buttons, 0)
        layout.addLayout(top)
        if data.badges:
            badges_row = QHBoxLayout()
            badges_row.setSpacing(theme.space("xs"))
            label = QLabel(S.PROFILE_ACHIEVEMENTS, host)
            label.setProperty("role", "muted")
            badges_row.addWidget(label)
            for badge in data.badges[:5]:
                if badge.is_owned:
                    badge_label = QLabel(badge.name, host)
                    badge_label.setPixmap(icons.pixmap("badge", "icon_alt", 18))
                    badge_label.setToolTip(badge.name)
                    badges_row.addWidget(badge_label)
            badges_row.addStretch(1)
            edit_badges = QPushButton(S.PROFILE_ACHIEVEMENTS_EDIT, host)
            edit_badges.setProperty("ui", "text")
            edit_badges.clicked.connect(lambda: self.open_route("badges"))
            badges_row.addWidget(edit_badges)
            layout.addLayout(badges_row)
        return host

    def _build_counters(self, data: ProfileData) -> QWidget:
        theme = active_theme()
        profile = data.profile
        host = QFrame(self)
        host.setProperty("ui", "panel")
        layout = QHBoxLayout(host)
        margin = theme.space("l")
        layout.setContentsMargins(margin, theme.space("m"), margin, theme.space("m"))
        layout.setSpacing(theme.space("m"))
        counters = (
            (profile.comments, S.PROFILE_COMMENTS),
            (profile.videos, S.PROFILE_VIDEOS),
            (profile.collections, S.PROFILE_COLLECTIONS),
            (profile.friends_count, S.PROFILE_FRIENDS),
        )
        for value, label in counters:
            cell = QWidget(host)
            cell_layout = QVBoxLayout(cell)
            cell_layout.setSpacing(0)
            number = QLabel(format_count(value), cell)
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            number.setStyleSheet(
                f"font-size: {theme.px(float(theme.tokens.typography('screen_title')['size_sp']))}px;"
                " font-weight: 600;"
            )
            cell_layout.addWidget(number)
            caption = QLabel(label, cell)
            caption.setProperty("role", "muted")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(caption)
            layout.addWidget(cell, 1)
        return host

    def _on_section_changed(self, key: str) -> None:
        try:
            index = int(key.rsplit("_", 1)[-1])
            self._section = S.PROFILE_SECTIONS[index]
        except (ValueError, IndexError):
            self._section = S.PROFILE_SECTIONS[0]
        self._render_section()

    def _render_section(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        while self._section_layout.count():
            item = self._section_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        section = self._section
        if section == S.PROFILE_SECTIONS[0]:
            self._render_statistics()
        elif section == S.PROFILE_SECTIONS[1]:
            self._render_votes()
        elif section == S.PROFILE_SECTIONS[2]:
            self._render_collections()
        elif section == S.PROFILE_SECTIONS[3]:
            self._render_comments()
        elif section == S.PROFILE_SECTIONS[4]:
            self._render_videos()
        else:
            self._render_badges()

    def _render_statistics(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        host = QWidget(self)
        layout = QHBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("m"))
        layout.setSpacing(theme.space("xxl"))
        left = QVBoxLayout()
        left.setSpacing(theme.space("sm"))
        title = QLabel(S.PROFILE_STATS, host)
        title.setProperty("role", "section")
        left.addWidget(title)
        for entry in self._data.stats:
            row = QHBoxLayout()
            row.setSpacing(theme.space("sm"))
            row.addWidget(StatSquare(entry.color_role, parent=host))
            label = QLabel(entry.label, host)
            label.setProperty("role", "muted")
            row.addWidget(label)
            row.addStretch(1)
            value = QLabel(format_count(entry.count), host)
            value.setStyleSheet("font-weight: 600;")
            row.addWidget(value)
            left.addLayout(row)
        left.addSpacing(theme.space("m"))
        watched = QLabel(
            f"{S.PROFILE_WATCHED_EPISODES}: {format_count(self._data.profile.watched_episodes)}",
            host,
        )
        left.addWidget(watched)
        time = QLabel(
            f"{S.PROFILE_WATCH_TIME}: {format_watch_time(self._data.profile.watched_minutes)}",
            host,
        )
        left.addWidget(time)
        genres = " · ".join(self._data.genres)
        genre_label = QLabel(genres, host)
        genre_label.setProperty("role", "tertiary")
        genre_label.setWordWrap(True)
        left.addWidget(genre_label)
        pin = QPushButton(
            S.PROFILE_SECTION_SETTINGS + f": {self.settings.pinned_section}", host
        )
        pin.setProperty("ui", "outlined")
        pin.clicked.connect(self._pin_section)
        left.addWidget(pin, 0, Qt.AlignmentFlag.AlignLeft)
        left.addStretch(1)
        layout.addLayout(left, 1)
        layout.addWidget(PieChart(tuple((entry.count, entry.color_role) for entry in self._data.stats), parent=host), 0, Qt.AlignmentFlag.AlignTop)
        if self._section_layout is not None:
            self._section_layout.addWidget(host)
        self._render_history_block()
        self._render_dynamics()

    def _render_history_block(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        header = QHBoxLayout()
        title = QLabel(S.PROFILE_HISTORY, host)
        title.setProperty("role", "section")
        header.addWidget(title)
        header.addStretch(1)
        more = QPushButton(S.SHOW_ALL, host)
        more.setProperty("ui", "text")
        more.clicked.connect(lambda: self.open_route("history"))
        header.addWidget(more)
        layout.addLayout(header)
        scroll = HScrollArea(host)
        scroll.setFixedHeight(theme.px(220))
        inner = QWidget()
        row = QHBoxLayout(inner)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(theme.semantic("grid_gap"))
        for release in self._data.history:
            card = CompactReleaseCard(release, parent=inner)
            card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
            row.addWidget(card)
        row.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        self._section_layout.addWidget(host)

    def _render_dynamics(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        title = QLabel(S.PROFILE_DYNAMICS, host)
        title.setProperty("role", "section")
        layout.addWidget(title)
        layout.addWidget(SparkBars(self._data.dynamics, parent=host))
        self._section_layout.addWidget(host)

    def _render_votes(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        for release in self._data.votes:
            row = ReleaseRow(release, parent=self)
            row.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
            self._section_layout.addWidget(row)

    def _render_collections(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        host = QWidget(self)
        grid = QGridLayout(host)
        grid.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("m"))
        grid.setSpacing(theme.space("m"))
        for index, collection in enumerate(self._data.collections):
            card = CollectionCard(
                collection,
                width=theme.px(300),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=host,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            grid.addWidget(card, index // 3, index % 3)
        self._section_layout.addWidget(host)

    def _render_comments(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        for comment in self._data.comments:
            host = QFrame(self)
            host.setProperty("ui", "card")
            layout = QHBoxLayout(host)
            layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
            layout.setSpacing(theme.space("m"))
            layout.addWidget(Avatar(comment.author, size=theme.semantic("comment_avatar_size"), seed=comment.id))
            text = QVBoxLayout()
            header = QLabel(comment.author + " · " + format_date_short(comment.timestamp), host)
            header.setProperty("role", "muted")
            text.addWidget(header)
            body = QLabel(comment.text, host)
            body.setWordWrap(True)
            text.addWidget(body)
            layout.addLayout(text, 1)
            self._section_layout.addWidget(host)

    def _render_videos(self) -> None:
        if self._section_layout is None:
            return
        from ..widgets import EmptyState

        self._section_layout.addWidget(
            EmptyState(S.EMPTY_TITLE, S.EMPTY_HINT, icon_name="play", parent=self)
        )

    def _render_badges(self) -> None:
        if self._section_layout is None or self._data is None:
            return
        theme = active_theme()
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        top = QHBoxLayout()
        title = QLabel(S.PROFILE_ACHIEVEMENTS, host)
        title.setProperty("role", "section")
        top.addWidget(title)
        top.addStretch(1)
        edit = QPushButton(S.PROFILE_ACHIEVEMENTS_EDIT, host)
        edit.setProperty("ui", "outlined")
        edit.clicked.connect(lambda: self.open_route("badges"))
        top.addWidget(edit)
        layout.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(theme.space("sm"))
        for badge in self._data.badges[:6]:
            if not badge.is_owned:
                continue
            tile = QFrame(host)
            tile.setProperty("ui", "card")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
            icon = QLabel(tile)
            icon.setPixmap(icons.pixmap("badge", "icon_alt", 40))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(icon)
            name = QLabel(badge.name, tile)
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(name)
            row.addWidget(tile)
        row.addStretch(1)
        layout.addLayout(row)
        self._section_layout.addWidget(host)

    def _pin_section(self) -> None:
        dialog = TextInputDialog(
            S.PROFILE_PIN_SECTION,
            S.PROFILE_SECTION_SETTINGS,
            placeholder=", ".join(S.PROFILE_SECTIONS),
            confirm_text=S.SAVE,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.pinned_section = dialog.text()
            self.notify(S.SET_DEFAULT_TAB)
            self.reload()

    def _edit_profile(self) -> None:
        dialog = TextInputDialog(
            S.PROFILE_EDIT,
            S.PROFILE_BIO_EMPTY,
            placeholder=S.PROFILE_BIO_EMPTY,
            confirm_text=S.SAVE,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.SETTINGS_PROFILE_SUMMARY)

    def _profile_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        share = menu.addAction(S.PROFILE_SHARE)
        report = menu.addAction(S.REPORT)
        nick_history = menu.addAction(S.PROFILE_NICK_HISTORY)
        block = menu.addAction(S.PROFILE_BLOCK)
        menu.addSeparator()
        health = menu.addAction(S.NAV_HEALTH)
        deletion = menu.addAction(S.NAV_DELETION)
        logout = (
            menu.addAction(S.AUTH_LOGOUT)
            if self.profile_id is None and self.repo.is_authenticated
            else None
        )
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == report:
            ReportDialog(self._data.profile.nick if self._data else S.PROFILE, parent=self).exec()
        elif chosen == nick_history:
            MessageDialog(S.PROFILE_NICK_HISTORY, S.EMPTY_HINT, parent=self).exec()
        elif chosen == block:
            self.notify(S.PROFILE_BLOCK)
        elif chosen == health:
            self.open_route("health")
        elif chosen == deletion:
            self.open_route("deletion")
        elif logout is not None and chosen == logout:
            self._logout()

    def _logout(self) -> None:
        try:
            self.repo.logout()
            authenticated = self.repo.is_authenticated
        except Exception:
            authenticated = True
        if authenticated:
            self.notify("Не удалось выйти из учётной записи. Попробуйте ещё раз.")
            return
        self.open_route("auth", push=False)
