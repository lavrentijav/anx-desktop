"""Responsive poster grid used by catalog screens."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from ..theme import active_theme


class CardGrid(QWidget):
    """Re-layouts fixed-width cards into as many columns as fit."""

    def __init__(
        self,
        cards: Sequence[QWidget] = (),
        *,
        min_card_width: int = 130,
        max_columns: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        theme = active_theme()
        self._min_width = min_card_width
        self._max_columns = max_columns
        self._cards: list[QWidget] = list(cards)
        self._grid = QGridLayout(self)
        self._grid.setSizeConstraint(QGridLayout.SizeConstraint.SetNoConstraint)
        self._grid.setContentsMargins(
            theme.semantic("grid_outer_padding"),
            theme.semantic("grid_outer_padding"),
            theme.semantic("grid_outer_padding"),
            theme.semantic("screen_gutter"),
        )
        self._grid.setHorizontalSpacing(theme.semantic("grid_gap"))
        self._grid.setVerticalSpacing(theme.semantic("grid_gap") * 2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._columns = 0
        self._relayoutting = False
        self._relayout()

    def _column_width(self) -> int:
        card_width = max(
            (max(card.minimumWidth(), card.minimumSizeHint().width()) for card in self._cards),
            default=0,
        )
        return max(self._min_width, card_width)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        if self._cards:
            margins = self._grid.contentsMargins()
            # The current number of columns must not prevent the parent from shrinking.
            hint.setWidth(self._column_width() + margins.left() + margins.right())
        return hint

    def _columns_for_width(self) -> int:
        gap = self._grid.horizontalSpacing()
        margins = self._grid.contentsMargins()
        available = self.contentsRect().width() - margins.left() - margins.right()
        columns = max(1, (available + gap) // (self._column_width() + gap))
        if self._max_columns:
            columns = min(columns, self._max_columns)
        return min(columns, len(self._cards) or 1)

    def _relayout(self) -> None:
        if self._relayoutting:
            return
        self._relayoutting = True
        try:
            columns = self._columns_for_width()
            if columns == self._columns and self._grid.count() == len(self._cards):
                return
            self._columns = columns
            while self._grid.count():
                self._grid.takeAt(0)
            for column in range(self._grid.columnCount()):
                self._grid.setColumnStretch(column, 0)
            for row in range(self._grid.rowCount()):
                self._grid.setRowStretch(row, 0)
            for index, card in enumerate(self._cards):
                self._grid.addWidget(card, index // columns, index % columns, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
                card.show()
            for column in range(columns):
                self._grid.setColumnStretch(column, 1)
            self._grid.setRowStretch((len(self._cards) + columns - 1) // columns, 1)
            self.updateGeometry()
        finally:
            self._relayoutting = False

    def add_cards(self, cards: Sequence[QWidget]) -> None:
        self._cards.extend(cards)
        for card in cards:
            card.setParent(self)
        self._columns = -1
        self._relayout()
        self.updateGeometry()

    def clear_cards(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._cards.clear()
        self._columns = 0
        self._relayout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()
