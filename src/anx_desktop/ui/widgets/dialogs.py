"""Token-styled dialogs used instead of Android bottom sheets."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..strings import S
from ..theme import active_theme
from .common import Divider, Switch


class BaseDialog(QDialog):
    def __init__(self, title: str, *, width: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(theme.px(width or 420))
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(theme.semantic("dialog_inset_vertical"), theme.semantic("dialog_inset_vertical"), theme.semantic("dialog_inset_vertical"), theme.semantic("dialog_inset_vertical"))
        self._root.setSpacing(theme.semantic("dialog_inset_horizontal"))
        title_label = QLabel(title, self)
        title_label.setProperty("role", "section")
        title_label.setWordWrap(True)
        self._root.addWidget(title_label)
        self._body = QVBoxLayout()
        self._body.setSpacing(theme.space("m"))
        self._root.addLayout(self._body, 1)
        self._root.addWidget(Divider(parent=self))
        self._buttons = QHBoxLayout()
        self._buttons.setSpacing(theme.space("sm"))
        self._buttons.addStretch(1)
        self._root.addLayout(self._buttons)

    def add_body(self, widget: QWidget) -> None:
        self._body.addWidget(widget)

    def add_text(self, text: str, *, role: str = "muted") -> QLabel:
        label = QLabel(text, self)
        label.setProperty("role", role)
        label.setWordWrap(True)
        self._body.addWidget(label)
        return label

    def add_field(self, label: str, widget: QWidget) -> None:
        theme = active_theme()
        wrapper = QVBoxLayout()
        wrapper.setSpacing(theme.space("xs"))
        caption = QLabel(label, self)
        caption.setProperty("role", "muted")
        wrapper.addWidget(caption)
        wrapper.addWidget(widget)
        self._body.addLayout(wrapper)

    def add_primary(self, text: str) -> QPushButton:
        button = QPushButton(text, self)
        button.setProperty("ui", "primary")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setDefault(True)
        self._buttons.addWidget(button)
        return button

    def add_outlined(self, text: str) -> QPushButton:
        button = QPushButton(text, self)
        button.setProperty("ui", "outlined")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._buttons.addWidget(button)
        return button

    def add_cancel(self, text: str = S.CANCEL) -> QPushButton:
        button = self.add_outlined(text)
        button.clicked.connect(self.reject)
        return button


class MessageDialog(BaseDialog):
    def __init__(self, title: str, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(title, parent=parent)
        self.add_text(text)
        ok = self.add_primary(S.OK)
        ok.clicked.connect(self.accept)


class ConfirmDialog(BaseDialog):
    def __init__(
        self,
        title: str,
        text: str,
        *,
        confirm_text: str = S.OK,
        cancel_text: str = S.CANCEL,
        destructive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent=parent)
        self.add_text(text)
        self.add_cancel(cancel_text)
        confirm = self.add_primary(confirm_text) if not destructive else self.add_outlined(confirm_text)
        if destructive:
            confirm.setProperty("ui", "danger")
            confirm.style().unpolish(confirm)
            confirm.style().polish(confirm)
        confirm.clicked.connect(self.accept)


class TextInputDialog(BaseDialog):
    def __init__(
        self,
        title: str,
        label: str,
        *,
        placeholder: str = "",
        multiline: bool = False,
        confirm_text: str = S.SAVE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent=parent)
        theme = active_theme()
        self._multiline = multiline
        if multiline:
            self._input = QPlainTextEdit(self)
            self._input.setPlaceholderText(placeholder)
            self._input.setMinimumHeight(theme.px(140))
        else:
            self._input = QLineEdit(self)
            self._input.setPlaceholderText(placeholder)
        self.add_field(label, self._input)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        self.add_cancel()
        confirm = self.add_primary(confirm_text)
        confirm.clicked.connect(self._accept_if_valid)

    def _accept_if_valid(self) -> None:
        if not self.text().strip():
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return
        self.accept()

    def text(self) -> str:
        if self._multiline:
            return self._input.toPlainText()
        return self._input.text()


class ReportDialog(BaseDialog):
    def __init__(self, target: str, *, parent: QWidget | None = None) -> None:
        super().__init__(S.REPORT_TITLE, parent=parent)
        self.add_text(target)
        self.reason = QComboBox(self)
        self.reason.addItems(S.REPORT_REASONS)
        self.add_field(S.REPORT_REASON, self.reason)
        self.message = QPlainTextEdit(self)
        self.message.setPlaceholderText(S.REPORT_MESSAGE)
        self.message.setMaximumHeight(active_theme().px(110))
        self.add_field(S.REPORT_MESSAGE, self.message)
        self.add_cancel()
        send = self.add_primary(S.SEND)
        send.clicked.connect(self.accept)


@dataclass
class ArticleDraft:
    title: str
    body: str


class ComposeArticleDialog(BaseDialog):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(S.ARTICLE_CREATE, width=560, parent=parent)
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText(S.CREATE_ARTICLE_TEXT)
        self.add_field(S.ARTICLE_TITLE_FIELD, self.title_input)
        self.body_input = QPlainTextEdit(self)
        self.body_input.setPlaceholderText(S.CREATE_ARTICLE_BODY)
        self.body_input.setMinimumHeight(active_theme().px(180))
        self.add_field(S.ARTICLE_TEXT_FIELD, self.body_input)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        self.add_cancel()
        preview = self.add_outlined(S.ARTICLE_PREVIEW)
        preview.clicked.connect(self._preview)
        publish = self.add_primary(S.ARTICLE_SEND)
        publish.clicked.connect(self._publish)

    def _valid(self) -> bool:
        if not self.title_input.text().strip() or not self.body_input.toPlainText().strip():
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return False
        return True

    def _preview(self) -> None:
        if not self._valid():
            return
        MessageDialog(S.ARTICLE_ALMOST_READY, self.title_input.text(), parent=self).exec()

    def _publish(self) -> None:
        if self._valid():
            self.accept()

    def draft(self) -> ArticleDraft:
        return ArticleDraft(self.title_input.text().strip(), self.body_input.toPlainText().strip())


class ComposeChannelDialog(BaseDialog):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(S.CHANNELS_CREATE, parent=parent)
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText(S.CHANNELS_TITLE_HINT)
        self.add_field(S.ARTICLE_TITLE_FIELD, self.title_input)
        self.description_input = QLineEdit(self)
        self.description_input.setPlaceholderText(S.CHANNELS_DESCRIPTION_HINT)
        self.add_field(S.CHANNELS_DESCRIPTION_HINT, self.description_input)
        self.comments = Switch(True, self)
        self.suggestions = Switch(True, self)
        row = QHBoxLayout()
        row.addWidget(QLabel(S.CHANNELS_COMMENTS, self))
        row.addStretch(1)
        row.addWidget(self.comments)
        self._body.addLayout(row)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(S.CHANNELS_SUGGESTIONS, self))
        row2.addStretch(1)
        row2.addWidget(self.suggestions)
        self._body.addLayout(row2)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        self.add_cancel()
        create = self.add_primary(S.CREATE)
        create.clicked.connect(self._create)

    def _create(self) -> None:
        length = len(self.title_input.text().strip())
        if length < 10 or length > 60:
            self._error.setText(S.CHANNELS_INVALID_TITLE)
            self._error.show()
            return
        self.accept()

    def channel_name(self) -> str:
        return self.title_input.text().strip()

    def channel_description(self) -> str:
        return self.description_input.text().strip()


class ClaimBadgeDialog(BaseDialog):
    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(S.BADGES_CLAIM, parent=parent)
        self.add_text(S.BADGES_CLAIM_HINT)
        self.code_input = QLineEdit(self)
        self.code_input.setPlaceholderText(S.BADGES_CLAIM_PLACEHOLDER)
        self.add_field(S.BADGES_CLAIM, self.code_input)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        self.add_cancel()
        claim = self.add_primary(S.BADGES_CLAIM_ACTION)
        claim.clicked.connect(self._claim)

    def _claim(self) -> None:
        if not self.code_input.text().strip():
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return
        self.accept()

    def code(self) -> str:
        return self.code_input.text().strip()


class QrConfirmDialog(BaseDialog):
    """Desktop stand-in for the phone-side QR approval screen."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(S.AUTH_QR_CONFIRM_TITLE, parent=parent)
        self.add_text(S.AUTH_QR_CONFIRM_WARNING)
        self.add_text(S.AUTH_QR_CONFIRM_ACCOUNT + ": nickname · Desktop")
        self.add_text(S.AUTH_QR_CONFIRM_DEVICE + ": Windows / Linux")
        self.code_input = QLineEdit(self)
        self.code_input.setMaxLength(4)
        self.code_input.setPlaceholderText("0000")
        self.add_field(S.AUTH_QR_CONFIRM_CODE, self.code_input)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        decline = self.add_outlined(S.AUTH_QR_DECLINE)
        decline.clicked.connect(self.reject)
        allow = self.add_primary(S.AUTH_QR_ALLOW)
        allow.clicked.connect(self._allow)

    def _allow(self) -> None:
        if len(self.code_input.text().strip()) != 4:
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return
        self.accept()


class PasswordConfirmDialog(BaseDialog):
    def __init__(self, title: str, text: str, *, parent: QWidget | None = None) -> None:
        super().__init__(title, parent=parent)
        self.add_text(text)
        self.password = QLineEdit(self)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_field(S.AUTH_PASSWORD, self.password)
        self._error = QLabel("", self)
        self._error.setProperty("role", "danger")
        self._error.hide()
        self.add_body(self._error)
        self.add_cancel()
        confirm = self.add_primary(S.DELETE)
        confirm.clicked.connect(self._confirm)

    def _confirm(self) -> None:
        if not self.password.text().strip():
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return
        self.accept()


def confirm(parent: QWidget, title: str, text: str, *, confirm_text: str = S.OK, destructive: bool = False) -> bool:
    dialog = ConfirmDialog(title, text, confirm_text=confirm_text, destructive=destructive, parent=parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
