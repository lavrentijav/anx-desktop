"""Коллекции: catalog grid and collection detail."""

from __future__ import annotations

import os

from PySide6.QtCore import QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QPainter
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
from ..data import Collection, CollectionDetails
from ..formatting import format_date_short, releases
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    CardGrid,
    CollectionCard,
    EmptyState,
    HScrollArea,
    InfoBanner,
    ReleaseRow,
    SearchField,
    SegmentedStatsBar,
    SkeletonDetail,
    SkeletonGrid,
    TextBadge,
    paint_placeholder,
)
from ..widgets.dialogs import ConfirmDialog, MessageDialog, ReportDialog, TextInputDialog
from .base import BaseScreen


class CollectionCover(QWidget):
    def __init__(self, seed: int, *, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._seed = seed
        self.setFixedHeight(height)
        self.setMinimumWidth(active_theme().px(320))

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        paint_placeholder(
            painter,
            QRectF(0, 0, self.width(), self.height()),
            seed=self._seed,
            radius=theme.radius("collection_header"),
            accent=True,
        )


class CollectionsScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.COLLECTIONS_TITLE)
        self._query = ""
        self._sort = "popular"
        self._grid_host: QWidget | None = None
        self._grid: CardGrid | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(80 if os.environ.get("ANX_UI_SMOKE_TEST") == "1" else 320)
        self._timer.timeout.connect(self._render)

    def create_loading_page(self) -> QWidget:
        return SkeletonGrid(columns=3, rows=2, parent=self)

    def create_empty_page(self) -> QWidget:
        page = EmptyState(S.COLLECTIONS_EMPTY_MINE, S.COLLECTIONS_EMPTY_HINT, icon_name="collection", parent=self)
        page.action_clicked.connect(self._create)
        return page

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.setSpacing(theme.space("sm"))
        search = SearchField(S.COLLECTIONS_SEARCH, show_mic=False, parent=toolbar)
        search.blockSignals(True)
        search.setText(self._query)
        search.blockSignals(False)
        search.textChanged.connect(self._on_query)
        row.addWidget(search, 1)
        sort = QPushButton(S.COLLECTIONS_SORT, toolbar)
        sort.setProperty("ui", "grey")
        sort.setIcon(icons.icon("sort", "icon", 16))
        sort.clicked.connect(lambda: self._sort_menu(sort))
        row.addWidget(sort)
        create = QPushButton(S.COLLECTIONS_CREATE, toolbar)
        create.setProperty("ui", "primary")
        create.clicked.connect(self._create)
        row.addWidget(create)
        self.add_content(toolbar)
        self._grid_host = QWidget(self)
        layout = QVBoxLayout(self._grid_host)
        layout.setContentsMargins(0, 0, 0, 0)
        self.add_content(self._grid_host, 1)
        self._render()
        self.add_stretch(1)

    def _collections(self) -> tuple[Collection, ...]:
        return self.repo.fetch_collections(self._query, self._sort)

    def _render(self) -> None:
        if self._grid_host is None:
            return
        layout = self._grid_host.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        collected = self._collections()
        self._collection_count = len(collected)
        if not collected:
            layout.addWidget(EmptyState(S.EMPTY_TITLE, S.COLLECTIONS_EMPTY_HINT, icon_name="collection", parent=self._grid_host))
            return
        theme = active_theme()
        cards = []
        for collection in collected:
            card = CollectionCard(
                collection,
                width=theme.px(320),
                height=theme.px(float(theme.tokens.layout("collection_compact_card_height_dp"))),
                parent=self._grid_host,
            )
            card.clicked.connect(lambda cid=collection.id: self.open_route("collection", cid))
            card.context_requested.connect(lambda pos, coll=collection: self._context(coll, pos))
            cards.append(card)
        grid = CardGrid(cards, min_card_width=theme.px(280), max_columns=4, parent=self._grid_host)
        layout.addWidget(grid)

    def is_empty_result(self) -> bool:
        return getattr(self, "_collection_count", 0) == 0 and bool(self._query)

    def _on_query(self, text: str) -> None:
        self._query = text.strip()
        self._timer.start()

    def _sort_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        options = (
            ("popular", S.COLLECTIONS_SORT_POPULAR),
            ("new", S.COLLECTIONS_SORT_NEW),
            ("favorites", S.COLLECTIONS_SORT_FAVORITES),
        )
        actions = [(key, menu.addAction(label)) for key, label in options]
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        for key, action in actions:
            if chosen == action:
                self._sort = key
                anchor.setText(action.text())
                self._render()
                break

    def _context(self, collection: Collection, pos) -> None:
        menu = QMenu(self)
        favorite = menu.addAction(S.COLLECTIONS_ADD_FAVORITE)
        share = menu.addAction(S.SHARE)
        report = menu.addAction(S.REPORT)
        chosen = menu.exec(pos)
        if chosen == favorite:
            self.notify(S.MOVED_TO_FAVORITES)
        elif chosen == share:
            self.notify(S.LINK_COPIED)
        elif chosen == report:
            ReportDialog(collection.title, parent=self).exec()

    def _create(self) -> None:
        dialog = TextInputDialog(S.COLLECTIONS_CREATE, S.ARTICLE_TITLE_FIELD, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.COLLECTIONS_CREATED)
            self._render()


