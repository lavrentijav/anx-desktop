"""Loading, empty and error states shared by all screens."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..strings import S
from ..theme import active_theme
from .common import EmptyIcon


class Spinner(QWidget):
    def __init__(self, size: int = 32, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        active_theme().changed.connect(self.update)

    def _tick(self) -> None:
        self._angle = (self._angle + 18) % 360
        if self.isVisible():
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(2.0, self._size / 14)
        pen = QPen(theme.qcolor("accent"), width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = QRectF(width, width, self._size - width * 2, self._size - width * 2)
        painter.drawArc(rect, -self._angle * 16, 100 * 16)
        pen.setColor(theme.qcolor("progress_track"))
        painter.setPen(pen)
        painter.drawArc(rect, (-self._angle + 130) * 16, 220 * 16)


class LoadingState(QWidget):
    def __init__(self, text: str = S.LOADING_DATA, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("xxl"), theme.space("xxl"), theme.space("xxl"), theme.space("xxl"))
        layout.setSpacing(theme.space("m"))
        layout.addStretch(1)
        spinner = Spinner(32, parent=self)
        layout.addWidget(spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        label = QLabel(text, self)
        label.setProperty("role", "muted")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch(1)


class EmptyState(QWidget):
    action_clicked = Signal()

    def __init__(
        self,
        title: str = S.EMPTY_TITLE,
        description: str = S.EMPTY_HINT,
        *,
        action_text: str = "",
        icon_name: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setMinimumHeight(theme.px(220))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("xxl"), theme.space("xxl"), theme.space("xxl"), theme.space("xxl"))
        layout.setSpacing(theme.space("m"))
        layout.addStretch(1)
        layout.addWidget(EmptyIcon(icon_name, size=72, parent=self), 0, Qt.AlignmentFlag.AlignHCenter)
        title_label = QLabel(title, self)
        title_label.setProperty("role", "section")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        if description:
            text = QLabel(description, self)
            text.setProperty("role", "muted")
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text.setWordWrap(True)
            text.setMinimumHeight(theme.px(44))
            text.setMaximumWidth(theme.px(420))
            layout.addWidget(text, 0, Qt.AlignmentFlag.AlignHCenter)
        if action_text:
            button = QPushButton(action_text, self)
            button.setProperty("ui", "outlined")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(self.action_clicked)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)


class ErrorState(QWidget):
    retry_clicked = Signal()
    help_clicked = Signal()

    def __init__(
        self,
        title: str = S.ERROR_TITLE,
        description: str = S.ERROR_TEXT,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setMinimumHeight(theme.px(220))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.space("xxl"), theme.space("xxl"), theme.space("xxl"), theme.space("xxl"))
        layout.setSpacing(theme.space("m"))
        layout.addStretch(1)
        layout.addWidget(EmptyIcon("warning", size=72, role="danger", parent=self), 0, Qt.AlignmentFlag.AlignHCenter)
        title_label = QLabel(title, self)
        title_label.setProperty("role", "section")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        text = QLabel(description, self)
        text.setProperty("role", "muted")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setMinimumHeight(theme.px(44))
        text.setMaximumWidth(theme.px(420))
        layout.addWidget(text, 0, Qt.AlignmentFlag.AlignHCenter)
        buttons = QHBoxLayout()
        buttons.setSpacing(theme.space("sm"))
        buttons.addStretch(1)
        help_button = QPushButton(S.HELP, self)
        help_button.setProperty("ui", "outlined")
        help_button.clicked.connect(self.help_clicked)
        buttons.addWidget(help_button)
        retry = QPushButton(S.RETRY, self)
        retry.setProperty("ui", "primary")
        retry.setCursor(Qt.CursorShape.PointingHandCursor)
        retry.clicked.connect(self.retry_clicked)
        buttons.addWidget(retry)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)


class NeedAuthState(EmptyState):
    def __init__(self, description: str = S.NEED_AUTH_TEXT, *, parent: QWidget | None = None) -> None:
        super().__init__(
            S.NEED_AUTH_TITLE,
            description,
            action_text=S.NEED_AUTH_ACTION,
            icon_name="auth",
            parent=parent,
        )
