"""Pagination footer and near-end scroll signal for infinite lists."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget

from ..strings import S
from ..theme import active_theme
from .empty_state import Spinner


class FooterLoader(QWidget):
    load_more = Signal()

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, theme.space("m"), 0, theme.space("m"))
        layout.setSpacing(theme.space("sm"))
        layout.addStretch(1)
        self._spinner = Spinner(24, parent=self)
        self._spinner.hide()
        layout.addWidget(self._spinner)
        self._label = QLabel("", self)
        self._label.setProperty("role", "muted")
        layout.addWidget(self._label)
        self._button = QPushButton(S.SHOW_MORE, self)
        self._button.setProperty("ui", "outlined")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self.load_more)
        layout.addWidget(self._button)
        layout.addStretch(1)
        self.set_done()

    def set_loading(self) -> None:
        self._spinner.show()
        self._label.setText(S.LOADING)
        self._button.hide()
        self.show()

    def set_idle(self) -> None:
        self._spinner.hide()
        self._label.setText("")
        self._button.setText(S.SHOW_MORE)
        self._button.show()
        self.show()

    def set_done(self) -> None:
        self._spinner.hide()
        self._label.setText("")
        self._button.hide()
        self.show()

    def set_hidden(self) -> None:
        self.hide()


class NearEndScrollArea(QScrollArea):
    near_end = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_scroll(self, value: int) -> None:
        bar = self.verticalScrollBar()
        if bar.maximum() <= 0:
            return
        if value >= bar.maximum() * 0.82:
            self.near_end.emit()

    def is_near_end(self) -> bool:
        bar = self.verticalScrollBar()
        return bar.maximum() > 0 and bar.value() >= bar.maximum() * 0.82
