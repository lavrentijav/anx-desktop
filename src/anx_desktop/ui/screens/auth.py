"""Авторизация: hub, e-mail login, registration, password restore and QR."""

from __future__ import annotations

import random

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...api.errors import AnixartError
from .. import icons
from ..strings import S
from ..theme import active_theme
from ..widgets import LogoMark, Spinner
from ..widgets.dialogs import MessageDialog, QrConfirmDialog
from .base import BaseScreen


class AuthCard(QFrame):
    def __init__(self, *, width: int = 460, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        theme = active_theme()
        self.setProperty("ui", "panel")
        self.setFixedWidth(theme.px(width))
        self.layout_box = QVBoxLayout(self)
        margin = theme.space("xl")
        self.layout_box.setContentsMargins(margin, margin, margin, margin)
        self.layout_box.setSpacing(theme.space("m"))


class ClickableLabel(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class AuthScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.AUTH_TITLE)
        self.payload = None

    def set_payload(self, payload) -> None:
        self.payload = payload

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xl"), theme.space("xl"), theme.space("xl"), theme.space("xl"))
        layout.addStretch(1)
        card = AuthCard(parent=wrap)
        header = QHBoxLayout()
        header.addWidget(LogoMark(64, parent=card))
        name = QLabel(S.APP_NAME, card)
        name.setProperty("role", "logo")
        name.setStyleSheet(
            f"font-size: {theme.px(float(theme.tokens.typography('logo_display')['size_sp']))}px;"
        )
        header.addWidget(name)
        header.addStretch(1)
        card.layout_box.addLayout(header)
        email = self._email_button(card)
        email.clicked.connect(lambda: self.open_route("auth_email"))
        card.layout_box.addWidget(email)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _email_button(self, parent: QWidget) -> QPushButton:
        button = QPushButton(S.AUTH_EMAIL, parent)
        button.setProperty("ui", "outlined")
        button.setIcon(icons.icon("mail", "icon_alt", 18))
        button.setIconSize(QSize(18, 18))
        button.setMinimumHeight(active_theme().semantic("button_height_small") - 6)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button


class EmailAuthScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.AUTH_EMAIL)
        self._login: QLineEdit | None = None
        self._password: QLineEdit | None = None
        self._error: QLabel | None = None

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xl"), theme.space("xl"), theme.space("xl"), theme.space("xl"))
        layout.addStretch(1)
        card = AuthCard(parent=wrap)
        title = QLabel(S.AUTH_WELCOME, card)
        title.setProperty("role", "title")
        card.layout_box.addWidget(title)
        subtitle = QLabel(S.AUTH_WELCOME_HINT, card)
        subtitle.setProperty("role", "muted")
        card.layout_box.addWidget(subtitle)
        self._login = QLineEdit(card)
        self._login.setPlaceholderText(S.AUTH_EMAIL_OR_NICK)
        card.layout_box.addWidget(self._login)
        self._password = QLineEdit(card)
        self._password.setPlaceholderText(S.AUTH_PASSWORD)
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._add_eye(self._password)
        card.layout_box.addWidget(self._password)
        self._error = QLabel("", card)
        self._error.setProperty("role", "danger")
        self._error.setWordWrap(True)
        self._error.hide()
        card.layout_box.addWidget(self._error)
        login = QPushButton(S.AUTH_LOGIN, card)
        login.setProperty("ui", "primary")
        login.clicked.connect(lambda: self._submit(login))
        self._login.returnPressed.connect(login.click)
        self._password.returnPressed.connect(login.click)
        card.layout_box.addWidget(login, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _add_eye(self, field: QLineEdit) -> None:
        action = QAction(field)
        action.setToolTip(S.AUTH_SHOW_PASSWORD)
        action.setIcon(icons.icon("eye", "icon", 18))

        def toggle() -> None:
            hidden = field.echoMode() == QLineEdit.EchoMode.Password
            field.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
            action.setToolTip(S.AUTH_HIDE_PASSWORD if hidden else S.AUTH_SHOW_PASSWORD)
            action.setIcon(icons.icon("eye_off" if hidden else "eye", "icon", 18))

        action.triggered.connect(toggle)
        field.addAction(action, QLineEdit.ActionPosition.TrailingPosition)

    def _submit(self, button: QPushButton) -> None:
        if not button.isEnabled() or self._error is None or self._login is None or self._password is None:
            return
        login = self._login.text().strip()
        password = self._password.text()
        if not login or not password:
            self._error.setText(S.AUTH_ERROR_EMPTY)
            self._error.show()
            return

        self._error.hide()
        button.setEnabled(False)
        try:
            self.repo.login(login, password)
            authenticated = self.repo.is_authenticated
        except AnixartError as exc:
            self._error.setText(
                S.AUTH_ERROR_INVALID if exc.code in {2, 3}
                else "Не удалось войти. Попробуйте ещё раз позже."
            )
            self._error.show()
            return
        except Exception:
            self._error.setText("Не удалось войти. Проверьте логин, пароль и подключение к сети.")
            self._error.show()
            return
        finally:
            button.setEnabled(True)

        if not authenticated:
            self._error.setText(S.AUTH_ERROR_INVALID)
            self._error.show()
            return
        self._password.clear()
        self.open_route("home", push=False)


class RegistrationScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xl"), theme.space("xl"), theme.space("xl"), theme.space("xl"))
        layout.addStretch(1)
        card = AuthCard(width=520, parent=wrap)
        title = QLabel(S.AUTH_ALMOST_DONE, card)
        title.setProperty("role", "title")
        card.layout_box.addWidget(title)
        subtitle = QLabel(S.AUTH_SIGN_UP_WITH, card)
        subtitle.setProperty("role", "muted")
        card.layout_box.addWidget(subtitle)
        self._nick = QLineEdit(card)
        self._nick.setPlaceholderText(S.AUTH_NICK)
        self._nick.setMaxLength(20)
        card.layout_box.addWidget(self._nick)
        self._email = QLineEdit(card)
        self._email.setPlaceholderText(S.AUTH_EMAIL_FIELD)
        card.layout_box.addWidget(self._email)
        self._password = QLineEdit(card)
        self._password.setPlaceholderText(S.AUTH_PASSWORD)
        self._password.setMaxLength(32)
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        card.layout_box.addWidget(self._password)
        self._repeat = QLineEdit(card)
        self._repeat.setPlaceholderText(S.AUTH_PASSWORD_REPEAT)
        self._repeat.setEchoMode(QLineEdit.EchoMode.Password)
        card.layout_box.addWidget(self._repeat)
        self._consent_one = QCheckBox(card)
        consent_one_row = QHBoxLayout()
        consent_one_row.setSpacing(theme.space("sm"))
        consent_one_row.addWidget(self._consent_one, 0, Qt.AlignmentFlag.AlignTop)
        consent_one_text = ClickableLabel(S.AUTH_CONSENT_1, card)
        consent_one_text.setWordWrap(True)
        consent_one_text.setCursor(Qt.CursorShape.PointingHandCursor)
        consent_one_text.clicked.connect(self._consent_one.toggle)
        consent_one_row.addWidget(consent_one_text, 1)
        card.layout_box.addLayout(consent_one_row)
        self._consent_two = QCheckBox(card)
        consent_two_row = QHBoxLayout()
        consent_two_row.setSpacing(theme.space("sm"))
        consent_two_row.addWidget(self._consent_two, 0, Qt.AlignmentFlag.AlignTop)
        consent_two_text = ClickableLabel(S.AUTH_CONSENT_2, card)
        consent_two_text.setWordWrap(True)
        consent_two_text.setCursor(Qt.CursorShape.PointingHandCursor)
        consent_two_text.clicked.connect(self._consent_two.toggle)
        consent_two_row.addWidget(consent_two_text, 1)
        card.layout_box.addLayout(consent_two_row)
        self._error = QLabel("", card)
        self._error.setProperty("role", "danger")
        self._error.setWordWrap(True)
        self._error.hide()
        card.layout_box.addWidget(self._error)
        self._register = QPushButton(S.AUTH_CREATE_PROFILE, card)
        self._register.setProperty("ui", "primary")
        self._register.setEnabled(False)
        self._register.clicked.connect(self._submit)
        card.layout_box.addWidget(self._register)
        for field in (self._nick, self._email, self._password, self._repeat):
            field.textChanged.connect(self._update_enabled)
        self._consent_one.toggled.connect(self._update_enabled)
        self._consent_two.toggled.connect(self._update_enabled)
        login = QPushButton(S.AUTH_HAS_ACCOUNT + " " + S.AUTH_LOGIN, card)
        login.setProperty("ui", "text")
        login.clicked.connect(lambda: self.open_route("auth_email"))
        card.layout_box.addWidget(login)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _update_enabled(self) -> None:
        if not hasattr(self, "_register"):
            return
        filled = all(
            field.text().strip()
            for field in (self._nick, self._email, self._password, self._repeat)
        )
        self._register.setEnabled(filled and self._consent_one.isChecked() and self._consent_two.isChecked())

    def _submit(self) -> None:
        if len(self._nick.text().strip()) < 2:
            self._fail(S.AUTH_ERROR_NICK)
            return
        if "@" not in self._email.text() or "." not in self._email.text():
            self._fail(S.AUTH_ERROR_EMAIL)
            return
        if len(self._password.text()) < 6:
            self._fail(S.AUTH_ERROR_SHORT)
            return
        if self._password.text() != self._repeat.text():
            self._fail(S.AUTH_ERROR_EMPTY)
            return
        if not (self._consent_one.isChecked() and self._consent_two.isChecked()):
            self._fail(S.AUTH_ERROR_TERMS)
            return
        self.notify(S.AUTH_CREATE_PROFILE)
        self.open_route("home", push=False)

    def _fail(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()


class RestoreScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xl"), theme.space("xl"), theme.space("xl"), theme.space("xl"))
        layout.addStretch(1)
        card = AuthCard(parent=wrap)
        title = QLabel(S.AUTH_RESTORE_TITLE, card)
        title.setProperty("role", "title")
        card.layout_box.addWidget(title)
        subtitle = QLabel(S.AUTH_RESTORE_HINT, card)
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        card.layout_box.addWidget(subtitle)
        login = QLineEdit(card)
        login.setPlaceholderText(S.AUTH_EMAIL_OR_NICK)
        card.layout_box.addWidget(login)
        password = QLineEdit(card)
        password.setPlaceholderText(S.AUTH_PASSWORD)
        password.setEchoMode(QLineEdit.EchoMode.Password)
        card.layout_box.addWidget(password)
        repeat = QLineEdit(card)
        repeat.setPlaceholderText(S.AUTH_PASSWORD_REPEAT)
        repeat.setEchoMode(QLineEdit.EchoMode.Password)
        card.layout_box.addWidget(repeat)
        error = QLabel("", card)
        error.setProperty("role", "danger")
        error.hide()
        card.layout_box.addWidget(error)
        continue_button = QPushButton(S.AUTH_CONTINUE, card)
        continue_button.setProperty("ui", "primary")

        def submit() -> None:
            if not login.text().strip() or not password.text():
                error.setText(S.AUTH_ERROR_EMPTY)
                error.show()
                return
            if password.text() != repeat.text():
                error.setText(S.AUTH_ERROR_INVALID)
                error.show()
                return
            self.notify(S.AUTH_RESTORE_TITLE)
            self.open_route("auth_email")

        continue_button.clicked.connect(submit)
        card.layout_box.addWidget(continue_button)
        back = QPushButton(S.BACK, card)
        back.setProperty("ui", "text")
        back.clicked.connect(self.ctx.host.go_back)
        card.layout_box.addWidget(back)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)


class QrPlaceholder(QWidget):
    """Original pseudo-QR graphic (not a scannable code; no copied assets)."""

    def __init__(self, seed: int = 1, *, size: int = 240, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._seed = seed
        self._modules = 25
        self.setFixedSize(size, size)
        active_theme().changed.connect(self.update)

    def set_seed(self, seed: int) -> None:
        self._seed = seed
        self.update()

    def _finder(self, x: int, y: int) -> bool:
        return (x < 7 and y < 7) or (x >= self._modules - 7 and y < 7) or (x < 7 and y >= self._modules - 7)

    def paintEvent(self, _event) -> None:  # noqa: N802
        theme = active_theme()
        painter = QPainter(self)
        painter.fillRect(self.rect(), theme.qcolor("surface_secondary"))
        margin = 12
        cell = (self.width() - margin * 2) / self._modules
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.qcolor("text_primary"))
        for y in range(self._modules):
            for x in range(self._modules):
                if self._finder(x, y):
                    continue
                if (x * 31 + y * 17 + self._seed * 7 + x * y * 3) % 11 < 5:
                    painter.drawRect(QRectF(margin + x * cell, margin + y * cell, cell + 0.5, cell + 0.5))
        for ox, oy in ((0, 0), (self._modules - 7, 0), (0, self._modules - 7)):
            painter.setBrush(theme.qcolor("text_primary"))
            painter.drawRect(QRectF(margin + ox * cell, margin + oy * cell, cell * 7, cell * 7))
            painter.setBrush(theme.qcolor("surface_secondary"))
            painter.drawRect(QRectF(margin + (ox + 1) * cell, margin + (oy + 1) * cell, cell * 5, cell * 5))
            painter.setBrush(theme.qcolor("text_primary"))
            painter.drawRect(QRectF(margin + (ox + 2) * cell, margin + (oy + 2) * cell, cell * 3, cell * 3))


class QrAuthScreen(BaseScreen):
    auto_load = False
    supports_empty = False

    def __init__(self, ctx) -> None:
        super().__init__(ctx, title=S.AUTH_QR_FULL)
        self._seed = random.randint(1000, 9999)
        self._qr: QrPlaceholder | None = None
        self._code: QLabel | None = None

    def populate(self) -> None:
        self.reset_content()
        theme = active_theme()
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(theme.space("xl"), theme.space("xl"), theme.space("xl"), theme.space("xl"))
        layout.addStretch(1)
        card = AuthCard(width=520, parent=wrap)
        title = QLabel(S.AUTH_QR_FULL, card)
        title.setProperty("role", "title")
        card.layout_box.addWidget(title)
        hint = QLabel(S.AUTH_QR_SCAN, card)
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        card.layout_box.addWidget(hint)
        self._qr = QrPlaceholder(self._seed, parent=card)
        card.layout_box.addWidget(self._qr, 0, Qt.AlignmentFlag.AlignHCenter)
        self._code = QLabel(self._code_text(), card)
        self._code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_caption = QLabel(S.AUTH_QR_PIN, card)
        code_caption.setProperty("role", "muted")
        code_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout_box.addWidget(code_caption)
        card.layout_box.addWidget(self._code)
        status = QLabel(S.AUTH_QR_STATUS, card)
        status.setProperty("role", "tertiary")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout_box.addWidget(status)
        steps = QLabel(
            f"1. {S.AUTH_QR_SCAN}\n2. {S.AUTH_QR_OPEN}\n3. {S.AUTH_QR_PIN}",
            card,
        )
        steps.setProperty("role", "muted")
        steps.setWordWrap(True)
        card.layout_box.addWidget(steps)
        actions = QHBoxLayout()
        refresh = QPushButton(S.AUTH_QR_REFRESH, card)
        refresh.setProperty("ui", "outlined")
        refresh.clicked.connect(self._refresh)
        actions.addWidget(refresh)
        other = QPushButton(S.AUTH_QR_OTHER, card)
        other.setProperty("ui", "text")
        other.clicked.connect(lambda: self.open_route("auth"))
        actions.addWidget(other)
        actions.addStretch(1)
        card.layout_box.addLayout(actions)
        confirm = QPushButton(S.AUTH_QR_ALLOW, card)
        confirm.setProperty("ui", "primary")
        confirm.clicked.connect(self._confirm)
        card.layout_box.addWidget(confirm)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        self.add_content(wrap, 1)

    def _code_text(self) -> str:
        digits = f"{self._seed:04d}"
        return f"{S.AUTH_QR_CODE}: {' '.join(digits)}"

    def _refresh(self) -> None:
        self._seed = random.randint(1000, 9999)
        if self._qr is not None:
            self._qr.set_seed(self._seed)
        if self._code is not None:
            self._code.setText(self._code_text())
        self.notify(S.AUTH_QR_REFRESH)

    def _confirm(self) -> None:
        dialog = QrConfirmDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notify(S.AUTH_QR_CONFIRMED)
            self.open_route("home", push=False)
        else:
            self.notify(S.AUTH_QR_DECLINED)
