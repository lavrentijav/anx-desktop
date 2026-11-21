"""Настройки: two-column desktop preferences with working theme/demo controls."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..data import DemoState
from ..strings import S
from ..theme import active_theme
from ..widgets import ChipRow, Divider, SettingRow, Switch
from ..widgets.dialogs import ConfirmDialog, MessageDialog
from ..widgets.util import clear_layout
from .base import BaseScreen


class SettingsScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.SETTINGS_TITLE)
        self._category = S.SETTINGS_GROUPS[0]
        self._category_buttons: dict[str, QPushButton] = {}
        self._content_host: QWidget | None = None
        self._content_layout: QVBoxLayout | None = None
        self._right_scroll: QScrollArea | None = None

    def set_payload(self, payload) -> None:
        if isinstance(payload, dict) and payload.get("section") in S.SETTINGS_GROUPS:
            self._category = payload["section"]

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        page = QWidget(self)
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QFrame(page)
        rail.setProperty("ui", "sidebar")
        rail.setFixedWidth(theme.px(260))
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(theme.space("sm"), theme.space("m"), theme.space("sm"), theme.space("m"))
        rail_layout.setSpacing(theme.space("xxs"))
        for category in S.SETTINGS_GROUPS:
            button = QPushButton(category, rail)
            button.setCheckable(True)
            button.setProperty("ui", "nav")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setChecked(category == self._category)
            button.setStyleSheet("text-align: left;")
            button.clicked.connect(lambda _checked=False, name=category: self._select(name))
            self._category_buttons[category] = button
            rail_layout.addWidget(button)
        rail_layout.addStretch(1)
        layout.addWidget(rail, 0)
        self._right_scroll = QScrollArea(page)
        self._right_scroll.setWidgetResizable(True)
        self._right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._content_host = QWidget()
        self._content_layout = QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(
            theme.space("xl"), theme.space("l"), theme.space("xl"), theme.semantic("screen_gutter")
        )
        self._content_layout.setSpacing(theme.space("sm"))
        self._right_scroll.setWidget(self._content_host)
        layout.addWidget(self._right_scroll, 1)
        self.add_content(page, 1)
        self._render_category()

    def _select(self, category: str) -> None:
        self._category = category
        for name, button in self._category_buttons.items():
            button.setChecked(name == category)
        self._render_category()
        if self._right_scroll is not None:
            self._right_scroll.verticalScrollBar().setValue(0)

    def _reset_page(self) -> None:
        if self._content_layout is not None:
            clear_layout(self._content_layout)

    def _render_category(self) -> None:
        self._reset_page()
        if self._content_layout is None:
            return
        theme = active_theme()
        title = QLabel(self._category, self._content_host)
        title.setProperty("role", "title")
        self._content_layout.addWidget(title)
        subtitle = QLabel(self._subtitle_for(self._category), self._content_host)
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        self._content_layout.addWidget(subtitle)
        self._content_layout.addSpacing(theme.space("m"))
        renderer = {
            S.SETTINGS_GROUPS[0]: self._render_theme,
            S.SETTINGS_GROUPS[1]: self._render_notifications,
            S.SETTINGS_GROUPS[2]: self._render_playback,
            S.SETTINGS_GROUPS[3]: self._render_appearance,
            S.SETTINGS_GROUPS[4]: self._render_data,
            S.SETTINGS_GROUPS[5]: self._render_ads,
            S.SETTINGS_GROUPS[6]: self._render_advanced,
            S.SETTINGS_GROUPS[7]: self._render_help,
            S.SETTINGS_GROUPS[8]: self._render_rules,
            S.SETTINGS_GROUPS[9]: self._render_update,
            S.SETTINGS_GROUPS[10]: self._render_bug,
            S.SETTINGS_GROUPS[11]: self._render_about,
        }.get(self._category)
        if renderer is not None:
            renderer()
        self._content_layout.addStretch(1)

    @staticmethod
    def _subtitle_for(category: str) -> str:
        mapping = {
            S.SETTINGS_GROUPS[0]: S.SETTINGS_THEME_HINT,
            S.SETTINGS_GROUPS[1]: S.SETTINGS_NOTIFICATIONS_SUMMARY,
            S.SETTINGS_GROUPS[2]: S.SETTINGS_PLAYBACK_SUMMARY,
            S.SETTINGS_GROUPS[3]: S.SETTINGS_APPEARANCE_SUMMARY,
            S.SETTINGS_GROUPS[4]: S.SETTINGS_DATA_SUMMARY,
            S.SETTINGS_GROUPS[5]: S.SETTINGS_ADS_SUMMARY,
            S.SETTINGS_GROUPS[6]: S.SETTINGS_ADVANCED_SUMMARY,
            S.SETTINGS_GROUPS[7]: S.HELP_TEXT,
            S.SETTINGS_GROUPS[8]: S.RULES_TEXT,
            S.SETTINGS_GROUPS[9]: S.UPDATE_TEXT,
            S.SETTINGS_GROUPS[10]: S.HELP_TEXT,
            S.SETTINGS_GROUPS[11]: S.ABOUT_TEXT,
        }
        return mapping.get(category, "")

    # ------------------------------------------------------------------ helpers
    def _row(self, title: str, summary: str = "", *, icon: str = "", trailing: QWidget | None = None) -> SettingRow:
        row = SettingRow(title, summary, icon_name=icon, trailing=trailing, parent=self._content_host)
        self._content_layout.addWidget(row)
        return row

    def _switch_row(self, title: str, summary: str, checked: bool, on_change, *, icon: str = "") -> None:
        switch = Switch(checked, self._content_host)
        switch.toggled.connect(on_change)
        self._row(title, summary, icon=icon, trailing=switch)

    def _combo(self, options: tuple[str, ...], current: int = 0) -> QComboBox:
        combo = QComboBox(self._content_host)
        combo.addItems(options)
        combo.setCurrentIndex(max(0, min(current, len(options) - 1)))
        return combo

    def _add_divider(self) -> None:
        self._content_layout.addWidget(Divider(parent=self._content_host))

    def _section(self, text: str) -> None:
        label = QLabel(text, self._content_host)
        label.setProperty("role", "section")
        label.setContentsMargins(0, active_theme().space("m"), 0, 0)
        self._content_layout.addWidget(label)

    # ------------------------------------------------------------------- pages
    def _render_theme(self) -> None:
        theme = active_theme()
        theme_row = QWidget(self._content_host)
        layout = QVBoxLayout(theme_row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        label = QLabel(S.SETTINGS_DARK_THEME, theme_row)
        label.setStyleSheet("font-weight: 500;")
        layout.addWidget(label)
        modes = (
            (S.SETTINGS_THEME_LIGHT, "light"),
            (S.SETTINGS_THEME_DARK, "dark"),
            (S.SETTINGS_THEME_SYSTEM, "system"),
        )
        current_mode = self.settings.theme_mode
        chips = ChipRow(
            tuple(label for label, _mode in modes),
            exclusive=True,
            checked=(next((label for label, mode in modes if mode == current_mode), S.SETTINGS_THEME_SYSTEM),),
            parent=theme_row,
        )
        chips.changed.connect(lambda: self._apply_theme(chips, modes))
        layout.addWidget(chips)
        self._content_layout.addWidget(theme_row)
        self._switch_row(
            S.SETTINGS_THEME_DEEP_BLACK,
            S.SETTINGS_DEEP_BLACK_TODO,
            False,
            lambda _checked: self.notify(S.SETTINGS_DEEP_BLACK_TODO),
        )
        self._switch_row(
            S.SETTINGS_REDUCE_MOTION,
            S.SETTINGS_REDUCE_MOTION_SUMMARY,
            self.settings.reduce_motion,
            lambda checked: setattr(self.settings, "reduce_motion", checked),
        )
        scale = QLabel(S.SETTINGS_UI_SCALE_HINT, self._content_host)
        scale.setProperty("role", "tertiary")
        self._content_layout.addWidget(scale)

    def _apply_theme(self, chips: ChipRow, modes) -> None:
        labels = chips.checked_labels()
        chosen = labels[0] if labels else S.SETTINGS_THEME_SYSTEM
        mode = next((mode for label, mode in modes if label == chosen), "system")
        self.settings.theme_mode = mode
        self.theme.set_mode(mode)
        self.notify(S.SETTINGS_THEME_HINT)

    def _render_notifications(self) -> None:
        for title, summary, attr in (
            (S.SETTINGS_PUSH_EPISODES, S.SETTINGS_NOTIFICATIONS_SUMMARY, "push_episodes"),
            (S.SETTINGS_PUSH_RELEASES, S.SETTINGS_PLAYBACK_SUMMARY, "push_releases"),
            (S.SETTINGS_PUSH_ARTICLES, S.SETTINGS_NOTIFICATIONS_SUMMARY, "push_articles"),
            (S.SETTINGS_PUSH_COMMENTS, S.SETTINGS_NOTIFICATIONS_SUMMARY, "push_comments"),
            (S.SETTINGS_PUSH_REPORTS, S.SETTINGS_NOTIFICATIONS_SUMMARY, "push_reports"),
        ):
            self._switch_row(
                title,
                summary,
                bool(getattr(self.settings, attr)),
                lambda checked, name=attr: setattr(self.settings, name, checked),
                icon="bell",
            )
        self._add_divider()
        note = QLabel(S.SETTINGS_SYSTEM_CATEGORIES, self._content_host)
        note.setProperty("role", "muted")
        self._content_layout.addWidget(note)

    def _render_playback(self) -> None:
        player = self._combo(
            (S.SETTINGS_PLAYER_ASK, S.SETTINGS_PLAYER_WEB, S.SETTINGS_PLAYER_ANIX, S.SETTINGS_PLAYER_EMBEDDED, S.SETTINGS_PLAYER_THIRD),
            {"ask": 0, "web": 1, "anix": 2, "embedded": 3, "third": 4}.get(self.settings.player, 0),
        )
        player.currentIndexChanged.connect(
            lambda index: setattr(self.settings, "player", ("ask", "web", "anix", "embedded", "third")[index])
        )
        row = self._row(S.SETTINGS_PLAYER, S.SETTINGS_PLAYBACK_SUMMARY, icon="play", trailing=player)
        row.clicked.connect(lambda: None)
        qualities = ("360p", "480p", "720p", "1080p", "1440p", "2160p")
        quality_index = qualities.index(self.settings.quality) if self.settings.quality in qualities else 3
        quality = self._combo(qualities, quality_index)
        quality.currentIndexChanged.connect(lambda index: setattr(self.settings, "quality", qualities[index]))
        self._row(S.SETTINGS_QUALITY, S.SETTINGS_PLAYBACK_SUMMARY, icon="quality", trailing=quality)
        seek = self._combo((S.SETTINGS_SEEK_5, S.SETTINGS_SEEK_10, S.SETTINGS_SEEK_15), 1)
        seek.currentIndexChanged.connect(lambda index: setattr(self.settings, "seek_seconds", (5, 10, 15)[index]))
        self._row(S.SETTINGS_SEEK, S.SETTINGS_PLAYBACK_SUMMARY, icon="seek_forward", trailing=seek)
        self._switch_row(S.SETTINGS_AUTOPLAY, S.SETTINGS_AUTOPLAY_SUMMARY, self.settings.autoplay, lambda checked: setattr(self.settings, "autoplay", checked), icon="play")
        self._switch_row(S.SETTINGS_REMEMBER_SOURCE, S.SETTINGS_PLAYBACK_SUMMARY, self.settings.remember_source, lambda checked: setattr(self.settings, "remember_source", checked), icon="history")
        self._switch_row(S.SETTINGS_HORIZONTAL, S.SETTINGS_PLAYBACK_SUMMARY, self.settings.horizontal_only, lambda checked: setattr(self.settings, "horizontal_only", checked), icon="fullscreen")
        self._add_divider()
        note = QLabel(S.PLAYER_BACKEND_TODO, self._content_host)
        note.setProperty("role", "tertiary")
        note.setWordWrap(True)
        self._content_layout.addWidget(note)

    def _render_appearance(self) -> None:
        theme = active_theme()
        view = ChipRow(
            (S.SETTINGS_VIEW_LIST, S.SETTINGS_VIEW_GRID),
            exclusive=True,
            checked=(S.SETTINGS_VIEW_GRID if self.settings.view_mode == "grid" else S.SETTINGS_VIEW_LIST,),
            parent=self._content_host,
        )
        view.changed.connect(lambda: self._set_view(view))
        row = QWidget(self._content_host)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(theme.space("sm"))
        label = QLabel(S.SETTINGS_VIEW_MODE, row)
        label.setStyleSheet("font-weight: 500;")
        row_layout.addWidget(label)
        row_layout.addWidget(view)
        self._content_layout.addWidget(row)
        home_key_index = self._key_index(self.settings.home_tab, "home")
        home = self._combo(S.HOME_TABS, home_key_index)
        home.currentIndexChanged.connect(lambda index: setattr(self.settings, "home_tab", f"home_{index}"))
        self._row(S.SETTINGS_HOME_DEFAULT, "", icon="home", trailing=home)
        bookmarks_key_index = self._key_index(self.settings.bookmarks_tab, "bookmark")
        bookmarks = self._combo(S.BOOKMARK_TABS, bookmarks_key_index)
        bookmarks.currentIndexChanged.connect(lambda index: setattr(self.settings, "bookmarks_tab", f"bookmark_{index}"))
        self._row(S.SETTINGS_BOOKMARKS_DEFAULT, "", icon="bookmarks", trailing=bookmarks)
        self._switch_row(S.SETTINGS_CONTINUE, S.SETTINGS_CONTINUE_SUMMARY, self.settings.continue_watching, self._continue_watching, icon="play")
        self._switch_row(S.SETTINGS_COMPACT_MENU, S.SETTINGS_COMPACT_MENU_SUMMARY, self.settings.compact_sidebar, self._compact_sidebar, icon="settings")
        self._switch_row(S.SETTINGS_HIDE_WIDGETS, S.SETTINGS_APPEARANCE_SUMMARY, self.settings.hide_channel_widgets, lambda checked: setattr(self.settings, "hide_channel_widgets", checked), icon="channel")
        time_format = self._combo((S.SETTINGS_TIME_SHORT, S.SETTINGS_TIME_HOURS), 1 if self.settings.time_format == "hours" else 0)
        time_format.currentIndexChanged.connect(lambda index: setattr(self.settings, "time_format", "hours" if index == 1 else "short"))
        self._row(S.SETTINGS_TIME_FORMAT, "", icon="history", trailing=time_format)
        if hasattr(self.repo, "set_demo_state"):
            self._add_divider()
            demo = self._combo((S.DEMO_DATA, S.DEMO_EMPTY, S.DEMO_ERROR, S.LOADING), self._demo_index(self.settings.demo_state))
            demo.currentIndexChanged.connect(self._on_demo_changed)
            self._row(S.SETTINGS_DEMO, S.SETTINGS_DEMO_HINT, icon="info", trailing=demo)

    def _set_view(self, view: ChipRow) -> None:
        labels = view.checked_labels()
        self.settings.view_mode = "grid" if labels and labels[0] == S.SETTINGS_VIEW_GRID else "list"
        self.notify(S.SETTINGS_VIEW_MODE + ": " + (S.SETTINGS_VIEW_GRID if self.settings.view_mode == "grid" else S.SETTINGS_VIEW_LIST))

    def _compact_sidebar(self, checked: bool) -> None:
        self.settings.compact_sidebar = checked
        if hasattr(self.ctx.host, "apply_compact_sidebar"):
            self.ctx.host.apply_compact_sidebar(checked)

    def _continue_watching(self, checked: bool) -> None:
        self.settings.continue_watching = checked
        if hasattr(self.ctx.host, "apply_continue_watching"):
            self.ctx.host.apply_continue_watching(checked)

    @staticmethod
    def _demo_index(state: DemoState) -> int:
        return {DemoState.DATA: 0, DemoState.EMPTY: 1, DemoState.ERROR: 2, DemoState.LOADING: 3}.get(state, 0)

    @staticmethod
    def _key_index(key: str, prefix: str) -> int:
        tail = key.rsplit("_", 1)[-1] if key else ""
        return int(tail) if tail.isdigit() else 0

    def _on_demo_changed(self, index: int) -> None:
        state = (DemoState.DATA, DemoState.EMPTY, DemoState.ERROR, DemoState.LOADING)[max(0, min(index, 3))]
        self.settings.demo_state = state
        if hasattr(self.repo, "set_demo_state"):
            self.repo.set_demo_state(state)  # type: ignore[attr-defined]
        self.notify(S.SETTINGS_DEMO_APPLIED)

    def _render_data(self) -> None:
        usage = S.SETTINGS_CACHE_USAGE.format(size=f"{self.settings.image_cache_used_mb} МБ")
        clear = QPushButton(S.SETTINGS_CLEAR_CACHE, self._content_host)
        clear.setProperty("ui", "outlined")
        clear.clicked.connect(self._clear_cache)
        self._row(S.SETTINGS_CACHE, usage, icon="memory", trailing=clear)
        limit = self._combo(S.SETTINGS_CACHE_LIMITS, 1)
        self._row(S.SETTINGS_CACHE_LIMIT, "", icon="memory", trailing=limit)
        self._add_divider()
        import_row = self._row(S.SETTINGS_IMPORT, "", icon="download")
        import_row.clicked.connect(lambda: self.notify(S.SETTINGS_IMPORT_OK))
        export_row = self._row(S.SETTINGS_EXPORT, S.SETTINGS_EXPORT_FORMAT, icon="download")
        export_row.clicked.connect(lambda: self.notify(S.SETTINGS_EXPORT_OK))

    def _clear_cache(self) -> None:
        dialog = ConfirmDialog(S.SETTINGS_CLEAR_CACHE_CONFIRM, S.SETTINGS_DATA_SUMMARY, confirm_text=S.CLEAR, destructive=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings.image_cache_used_mb = 0
            self.notify(S.SETTINGS_CACHE_CLEARED)
            self._render_category()

    def _render_ads(self) -> None:
        info = QLabel(S.SETTINGS_NOT_AVAILABLE + " " + S.SETTINGS_ADS_SUMMARY, self._content_host)
        info.setProperty("role", "muted")
        info.setWordWrap(True)
        self._content_layout.addWidget(info)
        self._add_divider()
        for title in S.SETTINGS_AD_ITEMS:
            switch = Switch(False, self._content_host)
            switch.setEnabled(False)
            self._row(title, S.SETTINGS_NOT_AVAILABLE, trailing=switch)

    def _render_advanced(self) -> None:
        self._switch_row(S.SETTINGS_ECONOMY, S.SETTINGS_ECONOMY_SUMMARY, self.settings.economy_mode, lambda checked: setattr(self.settings, "economy_mode", checked), icon="memory")
        self._switch_row(S.SETTINGS_ALT_CONNECTION, S.SETTINGS_ALT_CONNECTION_SUMMARY, self.settings.alternative_connection, lambda checked: setattr(self.settings, "alternative_connection", checked), icon="cloud")
        self._add_divider()
        clear = QPushButton(S.SETTINGS_CLEAR_WEB, self._content_host)
        clear.setProperty("ui", "outlined")
        clear.clicked.connect(self._clear_web_cache)
        self._row(S.SETTINGS_CLEAR_WEB, S.SETTINGS_CLEAR_WEB_WARNING, icon="globe", trailing=clear)

    def _clear_web_cache(self) -> None:
        dialog = ConfirmDialog(S.SETTINGS_CLEAR_WEB_CONFIRM, S.SETTINGS_CLEAR_WEB_WARNING, confirm_text=S.CLEAR, destructive=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.SETTINGS_WEB_CLEARED)

    def _render_help(self) -> None:
        self._content_layout.addWidget(Divider(parent=self._content_host))
        buttons = QHBoxLayout()
        help_button = QPushButton(S.SETTINGS_HELP, self._content_host)
        help_button.setProperty("ui", "outlined")
        help_button.clicked.connect(lambda: MessageDialog(S.SETTINGS_HELP, S.HELP_TEXT, parent=self).exec())
        buttons.addWidget(help_button)
        rules_button = QPushButton(S.SETTINGS_RULES, self._content_host)
        rules_button.setProperty("ui", "outlined")
        rules_button.clicked.connect(lambda: MessageDialog(S.SETTINGS_RULES, S.RULES_TEXT, parent=self).exec())
        buttons.addWidget(rules_button)
        buttons.addStretch(1)
        self._content_layout.addLayout(buttons)
        shortcuts = QLabel(S.SETTINGS_SHORTCUTS, self._content_host)
        shortcuts.setProperty("role", "tertiary")
        shortcuts.setWordWrap(True)
        self._content_layout.addWidget(shortcuts)

    def _render_rules(self) -> None:
        text = QLabel(S.RULES_TEXT, self._content_host)
        text.setWordWrap(True)
        self._content_layout.addWidget(text)

    def _render_update(self) -> None:
        check = QPushButton(S.SETTINGS_UPDATE, self._content_host)
        check.setProperty("ui", "primary")
        check.clicked.connect(lambda: self.notify(S.UPDATE_CHECKED))
        self._content_layout.addWidget(check, 0, Qt.AlignmentFlag.AlignLeft)
        version = QLabel(f"{S.SETTINGS_VERSION}: {S.APP_VERSION}", self._content_host)
        version.setProperty("role", "tertiary")
        self._content_layout.addWidget(version)

    def _render_bug(self) -> None:
        editor = QPlainTextEdit(self._content_host)
        editor.setPlaceholderText(S.REPORT_MESSAGE)
        editor.setMinimumHeight(active_theme().px(140))
        self._content_layout.addWidget(editor)
        send = QPushButton(S.SEND, self._content_host)
        send.setProperty("ui", "primary")
        send.clicked.connect(lambda: (editor.clear(), self.notify(S.SETTINGS_REPORT_BUG_SENT)))
        self._content_layout.addWidget(send, 0, Qt.AlignmentFlag.AlignLeft)

    def _render_about(self) -> None:
        version = QLabel(f"{S.APP_NAME} · {S.SETTINGS_VERSION} {S.APP_VERSION}", self._content_host)
        version.setProperty("role", "section")
        self._content_layout.addWidget(version)
        about = QLabel(S.ABOUT_TEXT, self._content_host)
        about.setWordWrap(True)
        self._content_layout.addWidget(about)
        disclaimer = QLabel(S.ASSET_DISCLAIMER, self._content_host)
        disclaimer.setProperty("role", "tertiary")
        disclaimer.setWordWrap(True)
        self._content_layout.addWidget(disclaimer)
        shortcuts = QLabel(S.SETTINGS_SHORTCUTS, self._content_host)
        shortcuts.setProperty("role", "tertiary")
        shortcuts.setWordWrap(True)
        self._content_layout.addWidget(shortcuts)
