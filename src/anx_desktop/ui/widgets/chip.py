"""Tabs, filter chips and horizontal scrolling helpers."""

from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)

from ..data import TabSpec
from ..theme import active_theme


class HScrollArea(QScrollArea):
    """Horizontal strip; the wheel scrolls sideways like a carousel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.viewport().setAutoFillBackground(False)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            delta = event.angleDelta().y() or event.angleDelta().x()
            bar = self.horizontalScrollBar()
            if delta and bar.maximum() > 0:
                bar.setValue(bar.value() - delta)
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def setWidget(self, widget: QWidget) -> None:  # noqa: N802
        super().setWidget(widget)
        # Wheel events must scroll the strip even when the cursor is over a
        # chip/button: install the filter on the content and all descendants.
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y() or event.angleDelta().x()
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()


class Chip(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        checkable: bool = True,
        checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("ui", "chip")
        self.setCheckable(checkable)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(active_theme().semantic("tag_height") - active_theme().space("xs"))


class SegmentedButton(QPushButton):
    def __init__(self, text: str, *, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("ui", "segmented")
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class _TabButton(QPushButton):
    """Tab button with an explicit 3 px token-coloured active indicator."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("ui", "tab")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        active_theme().changed.connect(self.update)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self.isChecked():
            return
        theme = active_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.qcolor("accent"))
        width = max(12, self.width() - theme.space("xl"))
        height = max(2, theme.px(3))
        painter.drawRoundedRect(
            QRectF((self.width() - width) / 2, self.height() - height, width, height),
            height / 2,
            height / 2,
        )


class ChipRow(QWidget):
    """A wrapping-ish horizontal row of checkable chips."""

    changed = Signal()

    def __init__(
        self,
        labels: Iterable[str],
        *,
        exclusive: bool = False,
        checked: Iterable[str] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._chips: dict[str, Chip] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(exclusive)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("sm"))
        checked_set = set(checked)
        for label in labels:
            chip = Chip(label, checkable=True, checked=label in checked_set, parent=self)
            chip.toggled.connect(lambda _state: self.changed.emit())
            self._group.addButton(chip)
            self._chips[label] = chip
            layout.addWidget(chip)
        layout.addStretch(1)

    def checked_labels(self) -> list[str]:
        return [label for label, chip in self._chips.items() if chip.isChecked()]

    def set_checked(self, labels: Iterable[str]) -> None:
        wanted = set(labels)
        for label, chip in self._chips.items():
            chip.blockSignals(True)
            chip.setChecked(label in wanted)
            chip.blockSignals(False)
        self.changed.emit()

    def chip(self, label: str) -> Chip | None:
        return self._chips.get(label)


class TabsBar(QWidget):
    """Scrollable top tabs with a 3 px accent underline (8.5.2 pattern)."""

    tab_changed = Signal(str)
    tab_context_requested = Signal(str, QPoint)

    def __init__(
        self,
        tabs: Sequence[TabSpec],
        *,
        current: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._tabs = list(tabs)
        self._buttons: dict[str, QPushButton] = {}
        self._current = current or (self._tabs[0].key if self._tabs else "")
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._scroll = HScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(theme.semantic("toolbar_height") - theme.space("sm"))
        host = QWidget()
        host.setObjectName("tabsHost")
        row = QHBoxLayout(host)
        row.setContentsMargins(theme.semantic("screen_gutter"), 0, theme.semantic("screen_gutter"), 0)
        row.setSpacing(0)
        for spec in self._tabs:
            button = _TabButton(spec.title, host)
            button.setProperty("ui", "tab")
            button.setCheckable(True)
            button.setFixedHeight(self._scroll.height() - theme.space("xxs"))
            button.setChecked(spec.key == self._current)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda pos, key=spec.key, btn=button: self._context(key, btn, pos)
            )
            button.clicked.connect(lambda _checked=False, key=spec.key: self._select(key))
            self._group.addButton(button)
            self._buttons[spec.key] = button
            row.addWidget(button)
        row.addStretch(1)
        self._scroll.setWidget(host)
        outer.addWidget(self._scroll)

    def _context(self, key: str, button: QPushButton, pos: QPoint) -> None:
        self.tab_context_requested.emit(key, button.mapToGlobal(pos))

    def _select(self, key: str) -> None:
        if key == self._current:
            return
        self._current = key
        self.tab_changed.emit(key)

    def current_key(self) -> str:
        return self._current

    def set_current(self, key: str, *, notify: bool = False) -> None:
        button = self._buttons.get(key)
        if button is None:
            return
        self._current = key
        button.setChecked(True)
        if notify:
            self.tab_changed.emit(key)

    def button(self, key: str) -> QPushButton | None:
        return self._buttons.get(key)


class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        *,
        current: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._buttons: dict[str, SegmentedButton] = {}
        self._current = current or (options[0][0] if options else "")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.space("xs"))
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, label in options:
            button = SegmentedButton(label, checked=key == self._current, parent=self)
            button.clicked.connect(lambda _checked=False, k=key: self._select(k))
            group.addButton(button)
            self._buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)

    def _select(self, key: str) -> None:
        if key == self._current:
            return
        self._current = key
        self.changed.emit(key)

    def current_key(self) -> str:
        return self._current

    def set_current(self, key: str) -> None:
        button = self._buttons.get(key)
        if button:
            button.setChecked(True)
            self._current = key
