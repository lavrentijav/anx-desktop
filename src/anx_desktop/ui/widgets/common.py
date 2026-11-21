"""Shared small components built only from 8.5.2 tokens."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons
from ..strings import S
from ..theme import active_theme


class IconButton(QToolButton):
    """Themed icon button that repaints when the palette changes."""

    def __init__(
        self,
        icon_name: str,
        *,
        role: str = "icon",
        size: int = 24,
        tooltip: str = "",
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._role = role
        self._size = size
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip or icon_name)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(size, size))
        self.setProperty("ui", "icon")
        self._refresh_icon()
        active_theme().changed.connect(self._refresh_icon)

    def set_icon(self, name: str, role: str | None = None) -> None:
        self._icon_name = name
        if role is not None:
            self._role = role
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        self.setIcon(icons.icon(self._icon_name, self._role, self._size))


class Avatar(QWidget):
    """Neutral initials avatar with token-based gradient."""

    def __init__(
        self,
        name: str = "",
        *,
        size: int = 48,
        seed: int = 0,
        online: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._seed = seed
        self._online = online
        self._size = size
        self.setFixedSize(size, size)
        self.setAccessibleName(name)
        active_theme().changed.connect(self.update)

    def set_name(self, name: str, seed: int | None = None) -> None:
        self._name = name
        if seed is not None:
            self._seed = seed
        self.update()

    def set_online(self, online: bool) -> None:
        self._online = online
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        palette = (
            theme.qcolor("poster_placeholder_start"),
            theme.qcolor("poster_placeholder_end"),
            theme.qcolor("surface_tertiary"),
            theme.qcolor("collection_card_header"),
        )
        first = palette[self._seed % len(palette)]
        second = palette[(self._seed // 2 + 1) % len(palette)]
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, first)
        gradient.setColorAt(1, second)
        painter.setBrush(gradient)
        painter.setPen(QPen(theme.qcolor("border_image"), 1))
        painter.drawEllipse(rect)
        initials = "".join(part[:1].upper() for part in self._name.replace("_", " ").split()[:2]) or "?"
        font = theme.font("body_medium", bold=True)
        font.setPixelSize(max(11, int(self._size * 0.34)))
        painter.setFont(font)
        painter.setPen(theme.qcolor("text_secondary"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initials)
        if self._online:
            dot = max(10, self._size // 4)
            dot_rect = self.rect().adjusted(self._size - dot, self._size - dot, 0, 0)
            painter.setPen(QPen(theme.qcolor("background"), 2))
            painter.setBrush(theme.qcolor("success"))
            painter.drawEllipse(dot_rect.adjusted(1, 1, -1, -1))


class LogoMark(QWidget):
    def __init__(self, size: int = 40, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawPixmap(0, 0, icons.logo_pixmap(self._size))


class Divider(QFrame):
    def __init__(self, *, vertical: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("ui", "divider")
        if vertical:
            self.setFixedWidth(1)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setFixedHeight(1)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class SectionHeader(QWidget):
    show_all = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        action_text: str = S.SHOW_ALL,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        layout.setSpacing(theme.space("sm"))
        self._title = QLabel(title, self)
        self._title.setProperty("role", "section")
        layout.addWidget(self._title)
        if subtitle:
            self._subtitle = QLabel(subtitle, self)
            self._subtitle.setProperty("role", "muted")
            layout.addWidget(self._subtitle)
        layout.addStretch(1)
        self._action = QPushButton(action_text, self)
        self._action.setProperty("ui", "text")
        self._action.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action.clicked.connect(self.show_all)
        self._action.setVisible(bool(action_text))
        layout.addWidget(self._action)
        self.setMinimumHeight(theme.semantic("section_header_height"))

    def set_action_visible(self, visible: bool) -> None:
        self._action.setVisible(visible)

    def set_title(self, title: str) -> None:
        self._title.setText(title)


class InfoBanner(QFrame):
    action_clicked = Signal()
    closed = Signal()

    def __init__(
        self,
        text: str,
        *,
        action_text: str = "",
        icon_name: str = "info",
        title: str = "",
        closable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "info")
        layout = QHBoxLayout(self)
        margins = theme.space("m")
        layout.setContentsMargins(margins, margins, margins, margins)
        layout.setSpacing(theme.space("m"))
        icon = make_icon_label(icon_name, "info_text", 20, self)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        text_box = QVBoxLayout()
        text_box.setSpacing(theme.space("xxs"))
        if title:
            title_label = QLabel(title, self)
            title_label.setProperty("role", "muted")
            title_label.setWordWrap(True)
            text_box.addWidget(title_label)
        label = QLabel(text, self)
        label.setWordWrap(True)
        label.setProperty("role", "muted")
        text_box.addWidget(label)
        layout.addLayout(text_box, 1)
        if action_text:
            button = QPushButton(action_text, self)
            button.setProperty("ui", "text")
            button.clicked.connect(self.action_clicked)
            layout.addWidget(button)
        if closable:
            close = IconButton("close", tooltip=S.TOOLTIP_CLOSE, size=18, parent=self)
            close.clicked.connect(self._close)
            layout.addWidget(close)

    def _close(self) -> None:
        self.closed.emit()
        self.hide()


class Switch(QWidget):
    """Material-style switch painted from tokens."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = bool(checked)
        self._offset = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(42, 24)
        self.setAccessibleName(S.SWITCH_ACCESSIBLE_NAME)
        active_theme().changed.connect(self.update)

    def isChecked(self) -> bool:  # noqa: N802 - Qt naming
        return self._checked

    def setChecked(self, checked: bool, *, animate: bool = True) -> None:  # noqa: N802
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0
        if animate:
            self._animation.stop()
            self._animation.setStartValue(self._offset)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._offset = target
            self.update()
        self.toggled.emit(checked)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 2, -1, -2)
        radius = rect.height() / 2
        track = theme.qcolor("switch_track_on" if self._checked else "switch_track_off")
        if not self._checked:
            painter.setPen(QPen(theme.qcolor("switch_outline"), 1.5))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, radius, radius)
        knob_d = rect.height() - 4
        x = rect.left() + 2 + (rect.width() - knob_d - 4) * self._offset
        knob = theme.qcolor("switch_thumb_on") if self._checked else theme.qcolor("text_tertiary")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob)
        painter.drawEllipse(int(x), rect.top() + 2, knob_d, knob_d)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(theme.qcolor("accent"), 2))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


