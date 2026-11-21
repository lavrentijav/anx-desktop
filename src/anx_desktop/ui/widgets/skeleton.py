"""Neutral skeleton/shimmer placeholders.

The 8.5.2 resources do not contain a skeleton component (documented UNKNOWN);
this is an explicitly clean-room addition built with the same token rhythm.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ..theme import active_theme


class SkeletonBlock(QWidget):
    def __init__(
        self,
        width: int | None = None,
        height: int = 12,
        *,
        radius: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._phase = 0.0
        self._radius = radius if radius is not None else theme.radius("tag") // 2
        if width is not None:
            self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed if width is not None else QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        active_theme().changed.connect(self.update)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.022) % 1.4
        if self.isVisible():
            self.update()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        if not self._timer.isActive():
            self._timer.start()
        super().showEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setBrush(theme.qcolor("surface_tertiary"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self._radius, self._radius)
        highlight = QColor(theme.color("surface_secondary"))
        highlight.setAlpha(165)
        clear = QColor(theme.color("surface_tertiary"))
        clear.setAlpha(0)
        gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)
        start = self._phase - 0.35
        gradient.setColorAt(max(0.0, min(1.0, start)), clear)
        gradient.setColorAt(max(0.0, min(1.0, start + 0.22)), highlight)
        gradient.setColorAt(max(0.0, min(1.0, start + 0.45)), clear)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, self._radius, self._radius)


class SkeletonRow(QWidget):
    def __init__(self, *, lines: int = 3, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        width, height = theme.tokens.list_poster_size()
        self.setMinimumHeight(height + theme.space("l"))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            theme.semantic("list_row_padding_horizontal"),
            theme.semantic("list_row_padding_vertical"),
            theme.semantic("list_row_padding_end"),
            theme.semantic("list_row_padding_vertical"),
        )
        layout.setSpacing(theme.semantic("list_poster_to_text_gap"))
        layout.addWidget(SkeletonBlock(width, height, radius=theme.radius("poster_card")))
        content = QVBoxLayout()
        content.setSpacing(theme.space("sm"))
        content.addWidget(SkeletonBlock(None, theme.px(18)))
        content.addWidget(SkeletonBlock(width * 2, theme.px(12)))
        for index in range(max(0, lines - 2)):
            content.addWidget(SkeletonBlock(None, theme.px(10)))
        content.addStretch(1)
        layout.addLayout(content, 1)


class SkeletonList(QWidget):
    def __init__(self, count: int = 6, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, theme.space("sm"), 0, theme.semantic("screen_gutter"))
        layout.setSpacing(0)
        for _ in range(count):
            layout.addWidget(SkeletonRow(parent=self))
        layout.addStretch(1)


class SkeletonCard(QWidget):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        width, height = theme.tokens.compact_poster_size()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        layout.addWidget(SkeletonBlock(width, height, radius=theme.radius("poster_card")))
        layout.addWidget(SkeletonBlock(width - theme.space("xl"), theme.px(13)))
        layout.addWidget(SkeletonBlock(width - theme.space("xxxl"), theme.px(10)))
        self.setFixedWidth(width + theme.space("sm"))


class SkeletonGrid(QWidget):
    def __init__(self, *, columns: int = 4, rows: int = 2, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QGridLayout(self)
        layout.setContentsMargins(
            theme.semantic("grid_outer_padding"),
            theme.semantic("grid_outer_padding"),
            theme.semantic("grid_outer_padding"),
            theme.semantic("screen_gutter"),
        )
        layout.setHorizontalSpacing(theme.semantic("grid_gap"))
        layout.setVerticalSpacing(theme.semantic("grid_gap") * 2)
        for index in range(columns * rows):
            layout.addWidget(SkeletonCard(parent=self), index // columns, index % columns)
        layout.setColumnStretch(columns, 1)
        layout.setRowStretch(rows, 1)


class SkeletonDetail(QWidget):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            theme.semantic("screen_gutter"),
            theme.semantic("screen_gutter"),
            theme.semantic("screen_gutter"),
            theme.semantic("screen_gutter"),
        )
        layout.setSpacing(theme.space("xxl"))
        poster_w = theme.px(280)
        poster_h = theme.px(396)
        layout.addWidget(SkeletonBlock(poster_w, poster_h, radius=theme.radius("release_detail_poster")), 0, Qt.AlignmentFlag.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(theme.space("m"))
        right.addWidget(SkeletonBlock(None, theme.px(30)))
        right.addWidget(SkeletonBlock(theme.px(220), theme.px(14)))
        right.addWidget(SkeletonBlock(None, theme.px(14)))
        right.addSpacing(theme.space("m"))
        right.addWidget(SkeletonBlock(None, theme.px(52)))
        right.addSpacing(theme.space("m"))
        for fraction in (1.0, 0.92, 0.84, 0.7):
            row = SkeletonBlock(None, theme.px(12))
            row.setMaximumWidth(int(520 * fraction))
            right.addWidget(row)
        right.addSpacing(theme.space("xl"))
        for _ in range(3):
            right.addWidget(SkeletonBlock(None, theme.px(16)))
        right.addStretch(1)
        layout.addLayout(right, 1)


class SkeletonSections(QWidget):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("m"), theme.semantic("screen_gutter"), theme.semantic("screen_gutter"))
        layout.setSpacing(theme.space("xl"))
        banner = SkeletonBlock(None, theme.px(160), radius=theme.radius("collection_card"))
        layout.addWidget(banner)
        for _ in range(2):
            layout.addWidget(SkeletonBlock(theme.px(180), theme.px(20)))
            row = QHBoxLayout()
            row.setSpacing(theme.semantic("grid_gap"))
            for _ in range(4):
                row.addWidget(SkeletonCard(parent=self))
            row.addStretch(1)
            layout.addLayout(row)
        layout.addStretch(1)
