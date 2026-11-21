"""Secondary screens: comments, generic lists, schedule, updates and auth wall."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..data import Comment, Release
from ..formatting import format_date, format_rating
from ..strings import S
from ..theme import active_theme
from ..widgets import (
    Avatar,
    CardGrid,
    CompactReleaseCard,
    EmptyIcon,
    EmptyState,
    HScrollArea,
    PosterCard,
    ReleaseRow,
    SectionHeader,
    SkeletonGrid,
    SkeletonList,
)
from .base import BaseScreen


class CommentCard(QFrame):
    vote = Signal(int, int)

    def __init__(self, comment: Comment, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.comment = comment
        self.setProperty("ui", "card")
        layout = QHBoxLayout(self)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.semantic("comment_avatar_gap"))
        layout.addWidget(
            Avatar(comment.author, size=theme.semantic("comment_avatar_size"), seed=comment.id, online=comment.is_verified),
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        content = QVBoxLayout()
        content.setSpacing(theme.space("xxs"))
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
        if comment.is_edited:
            edited = QLabel(S.COMMENTS_EDITED, self)
            edited.setProperty("role", "tertiary")
            header.addWidget(edited)
        content.addLayout(header)
        if comment.is_deleted:
            body = QLabel(S.COMMENTS_DELETED, self)
            body.setProperty("role", "tertiary")
        elif comment.is_spoiler:
            body = QLabel(S.COMMENTS_SPOILER_WARNING + " " + S.COMMENTS_SHOW_SPOILER, self)
            body.setProperty("role", "tertiary")
        else:
            body = QLabel(comment.text, self)
        body.setWordWrap(True)
        content.addWidget(body)
        footer = QHBoxLayout()
        reply = QPushButton(S.COMMENTS_REPLY, self)
        reply.setProperty("ui", "text")
        footer.addWidget(reply)
        if comment.replies:
            replies = QPushButton(S.COMMENTS_SHOW_REPLIES.format(count=comment.replies), self)
            replies.setProperty("ui", "text")
            footer.addWidget(replies)
        footer.addStretch(1)
        up = QPushButton(f"▲ {max(0, comment.votes)}", self)
        up.setProperty("ui", "text")
        up.clicked.connect(lambda: self.vote.emit(comment.id, 1))
        footer.addWidget(up)
        down = QPushButton("▼", self)
        down.setProperty("ui", "text")
        down.clicked.connect(lambda: self.vote.emit(comment.id, -1))
        footer.addWidget(down)
        content.addLayout(footer)
        layout.addLayout(content, 1)


class CommentsScreen(BaseScreen):
    def __init__(self, ctx, payload: dict | None = None) -> None:
        super().__init__(ctx, title=S.COMMENTS_TITLE)
        self.payload = payload or {}
        self.kind = self.payload.get("kind", "release")
        self.target_id = int(self.payload.get("id", 1000))
        self.target_title = str(self.payload.get("title", ""))
        self._comments: tuple[Comment, ...] = ()

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        return EmptyState(S.EMPTY_COMMENTS, "", icon_name="comment", parent=self)

    def populate(self) -> None:
        self.reset_content()
        if self.target_title:
            self.ctx.host.set_header(S.COMMENTS_TITLE, self.target_title)
        theme = active_theme()
        comments = self.repo.fetch_comments(self.kind, self.target_id)
        self._comments = comments
        toolbar = QWidget(self)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.space("sm"))
        row.addWidget(QLabel(S.HOME_COUNT.format(count=len(comments)), toolbar))
        row.addStretch(1)
        sort = QPushButton(S.COMMENTS_SORT, toolbar)
        sort.setProperty("ui", "grey")
        sort.clicked.connect(lambda: self.notify(S.COMMENTS_SORT))
        row.addWidget(sort)
        self.add_content(toolbar)
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        for comment in comments:
            card = CommentCard(comment, parent=host)
            card.vote.connect(lambda _cid, _vote: self.notify(S.RELEASE_YOUR_VOTE))
            layout.addWidget(card)
        if not comments:
            layout.addWidget(EmptyState(S.EMPTY_COMMENTS, "", icon_name="comment", parent=host))
        self.add_content(host, 1)
        self.add_content(self._input_box())
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return not self._comments

    def _input_box(self) -> QWidget:
        theme = active_theme()
        host = QFrame(self)
        host.setProperty("ui", "tertiary")
        layout = QVBoxLayout(host)
        margin = theme.space("m")
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(theme.space("xs"))
        top = QHBoxLayout()
        top.addWidget(QLabel(S.COMMENTS_SPOILER_MARK, host))
        top.addStretch(1)
        rules = QPushButton(S.COMMENTS_RULES, host)
        rules.setProperty("ui", "text")
        top.addWidget(rules)
        layout.addLayout(top)
        editor = QPlainTextEdit(host)
        editor.setPlaceholderText(S.COMMENTS_INPUT_HINT)
        editor.setMaximumHeight(theme.px(80))
        layout.addWidget(editor)
        row = QHBoxLayout()
        row.addStretch(1)
        send = QPushButton(S.COMMENTS_SEND, host)
        send.setProperty("ui", "primary")

        def submit() -> None:
            if editor.toPlainText().strip():
                editor.clear()
                self.notify(S.ARTICLE_COMMENT_SENT)

        send.clicked.connect(submit)
        row.addWidget(send)
        layout.addLayout(row)
        return host


class ListScreen(BaseScreen):
    def __init__(self, ctx, payload: dict | None = None) -> None:
        self.payload = payload or {}
        title = str(self.payload.get("title", S.SHOW_ALL))
        super().__init__(ctx, title=title)

    def set_payload(self, payload) -> None:
        self.payload = payload or {}

    def create_loading_page(self) -> QWidget:
        return SkeletonGrid(columns=5, rows=2, parent=self)

    def create_empty_page(self) -> QWidget:
        return EmptyState(S.EMPTY_TITLE, S.EMPTY_HINT, icon_name="search", parent=self)

    def _releases(self) -> tuple[Release, ...]:
        kind = self.payload.get("kind", "recommended")
        if kind == "search":
            return self.repo.fetch_search(str(self.payload.get("query", ""))).releases
        if kind in {"recommended", "watching", "related"}:
            return self.repo.fetch_related(kind)
        if kind == "filter":
            return self.repo.fetch_home("home_0", 1, 24).items
        return self.repo.fetch_home("home_0", 1, 24).items

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        releases = self._releases()
        self._count = len(releases)
        count = QLabel(S.HOME_COUNT.format(count=len(releases)), self)
        count.setProperty("role", "uppercase")
        count.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), 0, theme.space("sm"))
        self.add_content(count)
        if self.settings.view_mode == "list":
            host = QWidget(self)
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            for release in releases:
                row = ReleaseRow(release, parent=host)
                row.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                layout.addWidget(row)
            self.add_content(host, 1)
        else:
            width, height = theme.tokens.grid_poster_size()
            cards = []
            for release in releases:
                card = PosterCard(release, poster_width=width, poster_height=height, parent=self)
                card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                cards.append(card)
            self.add_content(CardGrid(cards, min_card_width=width + theme.space("l"), max_columns=6, parent=self), 1)
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return getattr(self, "_count", 0) == 0


class ScheduleScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.SCHEDULE_TITLE)

    def create_loading_page(self) -> QWidget:
        return SkeletonList(5, parent=self)

    def create_empty_page(self) -> QWidget:
        return EmptyState(S.SCHEDULE_EMPTY, S.EMPTY_HINT, icon_name="calendar", parent=self)

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        schedule = self.repo.fetch_schedule()
        count = 0
        for day, releases in schedule.items():
            if not releases:
                continue
            count += len(releases)
            header = SectionHeader(day, action_text="", parent=self)
            self.add_content(header)
            scroll = HScrollArea(self)
            scroll.setFixedHeight(theme.px(220))
            host = QWidget()
            row = QHBoxLayout(host)
            row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
            row.setSpacing(theme.semantic("grid_gap"))
            for release in releases:
                card = CompactReleaseCard(release, parent=host)
                card.clicked.connect(lambda rid=release.id: self.open_route("release", rid))
                row.addWidget(card)
            row.addStretch(1)
            scroll.setWidget(host)
            self.add_content(scroll)
        self._count = count
        if not count:
            self.add_content(EmptyState(S.SCHEDULE_EMPTY, S.EMPTY_HINT, icon_name="calendar", parent=self))
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return getattr(self, "_count", 0) == 0


class UpdatesScreen(BaseScreen):
    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.UPDATES_TITLE)

    def create_loading_page(self) -> QWidget:
        return SkeletonList(6, parent=self)

    def create_empty_page(self) -> QWidget:
        return EmptyState(S.UPDATES_EMPTY, S.EMPTY_HINT, icon_name="list", parent=self)

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        page = self.repo.fetch_history(1, 12)
        host = QWidget(self)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("sm"))
        for entry in page.items:
            row = QFrame(host)
            row.setProperty("ui", "card")
            row_layout = QHBoxLayout(row)
            margin = theme.space("m")
            row_layout.setContentsMargins(margin, margin, margin, margin)
            row_layout.setSpacing(theme.space("m"))
            color = QFrame(row)
            color.setFixedSize(theme.px(3), theme.px(40))
            color.setStyleSheet(f"background-color: {theme.color('accent')};")
            row_layout.addWidget(color)
            text = QVBoxLayout()
            title = QLabel(entry.release.title, row)
            title.setStyleSheet("font-weight: 500;")
            text.addWidget(title)
            subtitle = QLabel(f"{entry.episode_name} · {entry.source_name} · {format_date(entry.watch_ts)}", row)
            subtitle.setProperty("role", "tertiary")
            text.addWidget(subtitle)
            row_layout.addLayout(text, 1)
            layout.addWidget(row)
        self._count = len(page.items)
        self.add_content(host, 1)
        self.add_stretch(1)

    def is_empty_result(self) -> bool:
        return getattr(self, "_count", 0) == 0


class NeedAuthScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.NAV_NEED_AUTH)

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xxl"), theme.space("xxl"), theme.space("xxl"), theme.space("xxl"))
        layout.addStretch(1)
        layout.addWidget(EmptyIcon("auth", size=140, parent=wrap), 0, Qt.AlignmentFlag.AlignHCenter)
        title = QLabel(S.NEED_AUTH_TITLE, wrap)
        title.setProperty("role", "section")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        text = QLabel(S.NEED_AUTH_TEXT, wrap)
        text.setProperty("role", "muted")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setMaximumWidth(theme.px(320))
        layout.addWidget(text, 0, Qt.AlignmentFlag.AlignHCenter)
        button = QPushButton(S.NEED_AUTH_ACTION, wrap)
        button.setProperty("ui", "outlined")
        button.setFixedWidth(theme.px(180))
        button.clicked.connect(lambda: self.open_route("auth"))
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)
