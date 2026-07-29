"""Sign-in screen."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ...errors import ApiError
from ...passwords import is_valid_email
from ...session import Session
from ..widgets import (
    Card,
    Heading,
    PasswordField,
    StatusLine,
    labelled,
    link_button,
    primary_button,
)
from ..workers import run_async

if TYPE_CHECKING:
    from ..app import MainWindow


class SignInScreen(QWidget):
    def __init__(self, controller: MainWindow) -> None:
        super().__init__()
        self._controller = controller

        outer = QVBoxLayout(self)
        outer.setContentsMargins(80, 48, 80, 48)
        outer.addStretch(1)

        card = Card()
        outer.addWidget(card)
        outer.addStretch(1)

        card.body.addWidget(
            Heading(
                "FZIP Locker",
                "Sign in to lock and unlock your archives.",
            )
        )

        self._email = QLineEdit()
        self._email.setPlaceholderText("you@example.com")
        self._email.returnPressed.connect(self._submit)
        card.body.addWidget(labelled("Email", self._email))

        self._password = PasswordField("Your account password")
        self._password.returnPressed.connect(self._submit)
        card.body.addWidget(labelled("Password", self._password))

        self._status = StatusLine()
        card.body.addWidget(self._status)

        self._sign_in = primary_button("Sign in", self._submit)
        card.body.addWidget(self._sign_in)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(
            link_button("Create an account", lambda: controller.navigate("sign_up"))
        )
        footer.addStretch(1)
        card.body.addLayout(footer)

        remembered = Session.remembered_email()
        if remembered:
            self._email.setText(remembered)
            self._password.edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def on_enter(self) -> None:
        self._password.clear()
        self._status.clear_message()
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self._sign_in.setEnabled(not busy)
        self._email.setEnabled(not busy)
        self._password.setEnabled(not busy)

    def _submit(self) -> None:
        email = self._email.text().strip().lower()
        password = self._password.text()

        if not is_valid_email(email):
            self._status.error("That does not look like an email address.")
            return
        if not password:
            self._status.error("Enter your password.")
            return

        self._set_busy(True)
        self._status.busy("Signing in...")
        api = self._controller.api

        run_async(
            lambda: api.login(email, password),
            self._on_success,
            self._on_error,
        )

    def _on_success(self, _: Any) -> None:
        self._set_busy(False)
        self._status.clear_message()
        Session.remember_email(self._controller.session.email)
        self._controller.navigate("vault")

    def _on_error(self, message: str, exc: Exception) -> None:
        self._set_busy(False)
        if isinstance(exc, ApiError) and exc.type_slug == "account-locked":
            self._status.error(
                "Too many failed attempts. Wait a few minutes before trying again."
            )
            return
        self._status.error(message)