class CollectionScreen(BaseScreen):
    supports_empty = False

    def __init__(self, ctx, collection_id: int = 0) -> None:
        super().__init__(ctx, title=S.COLLECTIONS_TITLE)
        self.collection_id = collection_id
        self._details: CollectionDetails | None = None

    def create_loading_page(self) -> QWidget:
        return SkeletonDetail(parent=self)

    def populate(self) -> None:
        self.reset_content()
        details = self.repo.fetch_collection(self.collection_id)
        self._details = details
        theme = active_theme()
        if not details.is_available:
            self.ctx.host.set_header(S.COLLECTIONS_TITLE, details.collection.title)
            wrap = QWidget(self)
            layout = QVBoxLayout(wrap)
            layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("xl"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
            layout.addWidget(
                InfoBanner(
                    S.PRIVATE_COLLECTION_TEXT if details.is_private else S.DELETED_COLLECTION_TEXT,
                    icon_name="lock",
                    title=S.PRIVATE_COLLECTION_TITLE if details.is_private else S.COLLECTIONS_DELETED,
                    parent=wrap,
                )
            )
            back = QPushButton(S.BACK, wrap)
            back.setProperty("ui", "outlined")
            back.clicked.connect(self.ctx.host.go_back)
            layout.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addStretch(1)
            self.add_content(wrap, 1)
            return
        collection = details.collection
        self.ctx.host.set_header(S.COLLECTIONS_TITLE, collection.title)
        page = QWidget(self)
        layout = QHBoxLayout(page)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("xxl"))
        left = QVBoxLayout()
        cover = CollectionCover(
            collection.seed,
            height=theme.px(float(theme.tokens.layout("collection_header_height_dp"))),
            parent=page,
        )
        left.addWidget(cover)
        info = QFrame(page)
        info.setProperty("ui", "panel")
        info_layout = QVBoxLayout(info)
        margin = theme.space("l")
        info_layout.setContentsMargins(margin, margin, margin, margin)
        info_layout.setSpacing(theme.space("sm"))
        title = QLabel(collection.title, info)
        title.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('collection_detail_title')['size_sp']))}px;"
            " font-weight: 600;"
        )
        title.setWordWrap(True)
        info_layout.addWidget(title)
        author = QLabel(S.AUTHOR_PREFIX.format(author=collection.author) + f" · {format_date_short(collection.created_ts)}", info)
        author.setProperty("role", "tertiary")
        info_layout.addWidget(author)
        favorite = QPushButton(
            f"{S.COLLECTIONS_ADD_FAVORITE} · {collection.favorites_count}", info
        )
        favorite.setProperty("ui", "outlined")
        favorite.setIcon(icons.icon("heart_outline", "icon_alt", 16))
        favorite.clicked.connect(lambda: self.notify(S.MOVED_TO_FAVORITES))
        info_layout.addWidget(favorite, 0, Qt.AlignmentFlag.AlignLeft)
        description = QLabel(details.description, info)
        description.setWordWrap(True)
        info_layout.addWidget(description)
        if collection.is_private:
            info_layout.addWidget(InfoBanner(S.PRIVATE_COLLECTION_TEXT, icon_name="lock", parent=info))
        stats = SegmentedStatsBar(
            (
                (collection.completed_count, "status_completed"),
                (collection.watching_count, "status_watching"),
                (collection.plan_count, "status_planned"),
                (collection.hold_count, "status_on_hold"),
                (collection.dropped_count, "status_dropped"),
            ),
            parent=info,
        )
        info_layout.addWidget(stats)
        legend = QHBoxLayout()
        legend.setSpacing(theme.space("m"))
        for count, label in (
            (collection.completed_count, S.BOOKMARK_TABS[5]),
            (collection.watching_count, S.BOOKMARK_TABS[3]),
            (collection.plan_count, S.BOOKMARK_TABS[4]),
        ):
            legend.addWidget(TextBadge(f"{label}: {count}", parent=info))
        legend.addStretch(1)
        info_layout.addLayout(legend)
        releases_label = QLabel(releases(collection.releases_count), info)
        releases_label.setProperty("role", "muted")
        info_layout.addWidget(releases_label)
        if collection.is_owner:
            owner_actions = QHBoxLayout()
            edit = QPushButton(S.COLLECTIONS_EDIT, info)
            edit.setProperty("ui", "outlined")
            edit.clicked.connect(self._edit)
            owner_actions.addWidget(edit)
            delete = QPushButton(S.COLLECTIONS_DELETE, info)
            delete.setProperty("ui", "danger")
            delete.clicked.connect(self._delete)
            owner_actions.addWidget(delete)
            owner_actions.addStretch(1)
            info_layout.addLayout(owner_actions)
        left.addWidget(info)
        left.addStretch(1)
        layout.addLayout(left, 0)
        right = QVBoxLayout()
        right.setSpacing(theme.space("sm"))
        heading = QLabel(S.COLLECTION_RELEASES, page)
        heading.setProperty("role", "section")
        right.addWidget(heading)
        if details.releases:
            for release in details.releases:
                row = ReleaseRow(release, parent=page)
                row.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                right.addWidget(row)
        else:
            right.addWidget(EmptyState(S.EMPTY_COLLECTION, S.COLLECTIONS_EMPTY_HINT, icon_name="collection", parent=page))
        right.addStretch(1)
        layout.addLayout(right, 1)
        self.add_content(page, 1)

    def _edit(self) -> None:
        dialog = TextInputDialog(S.COLLECTIONS_EDIT, S.ARTICLE_TITLE_FIELD, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.COLLECTIONS_CREATED)

    def _delete(self) -> None:
        dialog = ConfirmDialog(S.COLLECTIONS_DELETE, S.DELETE_ALL_TEXT, confirm_text=S.DELETE, destructive=True, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.COLLECTIONS_DELETED)
            self.ctx.host.go_back()