class SettingRow(QWidget):
    """A clickable preference row (title + summary + trailing control)."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        summary: str = "",
        *,
        icon_name: str = "",
        trailing: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(theme.semantic("settings_row_min_height"))
        layout = QHBoxLayout(self)
        h = theme.semantic("screen_gutter")
        v = theme.semantic("settings_row_padding_vertical")
        layout.setContentsMargins(h, v, h, v)
        layout.setSpacing(theme.space("m"))
        if icon_name:
            icon_label = make_icon_label(icon_name, "icon", 22, self)
            icon_label.setFixedSize(24, 24)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)
        text_box = QVBoxLayout()
        text_box.setSpacing(theme.space("xxs"))
        title_label = QLabel(title, self)
        title_label.setProperty("role", "body")
        title_label.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('settings_title')['size_sp']))}px;"
            " font-weight: 500;"
        )
        title_label.setWordWrap(True)
        text_box.addWidget(title_label)
        if summary:
            summary_label = QLabel(summary, self)
            summary_label.setProperty("role", "tertiary")
            summary_label.setWordWrap(True)
            text_box.addWidget(summary_label)
        layout.addLayout(text_box, 1)
        if trailing is not None:
            layout.addWidget(trailing, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            chevron = make_icon_label("chevron_right", "icon", 18, self)
            layout.addWidget(chevron)
        self._trailing = trailing

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ClickableFrame(QFrame):
    clicked = Signal()
    context_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        self.context_requested.emit(event.globalPos())
        event.accept()


class TextBadge(QLabel):
    def __init__(
        self,
        text: str,
        *,
        role: str = "muted",
        background: str = "surface_tertiary",
        radius: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._role = role
        self._background = background
        self._radius = radius
        self.setProperty("role", role)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_style()
        active_theme().changed.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        theme = active_theme()
        self.setStyleSheet(
            f"background-color: {theme.color(self._background)};"
            f"border-radius: {theme.px(self._radius)}px;"
            f"padding: {theme.space('xxs')}px {theme.space('xs')}px;"
            f"font-size: {theme.px(float(theme.tokens.typography('caption')['size_sp']))}px;"
        )


class CountBadge(QLabel):
    """Notification counter badge (red pill)."""

    def __init__(self, count: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(theme.px(20))
        self._refresh_style()
        self.set_count(count)
        active_theme().changed.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        theme = active_theme()
        self.setStyleSheet(
            f"background-color: {theme.color('badge')};"
            f"color: {theme.color('badge_text')};"
            f"border-radius: {theme.px(10)}px;"
            f"padding: {theme.space('xxs')}px {theme.space('xs')}px;"
            f"font-size: {theme.px(float(theme.tokens.typography('badge')['size_sp']))}px;"
            " font-weight: 600;"
        )

    def set_count(self, count: int) -> None:
        self.setText(str(min(count, 99)))
        self.setVisible(count > 0)


def elide_label(label: QLabel, text: str, width: int) -> None:
    metrics = QFontMetrics(label.font())
    label.setText(metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(20, width)))


class _ThemedIconLabel(QLabel):
    def __init__(self, name: str, role: str, size: int, parent: QWidget | None) -> None:
        super().__init__(parent)
        self._icon_spec = (name, role, size)
        self.setFixedSize(size, size)
        self._refresh_icon()
        active_theme().changed.connect(self._refresh_icon)

    def _refresh_icon(self) -> None:
        self.setPixmap(icons.pixmap(*self._icon_spec))


def make_icon_label(name: str, role: str = "icon", size: int = 20, parent: QWidget | None = None) -> QLabel:
    return _ThemedIconLabel(name, role, size, parent)


def paint_placeholder(
    painter: QPainter,
    rect,
    *,
    seed: int = 0,
    radius: int = 6,
    accent: bool = False,
) -> None:
    """Neutral poster/image placeholder with a soft gradient and glyph."""

    theme = active_theme()
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.save()
    painter.setClipPath(path)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    if accent:
        gradient.setColorAt(0, theme.qcolor("accent_soft_20"))
        gradient.setColorAt(1, theme.qcolor("surface_tertiary"))
    else:
        gradient.setColorAt(0, theme.qcolor("poster_placeholder_start"))
        gradient.setColorAt(1, theme.qcolor("poster_placeholder_end"))
    painter.fillRect(rect, gradient)
    painter.setPen(QPen(theme.qcolor("border_image"), 1))
    cx, cy = rect.center().x(), rect.center().y()
    span = min(rect.width(), rect.height()) * 0.25
    offset = (seed % 5) * span * 0.12
    painter.drawEllipse(rect.center(), span + offset, span + offset)
    painter.drawLine(cx - span, cy + span * 0.6, cx + span, cy + span * 0.6)
    painter.setBrush(theme.qcolor("surface_secondary"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(rect.center(), span * 0.16, span * 0.16)
    painter.restore()


class EmptyIcon(QWidget):
    """Neutral illustration placeholder for empty/error states."""

    def __init__(self, icon_name: str = "info", *, size: int = 72, role: str = "icon", parent=None) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self._role = role
        self._size = size
        self.setFixedSize(size, size)
        active_theme().changed.connect(self.update)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setBrush(theme.qcolor("surface_tertiary"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)
        painter.drawPixmap(
            rect.center().x() - self._size // 4,
            rect.center().y() - self._size // 4,
            icons.pixmap(self._icon_name, self._role, self._size // 2),
        )
