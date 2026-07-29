"""Archive password dialog.

Corresponds to the original's PasswordScreen. The generator is kept, now
backed by :mod:`secrets` with an entropy meter, and the dialog carries an
explicit warning that this password cannot be recovered -- which is a direct
consequence of the zero-knowledge design and something the user genuinely
needs told.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...passwords import MIN_LENGTH, generate_password, is_valid_password
from ..widgets import (
    Heading,
    PasswordField,
    StatusLine,
    checkbox,
    ghost_button,
    labelled,
    primary_button,
)


class PasswordDialog(QDialog):
    """Collect an archive password, optionally offering to generate one."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        include_generator: bool,
        confirm: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Archive password")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._include_generator = include_generator
        self._confirm = confirm
        self.password = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        outer.addWidget(
            Heading(
                "Archive password" if include_generator else "Unlock archive",
                "This password encrypts the archive itself. It is never sent to "
                "the server, so nobody - including the server - can recover it "
                "for you."
                if include_generator
                else "Enter the password this archive was locked with.",
            )
        )

        self._password = PasswordField(
            "Archive password", show_strength=include_generator
        )
        self._password.returnPressed.connect(self._submit)
        outer.addWidget(labelled("Password", self._password))

        self._repeat: PasswordField | None = None
        if confirm:
            self._repeat = PasswordField("Repeat password")
            self._repeat.returnPressed.connect(self._submit)
            outer.addWidget(labelled("Confirm password", self._repeat))

        if include_generator:
            outer.addWidget(self._build_generator())

        self._status = StatusLine()
        outer.addWidget(self._status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(ghost_button("Cancel", self.reject))
        self._submit_button = primary_button(
            "Continue" if include_generator else "Unlock", self._submit
        )
        buttons.addWidget(self._submit_button)
        outer.addLayout(buttons)

    # -- generator ---------------------------------------------------------
    def _build_generator(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        header = QLabel("Or generate one")
        header.setObjectName("FieldLabel")
        layout.addWidget(header)

        options = QHBoxLayout()
        self._uppercase = checkbox("A-Z")
        self._numbers = checkbox("2-9")
        self._symbols = checkbox("!@#")
        for box in (self._uppercase, self._numbers, self._symbols):
            options.addWidget(box)
        options.addStretch(1)
        options.addWidget(ghost_button("Generate", self._generate))
        self._copy_button = ghost_button("Copy", self._copy)
        self._copy_button.setEnabled(False)
        options.addWidget(self._copy_button)
        layout.addLayout(options)

        note = QLabel(
            "Ambiguous characters (0 O o 1 I l) are excluded so a generated "
            "password can be read off the screen reliably."
        )
        note.setObjectName("Subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

    def _generate(self) -> None:
        value = generate_password(
            include_uppercase=self._uppercase.isChecked(),
            include_numbers=self._numbers.isChecked(),
            include_symbols=self._symbols.isChecked(),
        )
        self._password.setText(value)
        if self._repeat is not None:
            self._repeat.setText(value)
        # Reveal it: a generated password the user cannot see is a password
        # they cannot write down, and they will need it to ever open the file.
        self._password.edit.setEchoMode(self._password.edit.EchoMode.Normal)
        self._copy_button.setEnabled(True)
        self._status.info("Generated. Save it somewhere safe before continuing.")

    def _copy(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._password.text())
            self._status.success("Copied to clipboard.")

    # -- submit ------------------------------------------------------------
    def _submit(self) -> None:
        value = self._password.text()

        if self._include_generator and not is_valid_password(value):
            self._status.error(
                f"Use at least {MIN_LENGTH} characters. Short passwords are the "
                "weakest part of any encryption scheme."
            )
            return
        if not value:
            self._status.error("Enter the archive password.")
            return
        if self._repeat is not None and value != self._repeat.text():
            self._status.error("The two passwords do not match.")
            return

        self.password = value
        self.accept()

    @classmethod
    def ask(
        cls,
        parent: QWidget | None,
        *,
        include_generator: bool,
        confirm: bool = False,
    ) -> str | None:
        """Show the dialog, returning the password or None if cancelled."""
        dialog = cls(parent, include_generator=include_generator, confirm=confirm)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.password
        return None
