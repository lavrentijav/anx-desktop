"""Ratings, vote distribution and small statistical charts."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from .. import icons
from ..formatting import format_count, format_rating, voices
from ..strings import S
from ..theme import active_theme


class RatingBadge(QWidget):
    """Small star + numeric rating used in rows and cards."""

    def __init__(self, rating: float | None, *, show_star: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rating = rating
        self._show_star = show_star
        theme = active_theme()
        self.setFixedSize(theme.space("xl") + theme.space("xxl") + theme.space("xs"), theme.space("xl"))
        active_theme().changed.connect(self.update)

    def set_rating(self, rating: float | None) -> None:
        self._rating = rating
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        x = 0
        if self._show_star:
            painter.drawPixmap(0, (self.height() - 16) // 2, icons.pixmap("star", "rating_favorite", 16))
            x = 20
        font = theme.font("body")
        font.setPixelSize(theme.px(14))
        painter.setFont(font)
        painter.setPen(theme.qcolor("text_secondary"))
        painter.drawText(
            QRectF(x, 0, self.width() - x, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            format_rating(self._rating),
        )


class StarRating(QWidget):
    """1–5 star voting control with 0.5 steps and hover preview."""

    rated = Signal(float)

    def __init__(
        self,
        value: float | None = None,
        *,
        star_size: int | None = None,
        interactive: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._value = float(value or 0)
        self._hover = 0.0
        self._interactive = interactive
        self._star = star_size or theme.px(28)
        self._gap = theme.space("xs")
        self.setFixedSize(self._star * 5 + self._gap * 4, self._star)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor if interactive else Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if interactive else Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(S.RATING_ACCESSIBLE_NAME)
        active_theme().changed.connect(self.update)

    def value(self) -> float:
        return self._value

    def set_value(self, value: float | None) -> None:
        self._value = float(value or 0)
        self.update()

    def _value_at(self, x: float) -> float:
        index = int(max(0, min(4, x // (self._star + self._gap))))
        local = x - index * (self._star + self._gap)
        half = local >= self._star / 2
        return min(5.0, index + (1.0 if half else 0.5))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._interactive:
            self._hover = self._value_at(event.position().x())
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = 0.0
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._interactive:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            value = self._value_at(event.position().x())
            self._value = value
            self.update()
            self.rated.emit(value)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._interactive:
            return super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Down):
            self._value = max(0.5, self._value - 0.5)
            self.rated.emit(self._value)
            self.update()
            return
        if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Up):
            self._value = min(5.0, self._value + 0.5)
            self.rated.emit(self._value)
            self.update()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        display = self._hover if self._hover else self._value
        for index in range(5):
            x = index * (self._star + self._gap)
            filled = max(0.0, min(1.0, display - index))
            base = icons.pixmap("star_outline", "icon_secondary", self._star)
            painter.drawPixmap(int(x), 0, base)
            if filled > 0:
                painter.save()
                clip = QRectF(x, 0, self._star * filled, self._star)
                painter.setClipRect(clip)
                painter.drawPixmap(
                    int(x),
                    0,
                    icons.pixmap("star", "icon_alt" if self._interactive else "rating_favorite", self._star),
                )
                painter.restore()


class RatingDistribution(QWidget):
    """Five horizontal bars (5..1), using progress tokens."""

    def __init__(
        self,
        distribution: tuple[int, int, int, int, int],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._distribution = distribution
        self._counts = max(1, sum(distribution))
        self.setMinimumHeight(theme.space("xxxl") + theme.space("xxl"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        font = theme.font("caption")
        font.setPixelSize(theme.px(float(theme.tokens.typography("caption")["size_sp"])))
        painter.setFont(font)
        label_width = theme.space("xl")
        rows = 5
        gap = theme.space("xs")
        bar_h = max(theme.px(7), theme.radius("progress_track"))
        row_h = (self.height() - gap * (rows - 1)) / rows
        max_value = max(1, max(self._distribution))
        for row in range(rows):
            stars = 5 - row
            value = self._distribution[row]
            y = row * (row_h + gap)
            painter.setPen(theme.qcolor("text_secondary"))
            painter.drawText(
                QRectF(0, y, label_width, row_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(stars),
            )
            track = QRectF(
                label_width,
                y + (row_h - bar_h) / 2,
                self.width() - label_width,
                bar_h,
            )
            painter.setBrush(theme.qcolor("progress_track"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(track, bar_h / 2, bar_h / 2)
            fill_width = track.width() * (value / max_value)
            if fill_width > 0:
                painter.setBrush(theme.qcolor("progress_indicator"))
                painter.drawRoundedRect(
                    QRectF(track.left(), track.top(), fill_width, track.height()),
                    bar_h / 2,
                    bar_h / 2,
                )
            percent = round(100 * value / self._counts)
            painter.setPen(theme.qcolor("text_tertiary"))
            painter.drawText(
                QRectF(track.right() - theme.space("xxl"), y, theme.space("xxl"), row_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                f"{percent}%",
            )


class RatingSummary(QWidget):
    """Large 46 sp grade + vote count + distribution."""

    def __init__(
        self,
        grade: float,
        vote_count: int,
        distribution: tuple[int, int, int, int, int],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), theme.space("sm"), theme.semantic("screen_gutter"), theme.space("sm"))
        layout.setSpacing(theme.space("xxl"))
        left = QVBoxLayout()
        left.setSpacing(theme.space("xxs"))
        value = QLabel(format_rating(grade), self)
        font = theme.font("rating_value")
        value.setStyleSheet(
            f"font-family: \"{font.family()}\";"
            f"font-size: {theme.px(float(theme.tokens.typography('rating_value')['size_sp']))}px;"
            " font-weight: 700;"
        )
        left.addWidget(value)
        votes = QLabel(voices(vote_count), self)
        votes.setProperty("role", "tertiary")
        left.addWidget(votes)
        left.addStretch(1)
        layout.addLayout(left, 0)
        distribution_widget = RatingDistribution(distribution, parent=self)
        layout.addWidget(distribution_widget, 1)


class SegmentedStatsBar(QWidget):
    """Collection/profile status bar with colour + text legend elsewhere."""

    def __init__(
        self,
        segments: tuple[tuple[int, str], ...],
        *,
        height: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._segments = tuple((count, role) for count, role in segments if count > 0)
        self._bar_height = height or theme.px(14)
        self.setFixedHeight(self._bar_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        total = sum(count for count, _role in self._segments) or 1
        x = 0.0
        radius = self._bar_height / 2
        for index, (count, role) in enumerate(self._segments):
            width = self.width() * (count / total)
            painter.setBrush(theme.qcolor(role))
            painter.setPen(Qt.PenStyle.NoPen)
            # Round only the outer ends of the whole bar.
            rect = QRectF(x, 0, width + 0.5, self._bar_height)
            painter.save()
            painter.setClipRect(QRectF(0, 0, self.width(), self._bar_height))
            painter.drawRoundedRect(rect, radius, radius)
            painter.restore()
            if index < len(self._segments) - 1:
                painter.setBrush(theme.qcolor("surface"))
                painter.drawRect(QRectF(x + width - 1, 0, 2, self._bar_height))
            x += width


class SparkBars(QWidget):
    """Small watch-dynamics bar chart painted from tokens."""

    def __init__(self, values: tuple[int, ...], *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values = values
        theme = active_theme()
        self.setMinimumHeight(theme.space("xxxl") + theme.space("xl"))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        values = self._values or (0,)
        maximum = max(1, max(values))
        count = len(values)
        gap = max(2, theme.space("xxs"))
        bar_w = max(4.0, (self.width() - gap * (count - 1)) / count)
        base = self.height() - theme.space("sm")
        painter.setPen(Qt.PenStyle.NoPen)
        for index, value in enumerate(values):
            height = max(2.0, (base - theme.space("xs")) * value / maximum)
            rect = QRectF(index * (bar_w + gap), base - height, bar_w, height)
            painter.setBrush(theme.qcolor("progress_indicator" if index % 2 == 0 else "accent_soft_50"))
            painter.drawRoundedRect(rect, min(4.0, bar_w / 2), min(4.0, bar_w / 2))
