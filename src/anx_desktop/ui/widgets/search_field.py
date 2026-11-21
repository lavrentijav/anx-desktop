"""Search capsule (48 dp / radius 24) with clear, voice and filter actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLineEdit, QWidget

from .. import icons
from ..strings import S
from ..theme import active_theme


class SearchField(QLineEdit):
    submitted = Signal(str)
    filter_clicked = Signal()
    mic_clicked = Signal()
    cleared = Signal()

    def __init__(
        self,
        placeholder: str = S.SEARCH_PLACEHOLDER,
        *,
        show_mic: bool = True,
        show_filter: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(False)
        self.setFont(theme.font("search_placeholder"))
        self.setMinimumWidth(theme.px(220))
        self.setMaximumWidth(theme.px(480))
        self.setAccessibleName(placeholder)
        self._search_action = QAction(self)
        self._search_action.setEnabled(False)
        self.addAction(self._search_action, QLineEdit.ActionPosition.LeadingPosition)
        self._clear_action = QAction(self)
        self._clear_action.setToolTip(S.CLEAR)
        self._clear_action.triggered.connect(self._clear)
        self.addAction(self._clear_action, QLineEdit.ActionPosition.TrailingPosition)
        self._mic_action = QAction(self)
        self._mic_action.setToolTip(S.SEARCH_VOICE)
        self._mic_action.triggered.connect(self.mic_clicked)
        self._mic_action.setVisible(show_mic)
        self.addAction(self._mic_action, QLineEdit.ActionPosition.TrailingPosition)
        self._filter_action = QAction(self)
        self._filter_action.setToolTip(S.TOOLTIP_FILTER)
        self._filter_action.triggered.connect(self.filter_clicked)
        self._filter_action.setVisible(show_filter)
        self.addAction(self._filter_action, QLineEdit.ActionPosition.TrailingPosition)
        self.textChanged.connect(self._on_text)
        self.returnPressed.connect(self._on_submit)
        self._refresh_icons()
        self._on_text("")
        active_theme().changed.connect(self._refresh_icons)

    def _refresh_icons(self) -> None:
        self._search_action.setIcon(icons.icon("search", "text_secondary", 18))
        self._clear_action.setIcon(icons.icon("close", "icon", 16))
        self._mic_action.setIcon(icons.icon("microphone", "icon", 18))
        self._filter_action.setIcon(icons.icon("filter", "icon", 18))

    def _on_text(self, text: str) -> None:
        self._clear_action.setVisible(bool(text))
        self._mic_action.setVisible(not text and self._mic_action.isEnabled())
        if not text:
            self.cleared.emit()

    def _on_submit(self) -> None:
        self.submitted.emit(self.text().strip())

    def _clear(self) -> None:
        self.clear()
        self.cleared.emit()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def set_filter_visible(self, visible: bool) -> None:
        self._filter_action.setVisible(visible)

    def set_mic_visible(self, visible: bool) -> None:
        self._mic_action.setEnabled(visible)
        self._mic_action.setVisible(visible and not self.text())
