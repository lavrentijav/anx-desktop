"""Фильтр: genre modes, metadata selects and apply/reset actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..strings import S
from ..theme import active_theme
from ..widgets import ChipRow, Divider, HScrollArea
from .base import BaseScreen


def _combo(options: tuple[str, ...], parent: QWidget) -> QComboBox:
    combo = QComboBox(parent)
    combo.addItems(options)
    combo.setMinimumHeight(active_theme().px(40))
    return combo


class FilterScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.FILTER_TITLE, subtitle=S.FILTER_SUBTITLE)
        self.payload = None
        self._genre_mode: ChipRow | None = None
        self._genres: ChipRow | None = None
        self._warning: QLabel | None = None
        self._combos: dict[str, QComboBox] = {}

    def activate(self) -> None:
        super().activate()

    def set_payload(self, payload) -> None:
        self.payload = payload

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter")
        )
        layout.setSpacing(theme.space("l"))

        intro = QLabel(S.FILTER_SUBTITLE, wrap)
        intro.setProperty("role", "muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        actions = QHBoxLayout()
        actions.setSpacing(theme.space("sm"))
        reset = QPushButton(S.RESET, wrap)
        reset.setProperty("ui", "outlined")
        reset.clicked.connect(self._reset)
        apply_button = QPushButton(S.APPLY, wrap)
        apply_button.setProperty("ui", "primary")
        apply_button.clicked.connect(self._apply)
        copy_link = QPushButton(S.FILTER_COPY_LINK, wrap)
        copy_link.setProperty("ui", "text")
        copy_link.clicked.connect(self._copy_link)
        set_tab = QPushButton(S.FILTER_SET_MY_TAB, wrap)
        set_tab.setProperty("ui", "text")
        set_tab.clicked.connect(self._set_my_tab)
        actions.addWidget(reset)
        actions.addWidget(apply_button)
        actions.addStretch(1)
        actions.addWidget(copy_link)
        actions.addWidget(set_tab)
        layout.addLayout(actions)
        layout.addWidget(Divider(parent=wrap))

        grid = QGridLayout()
        grid.setHorizontalSpacing(theme.space("xl"))
        grid.setVerticalSpacing(theme.space("m"))
        fields = (
            ("country", S.FILTER_COUNTRY, S.FILTER_COUNTRIES),
            ("category", S.FILTER_CATEGORY, S.FILTER_CATEGORIES),
            ("types", S.FILTER_TYPES, S.FILTER_TYPE_OPTIONS),
            ("studio", S.FILTER_STUDIO, S.FILTER_STUDIOS),
            ("source", S.FILTER_SOURCE, S.FILTER_SOURCES),
            ("years", S.FILTER_YEARS, S.FILTER_YEAR_OPTIONS),
            ("season", S.FILTER_SEASON, S.FILTER_SEASONS),
            ("episodes", S.FILTER_EPISODES, S.FILTER_EPISODE_OPTIONS),
            ("status", S.FILTER_STATUS, S.FILTER_STATUS_OPTIONS),
            ("duration", S.FILTER_DURATION, S.FILTER_DURATION_OPTIONS),
            ("age", S.FILTER_AGE, S.FILTER_AGE_OPTIONS),
            ("exclude", S.FILTER_EXCLUDE_BOOKMARKS, S.FILTER_EXCLUDE_OPTIONS),
            ("sort", S.FILTER_SORT, S.FILTER_SORT_OPTIONS),
        )
        for index, (key, label, options) in enumerate(fields):
            cell = QWidget(wrap)
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(theme.space("xs"))
            caption = QLabel(label, cell)
            caption.setProperty("role", "muted")
            cell_layout.addWidget(caption)
            combo = _combo(options, cell)
            self._combos[key] = combo
            cell_layout.addWidget(combo)
            grid.addWidget(cell, index // 3, index % 3)
        layout.addLayout(grid)

        genres_header = QLabel(S.FILTER_GENRES, wrap)
        genres_header.setProperty("role", "section")
        layout.addWidget(genres_header)
        self._genre_mode = ChipRow(
            (S.FILTER_GENRES_ALL, S.FILTER_GENRES_ANY, S.FILTER_GENRES_EXCLUDE),
            exclusive=True,
            checked=(S.FILTER_GENRES_ALL,),
            parent=wrap,
        )
        self._genre_mode.changed.connect(self._update_genre_hint)
        layout.addWidget(self._genre_mode)
        hint = QLabel(S.FILTER_GENRES_ALL_HINT, wrap)
        hint.setProperty("role", "tertiary")
        hint.setWordWrap(True)
        self._genre_hint = hint
        layout.addWidget(hint)

        genres = S.FILTER_GENRE_NAMES
        genre_host = QWidget(wrap)
        genre_grid = QGridLayout(genre_host)
        genre_grid.setContentsMargins(0, 0, 0, 0)
        genre_grid.setHorizontalSpacing(theme.space("sm"))
        genre_grid.setVerticalSpacing(theme.space("sm"))
        self._genres = ChipRow(genres, parent=genre_host)
        self._genres.changed.connect(self._update_genre_hint)
        genre_grid.addWidget(self._genres, 0, 0)
        genre_scroll = HScrollArea(wrap)
        genre_scroll.setFixedHeight(theme.px(52))
        genre_scroll.setWidget(genre_host)
        layout.addWidget(genre_scroll)
        self._warning = QLabel(S.FILTER_GENRES_WARNING, wrap)
        self._warning.setProperty("role", "warning")
        self._warning.setWordWrap(True)
        self._warning.hide()
        layout.addWidget(self._warning)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _update_genre_hint(self) -> None:
        mode = self._genre_mode.checked_labels()[0] if self._genre_mode and self._genre_mode.checked_labels() else S.FILTER_GENRES_ALL
        hints = {
            S.FILTER_GENRES_ALL: S.FILTER_GENRES_ALL_HINT,
            S.FILTER_GENRES_ANY: S.FILTER_GENRES_ANY_HINT,
            S.FILTER_GENRES_EXCLUDE: S.FILTER_GENRES_EXCLUDE_HINT,
        }
        self._genre_hint.setText(hints.get(mode, S.FILTER_GENRES_ALL_HINT))
        selected = len(self._genres.checked_labels()) if self._genres else 0
        if self._warning is not None:
            self._warning.setVisible(selected > 8)

    def _reset(self) -> None:
        for combo in self._combos.values():
            combo.setCurrentIndex(0)
        if self._genre_mode is not None:
            self._genre_mode.set_checked((S.FILTER_GENRES_ALL,))
        if self._genres is not None:
            self._genres.set_checked(())
        self._update_genre_hint()

    def _apply(self) -> None:
        self.notify(S.FILTER_APPLIED)
        if self.payload and isinstance(self.payload, dict) and self.payload.get("target") == "my_tab":
            self.settings.home_tab = "home_0"
            self.notify(S.FILTER_SET_TO_MY_TAB)
            self.open_route("home", push=False)
            return
        self.open_route("list", {"kind": "filter", "title": S.FILTER_RESULTS})

    def _copy_link(self) -> None:
        QApplication.clipboard().setText("anixart://filter")
        self.notify(S.LINK_COPIED)

    def _set_my_tab(self) -> None:
        self.settings.home_tab = "home_0"
        self.notify(S.FILTER_SET_TO_MY_TAB)
