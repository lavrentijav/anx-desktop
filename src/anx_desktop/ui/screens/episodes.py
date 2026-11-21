"""Серии: type/source chips, watched marks, channel widget and player entry."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..data import Channel, Episode, EpisodeSource, EpisodeType
from ..formatting import format_duration_minutes
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    ChipRow,
    ClickableFrame,
    EmptyState,
    HScrollArea,
    IconButton,
    SearchField,
    SkeletonList,
    TextBadge,
)
from ..widgets.dialogs import MessageDialog
from .. import icons
from .base import BaseScreen


class EpisodeRow(ClickableFrame):
    watched_toggled = Signal(int)
    more_clicked = Signal(int)

    def __init__(self, episode: Episode, type_name: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.episode = episode
        self.setMinimumHeight(theme.semantic("episode_row_min_height"))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        layout.setSpacing(theme.space("m"))
        number = QLabel(str(episode.number), self)
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setFixedWidth(theme.px(32))
        number.setStyleSheet("font-weight: 600;")
        layout.addWidget(number)
        text = QVBoxLayout()
        text.setSpacing(theme.space("xxs"))
        title = QLabel(episode.title, self)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('list_title')['size_sp']))}px;"
            " font-weight: 500;"
        )
        text.addWidget(title)
        secondary_parts = [type_name or episode.type_name]
        if episode.watched:
            secondary_parts.append(S.EPISODES_WATCHED)
        secondary = QLabel(" · ".join(secondary_parts), self)
        secondary.setProperty("role", "tertiary")
        text.addWidget(secondary)
        layout.addLayout(text, 1)
        if episode.filler:
            filler = TextBadge(S.EPISODES_FILLER.upper(), parent=self)
            layout.addWidget(filler)
        if episode.duration_seconds > 0:
            duration = QLabel(
                format_duration_minutes(episode.duration_seconds // 60), self
            )
            duration.setProperty("role", "tertiary")
            layout.addWidget(duration)
        watched = IconButton(
            "check_circle" if episode.watched else "circle",
            role="success" if episode.watched else "icon",
            size=20,
            tooltip=S.EPISODES_WATCHED if episode.watched else S.EPISODES_UNWATCHED,
            parent=self,
        )
        watched.clicked.connect(lambda: self.watched_toggled.emit(episode.id))
        layout.addWidget(watched)
        download = IconButton("download", size=18, tooltip=S.EPISODES_DOWNLOAD, parent=self)
        download.clicked.connect(lambda: MessageDialog(S.EPISODES_DOWNLOAD, S.EPISODES_DOWNLOAD_STUB, parent=self).exec())
        layout.addWidget(download)
        more = IconButton("more", size=18, tooltip=S.TOOLTIP_MORE, parent=self)
        more.clicked.connect(lambda: self.more_clicked.emit(episode.id))
        layout.addWidget(more)
        self.setAccessibleName(episode.title)


class EpisodesScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, release_id: int = 0) -> None:
        super().__init__(ctx, title=S.EPISODES_TITLE)
        self.release_id = release_id
        self._episodes: tuple[Episode, ...] = ()
        self._sources: tuple[EpisodeSource, ...] = ()
        self._types: tuple[EpisodeType, ...] = ()
        self._active_type_id: int | None = None
        self._active_source: EpisodeSource | None = None
        self._source_chips: ChipRow | None = None
        self._watched: set[int] = set()
        self._studio_filter = S.EPISODES_SOURCE_ALL
        self._kind_filter = S.EPISODES_ALL
        self._search = ""
        self._list_host: QWidget | None = None
        self._list_layout: QVBoxLayout | None = None
        self._release_title = ""

    def create_loading_page(self) -> QWidget:
        return SkeletonList(7, parent=self)

    def create_empty_page(self) -> QWidget:
        from ..widgets import EmptyState

        return EmptyState(S.EPISODES_EMPTY_TITLE, S.EPISODES_EMPTY_HINT, icon_name="list", parent=self)

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_release(self.release_id)
        self._release_title = details.release.title
        self.ctx.host.set_header(S.EPISODES_TITLE, details.release.title)
        self._types = self.repo.episode_types(self.release_id)
        options = self._type_options()
        active_type = next(
            (item for item in options if item.name == self._studio_filter),
            options[0] if options else None,
        )
        self._active_type_id = active_type.id if active_type is not None else None
        self._sources = self.repo.episode_sources(
            self.release_id, self._active_type_id
        )
        self._active_source = self._sources[0] if self._sources else None
        self._episodes = self.repo.fetch_episodes(
            self.release_id,
            type_id=self._active_type_id,
            source_id=self._active_source.id if self._active_source else None,
        )
        self._watched = {episode.id for episode in self._episodes if episode.watched}
        if not self._episodes:
            self.show_empty()
            return
        theme = active_theme()
        toolbar = QWidget(self)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm")
        )
        toolbar_layout.setSpacing(theme.space("sm"))
        kind = ChipRow(
            (S.EPISODES_ALL, S.EPISODES_VOICES, S.EPISODES_SUBTITLES),
            exclusive=True,
            checked=(self._kind_filter,),
            parent=toolbar,
        )
        kind.changed.connect(lambda: self._on_kind(kind))
        toolbar_layout.addWidget(kind, 1)
        search = SearchField(S.EPISODES_SEARCH, show_mic=False, parent=toolbar)
        search.setMaximumWidth(theme.px(260))
        search.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(search)
        sort = QPushButton(S.EPISODES_SORT, toolbar)
        sort.setProperty("ui", "grey")
        sort.clicked.connect(lambda: self._episodes_menu(sort))
        toolbar_layout.addWidget(sort)
        updates = QPushButton(S.EPISODES_UPDATES, toolbar)
        updates.setProperty("ui", "grey")
        updates.clicked.connect(lambda: self.open_route("updates"))
        toolbar_layout.addWidget(updates)
        self.add_content(toolbar)

        source_row = QWidget(self)
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(
            theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm")
        )
        source_layout.setSpacing(theme.space("sm"))
        source_label = QLabel(S.FILTER_TYPES, source_row)
        source_label.setProperty("role", "muted")
        source_layout.addWidget(source_label)
        self._source_chips = ChipRow(
            (S.EPISODES_SOURCE_ALL,) + tuple(item.name for item in options),
            exclusive=True,
            checked=(
                active_type.name
                if active_type is not None and active_type.name in {item.name for item in options}
                else S.EPISODES_SOURCE_ALL,
            ),
            parent=source_row,
        )
        self._source_chips.changed.connect(self._on_source_chips)
        self._source_chips.setMinimumWidth(self._source_chips.sizeHint().width())
        chips_host = QWidget(source_row)
        chips_layout = QHBoxLayout(chips_host)
        chips_layout.setContentsMargins(0, 0, theme.space("m"), 0)
        chips_layout.setSpacing(0)
        chips_layout.addWidget(self._source_chips)
        chips_host.setMinimumWidth(
            self._source_chips.sizeHint().width() + theme.space("m")
        )
        source_scroll = HScrollArea(source_row)
        source_scroll.setFixedHeight(
            max(theme.px(40), self._source_chips.sizeHint().height() + theme.px(12))
        )
        source_scroll.setWidget(chips_host)
        source_layout.addWidget(source_scroll, 1)
        self.add_content(source_row)

        if not self.settings.hide_channel_widgets:
            channels = self.repo.fetch_channels()
            if channels:
                self._add_channel_widget(channels[0])

        heading = QLabel(S.EPISODES_SEASON.format(n=1), self)
        heading.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('episode_type_heading')['size_sp']))}px;"
            " font-weight: 800;"
        )
        heading.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), 0, theme.space("xs"))
        self.add_content(heading)
        self._list_host = QWidget(self)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self.add_content(self._list_host, 1)
        self._render_episodes()
        self.add_stretch(1)

    def _add_channel_widget(self, channel: Channel) -> None:
        theme = active_theme()
        widget = QFrame(self)
        widget.setProperty("ui", "card")
        w_layout = QHBoxLayout(widget)
        w_layout.setContentsMargins(theme.space("m"), theme.space("m"), theme.space("m"), theme.space("m"))
        w_layout.setSpacing(theme.space("m"))
        w_icon = QLabel(widget)
        w_icon.setPixmap(icons.pixmap("channel", "icon_alt", 24))
        w_layout.addWidget(w_icon)
        w_text = QVBoxLayout()
        title = QLabel(channel.title, widget)
        title.setStyleSheet("font-weight: 500;")
        w_text.addWidget(title)
        article = self.repo.fetch_articles(channel.id)
        caption = QLabel(article[0].title if article else S.EPISODES_CHANNEL_WIDGET, widget)
        caption.setProperty("role", "muted")
        caption.setWordWrap(True)
        w_text.addWidget(caption)
        w_layout.addLayout(w_text, 1)
        open_channel = QPushButton(S.SHOW_ALL, widget)
        open_channel.setProperty("ui", "text")
        open_channel.clicked.connect(lambda: self.open_route("channel", channel.id))
        w_layout.addWidget(open_channel)
        hide = IconButton("close", size=16, tooltip=S.TOOLTIP_CLOSE, parent=widget)
        hide.clicked.connect(lambda: widget.hide())
        w_layout.addWidget(hide)
        wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("sm"))
        wrapper_layout.addWidget(widget)
        self.add_content(wrapper)

    def _type_options(self) -> tuple[EpisodeType, ...]:
        if self._kind_filter == S.EPISODES_SUBTITLES:
            return tuple(item for item in self._types if item.is_sub) or self._types
        if self._kind_filter == S.EPISODES_VOICES:
            return tuple(item for item in self._types if not item.is_sub) or self._types
        return self._types

    def _type_by_name(self, name: str) -> EpisodeType | None:
        if name == S.EPISODES_SOURCE_ALL:
            return None
        return next((item for item in self._type_options() if item.name == name), None)

    def _filtered(self) -> list[Episode]:
        episodes = list(self._episodes)
        if self._kind_filter == S.EPISODES_SUBTITLES:
            episodes = [ep for ep in episodes if ep.type_name == "Субтитры"]
        if self._search:
            needle = self._search.lower()
            episodes = [ep for ep in episodes if needle in ep.title.lower() or needle in str(ep.number)]
        return episodes

    def _render_episodes(self) -> None:
        if self._list_layout is None:
            return
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for episode in self._filtered():
            row = EpisodeRow(episode, episode.type_name, parent=self._list_host)
            row.clicked.connect(lambda ep=episode: self._open_player(ep))
            row.watched_toggled.connect(self._toggle_watched)
            row.more_clicked.connect(lambda eid, ep=episode: self._episode_menu(ep, self.mapToGlobal(self.rect().center())))
            self._list_layout.addWidget(row)
        if not self._filtered():
            self._list_layout.addWidget(
                EmptyState(S.EPISODES_EMPTY_TITLE, S.EPISODES_EMPTY_HINT, parent=self._list_host)
            )

    def _open_player(self, episode: Episode) -> None:
        self.open_route(
            "player",
            {
                "release_id": self.release_id,
                "episode_id": episode.id,
                "episode_number": episode.number,
                "title": self._release_title,
                "episode": episode.title,
                "type_id": self._active_type_id,
                "source_id": self._active_source.id if self._active_source else None,
            },
        )

    def _toggle_watched(self, episode_id: int) -> None:
        if episode_id in self._watched:
            self._watched.discard(episode_id)
        else:
            self._watched.add(episode_id)
        self._render_episodes()

    def _on_kind(self, row: ChipRow) -> None:
        labels = row.checked_labels()
        self._kind_filter = labels[0] if labels else S.EPISODES_ALL
        self._studio_filter = S.EPISODES_SOURCE_ALL
        self._active_source = None
        self.reload()

    def _on_source_chips(self) -> None:
        if self._source_chips is None:
            return
        labels = self._source_chips.checked_labels()
        label = labels[0] if labels else S.EPISODES_SOURCE_ALL
        type_item = self._type_by_name(label)
        if type_item is None and label != S.EPISODES_SOURCE_ALL:
            return
        if type_item is None:
            options = self._type_options()
            type_item = options[0] if options else None
        self._studio_filter = type_item.name if type_item is not None else S.EPISODES_SOURCE_ALL
        self._active_type_id = type_item.id if type_item is not None else None
        self._sources = self.repo.episode_sources(
            self.release_id, self._active_type_id
        )
        self._active_source = self._sources[0] if self._sources else None
        self._episodes = self.repo.fetch_episodes(
            self.release_id,
            type_id=self._active_type_id,
            source_id=self._active_source.id if self._active_source is not None else None,
        )
        self._watched = {episode.id for episode in self._episodes if episode.watched}
        self._render_episodes()

    def _on_search(self, text: str) -> None:
        self._search = text.strip()
        self._render_episodes()

    def _episodes_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        mark_all = menu.addAction(S.EPISODES_MARK_ALL)
        clear_all = menu.addAction(S.EPISODES_CLEAR_MARKS)
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen == mark_all:
            self._watched = {episode.id for episode in self._episodes}
            self._render_episodes()
        elif chosen == clear_all:
            self._watched.clear()
            self._render_episodes()

    def _episode_menu(self, episode: Episode, pos) -> None:
        menu = QMenu(self)
        download = menu.addAction(S.EPISODES_DOWNLOAD)
        watch = menu.addAction(S.EPISODES_MARK_ONE)
        chosen = menu.exec(pos)
        if chosen == download:
            self.notify(S.EPISODES_DOWNLOAD_STUB)
        elif chosen == watch:
            self._toggle_watched(episode.id)
