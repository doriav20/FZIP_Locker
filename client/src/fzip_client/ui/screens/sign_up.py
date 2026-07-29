"""Registration screen: account details plus face enrolment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ...errors import ApiError
from ...passwords import MIN_LENGTH, is_valid_email, is_valid_password
from ...session import Session
from ..widgets import (
    Card,
    Heading,
    PasswordField,
    StatusLine,
    ghost_button,
    labelled,
    link_button,
    primary_button,
)
from ..workers import run_async
from .face_scan import ENROLMENT_CAPTURES, EnrolmentCaptureDialog

if TYPE_CHECKING:
    from ..app import MainWindow


class SignUpScreen(QWidget):
    def __init__(self, controller: MainWindow) -> None:
        super().__init__()
        self._controller = controller
        self._frames: list[bytes] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(80, 40, 80, 40)
        outer.addStretch(1)

        card = Card()
        outer.addWidget(card)
        outer.addStretch(1)

        card.body.addWidget(
            Heading(
                "Create your account",
                "Your account password protects sign-in. Each archive gets its "
                "own separate password, which never leaves your machine.",
            )
        )

        self._email = QLineEdit()
        self._email.setPlaceholderText("you@example.com")
        card.body.addWidget(labelled("Email", self._email))

        self._password = PasswordField(f"At least {MIN_LENGTH} characters", show_strength=True)
        card.body.addWidget(labelled("Account password", self._password))

        self._repeat = PasswordField("Repeat your password")
        card.body.addWidget(labelled("Confirm password", self._repeat))

        self._scan_button = ghost_button(
            f"Scan my face ({ENROLMENT_CAPTURES} captures)", self._scan
        )
        card.body.addWidget(self._scan_button)

        self._status = StatusLine()
        card.body.addWidget(self._status)

        self._register = primary_button("Create account", self._submit)
        card.body.addWidget(self._register)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(link_button("Back to sign in", lambda: controller.navigate("sign_in")))
        footer.addStretch(1)
        card.body.addLayout(footer)

    def on_enter(self) -> None:
        self._frames.clear()
        self._password.clear()
        self._repeat.clear()
        self._status.clear_message()
        self._scan_button.setText(f"Scan my face ({ENROLMENT_CAPTURES} captures)")
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        for widget in (self._email, self._password, self._repeat, self._scan_button):
            widget.setEnabled(not busy)
        self._register.setEnabled(not busy)

    def _scan(self) -> None:
        dialog = EnrolmentCaptureDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._status.info("Face scan cancelled.")
            return

        self._frames = dialog.frames
        self._scan_button.setText(f"Face scanned ({len(self._frames)} captures) - rescan")
        self._status.success("Face captured. You can create your account now.")

    def _submit(self) -> None:
        email = self._email.text().strip().lower()
        password = self._password.text()

        if not is_valid_email(email):
            self._status.error("That does not look like an email address.")
            return
        if not is_valid_password(password):
            self._status.error(f"Your password needs at least {MIN_LENGTH} characters.")
            return
        if password != self._repeat.text():
            self._status.error("The two passwords do not match.")
            return
        if len(self._frames) != ENROLMENT_CAPTURES:
            self._status.error("Scan your face before creating the account.")
            return

        self._set_busy(True)
        self._status.busy("Creating your account...")
        api = self._controller.api
        frames = list(self._frames)

        run_async(
            lambda: api.register(email, password, frames),
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
        if isinstance(exc, ApiError) and exc.type_slug == "email-already-registered":
            self._status.error("An account already exists for that email address.")
            return
        if isinstance(exc, ApiError) and exc.type_slug in {
            "no-face-detected",
            "multiple-faces",
            "face-mismatch",
        }:
            # Enrolment is the one place a face failure is recoverable in place,
            # so drop the captures and let them retry without losing the form.
            self._frames.clear()
            self._scan_button.setText(f"Scan my face ({ENROLMENT_CAPTURES} captures)")
            self._status.error(f"{message} Please scan again.")
            return
        self._status.error(message)
