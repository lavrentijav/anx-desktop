"""Значки профиля и релиза: коллекционные карточки, редкость, витрина."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Badge, ProfileData
from ..formatting import format_count
from ..strings import S
from ..theme import active_theme
from ..widgets import Avatar, EmptyState, SkeletonList, Switch
from ..widgets.dialogs import ClaimBadgeDialog, MessageDialog
from .base import BaseScreen


_RARITY = {
    "common": S.BADGES_RARITY_COMMON,
    "uncommon": S.BADGES_RARITY_UNCOMMON,
    "rare": S.BADGES_RARITY_RARE,
    "epic": S.BADGES_RARITY_EPIC,
    "legendary": S.BADGES_RARITY_LEGENDARY,
}


class BadgeCard(QFrame):
    action_clicked = Signal(int, str)

    def __init__(
        self,
        badge: Badge,
        *,
        showcase_actions: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.badge = badge
        self.setProperty("ui", "card")
        self.setMinimumHeight(theme.px(190))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
        layout.setSpacing(theme.space("xs"))
        icon = QLabel(self)
        icon.setPixmap(icons.pixmap("badge", "icon_alt" if badge.is_owned else "icon_secondary", 44))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        name = QLabel(badge.name, self)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-weight: 600;")
        name.setWordWrap(True)
        layout.addWidget(name)
        rarity = QLabel(_RARITY.get(badge.rarity, badge.rarity), self)
        rarity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rarity.setProperty("role", "muted")
        layout.addWidget(rarity)
        ownership = QLabel(S.BADGES_OWNERSHIP.format(count=format_count(badge.ownership_percent)), self)
        ownership.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ownership.setProperty("role", "tertiary")
        ownership.setWordWrap(True)
        layout.addWidget(ownership)
        award = QLabel(badge.award or badge.description, self)
        award.setAlignment(Qt.AlignmentFlag.AlignCenter)
        award.setProperty("role", "tertiary")
        award.setWordWrap(True)
        layout.addWidget(award)
        layout.addStretch(1)
        if badge.is_owned:
            actions = QHBoxLayout()
            actions.setSpacing(theme.space("xs"))
            select = QPushButton(S.BADGES_REMOVE if badge.is_selected else S.BADGES_SET, self)
            select.setProperty("ui", "outlined")
            select.clicked.connect(lambda: self.action_clicked.emit(badge.id, "select"))
            actions.addWidget(select, 1)
            if showcase_actions:
                pin = QPushButton(S.BADGES_UNPIN if badge.is_showcased else S.BADGES_PIN, self)
                pin.setProperty("ui", "text")
                pin.clicked.connect(lambda: self.action_clicked.emit(badge.id, "pin"))
                actions.addWidget(pin)
            layout.addLayout(actions)
        else:
            hidden = QLabel(S.BADGES_HIDE_UNEARNED, self)
            hidden.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hidden.setProperty("role", "tertiary")
            layout.addWidget(hidden)


class BadgesScreen(BaseScreen):
    """Profile badges.  `release_id` switches to the release badge section."""

    def __init__(self, ctx, release_id: int | None = None) -> None:
        super().__init__(ctx, title=S.BADGES_TITLE)
        self.release_id = release_id
        self._hide_unearned = False
        self._grid_host: QWidget | None = None
        self._grid: QGridLayout | None = None
        self._badges: tuple[Badge, ...] = ()

    def create_loading_page(self) -> QWidget:
        return SkeletonList(5, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(
            S.EMPTY_RELEASE_BADGES if self.release_id else S.EMPTY_BADGES,
            S.EMPTY_RELEASE_BADGES_HINT if self.release_id else S.EMPTY_BADGES_HINT,
            icon_name="badge",
            parent=self,
        )
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        kind = "release" if self.release_id else "profile"
        self._badges = self.repo.fetch_badges(kind, self.release_id or 0)
        if not self._badges:
            self.show_empty()
            return
        if self.release_id is None:
            profile = self.repo.fetch_profile().profile
            preview = QFrame(self)
            preview.setProperty("ui", "panel")
            layout = QHBoxLayout(preview)
            margin = theme.space("l")
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(theme.space("m"))
            layout.addWidget(Avatar(profile.nick, size=theme.px(64), seed=profile.id, online=profile.is_online))
            text = QVBoxLayout()
            name = QLabel(profile.nick, preview)
            name.setStyleSheet("font-weight: 600;")
            text.addWidget(name)
            hint = QLabel(S.BADGES_INFO, preview)
            hint.setProperty("role", "muted")
            text.addWidget(hint)
            layout.addLayout(text, 1)
            claim = QPushButton(S.BADGES_CLAIM, preview)
            claim.setProperty("ui", "outlined")
            claim.clicked.connect(self._claim)
            layout.addWidget(claim)
            self.add_content(preview)
        else:
            intro = self.make_intro(S.RELEASE_BADGES, S.RELEASE_BADGES_HINT)
            self.add_content(intro)
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("m"))
        count = QLabel(S.HOME_COUNT.format(count=len(self._badges)), toolbar)
        count.setProperty("role", "uppercase")
        row.addWidget(count)
        row.addStretch(1)
        if self.release_id is None:
            reorder = QPushButton(S.BADGES_REORDER, toolbar)
            reorder.setProperty("ui", "text")
            reorder.clicked.connect(lambda: MessageDialog(S.BADGES_REORDER, S.BADGES_SHOWCASE_LIMIT, parent=self).exec())
            row.addWidget(reorder)
        else:
            hide = Switch(self._hide_unearned, toolbar)
            hide.toggled.connect(self._on_hide_unearned)
            row.addWidget(QLabel(S.BADGES_HIDE_UNEARNED, toolbar))
            row.addWidget(hide)
        self.add_content(toolbar)
        self._grid_host = QWidget(self)
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        self._grid.setHorizontalSpacing(theme.space("m"))
        self._grid.setVerticalSpacing(theme.space("m"))
        self.add_content(self._grid_host, 1)
        self._fill_grid()
        self.add_stretch(1)

    def _fill_grid(self) -> None:
        if self._grid is None:
            return
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        shown = [badge for badge in self._badges if not (self._hide_unearned and not badge.is_owned)]
        for index, badge in enumerate(shown):
            card = BadgeCard(
                badge,
                showcase_actions=self.release_id is None,
                parent=self._grid_host,
            )
            card.action_clicked.connect(self._badge_action)
            self._grid.addWidget(card, index // 3, index % 3)

    def _on_hide_unearned(self, hide: bool) -> None:
        self._hide_unearned = hide
        self._fill_grid()

    def _badge_action(self, badge_id: int, action: str) -> None:
        if action == "pin":
            showcased = [badge for badge in self._badges if badge.is_showcased]
            if len(showcased) >= 3:
                MessageDialog(S.BADGES_PIN, S.BADGES_SHOWCASE_LIMIT, parent=self).exec()
                return
            self.notify(S.SET_DEFAULT_TAB)
        else:
            self.notify(S.SET_DEFAULT_TAB)

    def _claim(self) -> None:
        dialog = ClaimBadgeDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.BADGES_CLAIM_ACTION)
            self.reload()

    def is_empty_result(self) -> bool:
        return not self._badges
