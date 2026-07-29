"""Main screen: lock a selection into a `.lck`, or unlock one.

Mirrors the original CompressScreen, including the order of the unlock flow
(choose file, then face, then password). What changed is where the work runs:
archiving and Argon2id key derivation happen on a worker thread, so the window
stays responsive on large archives instead of appearing hung.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ... import operations
from ...errors import ApiError, AuthRequiredError, OwnershipError, VaultError
from ..widgets import (
    Card,
    Heading,
    StatusLine,
    confirm_button,
    ghost_button,
    link_button,
    primary_button,
)
from ..workers import run_async
from .face_scan import VerificationCaptureDialog
from .password import PasswordDialog

if TYPE_CHECKING:
    from ..app import MainWindow


def _human_bytes(count: int) -> str:
    size = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class VaultScreen(QWidget):
    def __init__(self, controller: MainWindow) -> None:
        super().__init__()
        self._controller = controller

        outer = QVBoxLayout(self)
        outer.setContentsMargins(64, 32, 64, 32)
        outer.setSpacing(16)

        header = QHBoxLayout()
        self._who = QLabel("")
        self._who.setObjectName("Subtitle")
        header.addWidget(self._who)
        header.addStretch(1)
        header.addWidget(link_button("Sign out", self._logout))
        outer.addLayout(header)

        outer.addStretch(1)

        card = Card()
        outer.addWidget(card)
        outer.addStretch(1)

        card.body.addWidget(
            Heading(
                "Your locker",
                "Files are compressed and encrypted on this machine. The server "
                "never receives them, and never receives the archive password.",
            )
        )

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self._lock_button = primary_button("Lock files...", self._start_lock)
        self._lock_folder_button = ghost_button("Lock a folder...", self._start_lock_folder)
        self._unlock_button = confirm_button("Unlock a .lck...", self._start_unlock)
        for button in (self._lock_button, self._lock_folder_button, self._unlock_button):
            actions.addWidget(button)
        card.body.addLayout(actions)

        self._status = StatusLine()
        card.body.addWidget(self._status)

        note = QLabel(
            "Unlocking requires your face as well as the archive password. "
            "Locking does not - so you can always lock files, even offline."
        )
        note.setObjectName("Subtitle")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card.body.addWidget(note)

    # ------------------------------------------------------------------
    def on_enter(self) -> None:
        session = self._controller.session
        self._who.setText(f"Signed in as {session.email}")
        self._status.clear_message()
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        for button in (self._lock_button, self._lock_folder_button, self._unlock_button):
            button.setEnabled(not busy)

    def _logout(self) -> None:
        api = self._controller.api
        run_async(api.logout, lambda _: self._controller.navigate("sign_in"),
                  lambda *_: self._controller.navigate("sign_in"))

    # ------------------------------------------------------------------
    # Lock
    # ------------------------------------------------------------------
    def _start_lock(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files to lock")
        if paths:
            self._lock([Path(p) for p in paths])

    def _start_lock_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select a folder to lock")
        if folder:
            self._lock([Path(folder)])

    def _lock(self, sources: list[Path]) -> None:
        suggested = str(sources[0].with_suffix(".lck"))
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save locked archive as", suggested, "Locked archives (*.lck)"
        )
        if not destination:
            return

        password = PasswordDialog.ask(self, include_generator=True, confirm=True)
        if password is None:
            self._status.info("Locking cancelled.")
            return

        self._set_busy(True)
        self._status.busy("Compressing and encrypting...")
        owner = self._controller.session.user_id
        target = Path(destination)

        run_async(
            lambda: operations.lock(sources, target, password, owner=owner),
            self._on_locked,
            self._on_failed,
        )

    def _on_locked(self, result: operations.LockResult) -> None:
        self._set_busy(False)
        self._status.success(
            f"Locked {result.file_count} file(s) into {result.destination.name} "
            f"({_human_bytes(result.locked_bytes)})."
        )

    # ------------------------------------------------------------------
    # Unlock
    # ------------------------------------------------------------------
    def _start_unlock(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a locked archive", "", "Locked archives (*.lck)"
        )
        if not path:
            return

        source = Path(path)

        # Read the header first: an unreadable or foreign file should be caught
        # before we make the user perform a face scan for nothing.
        try:
            header = operations.peek(source)
        except VaultError as exc:
            self._status.error(exc.user_message)
            return

        owner = self._controller.session.user_id
        if header.owner and header.owner != owner:
            self._status.error(
                "This archive belongs to a different account. Only its owner's "
                "password can open it."
            )
            return

        self._request_face_challenge(source)

    def _request_face_challenge(self, source: Path) -> None:
        self._set_busy(True)
        self._status.busy("Requesting a face challenge...")
        api = self._controller.api

        run_async(
            api.face_challenge,
            lambda challenge: self._run_face_capture(source, challenge),
            self._on_failed,
        )

    def _run_face_capture(self, source: Path, challenge: dict[str, Any]) -> None:
        self._status.clear_message()
        dialog = VerificationCaptureDialog(
            direction=str(challenge["direction"]),
            frames_required=int(challenge["frames_required"]),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._set_busy(False)
            self._status.info("Face verification cancelled.")
            return

        self._status.busy("Verifying your face...")
        api = self._controller.api
        nonce = str(challenge["nonce"])
        frames = list(dialog.frames)

        run_async(
            lambda: api.face_verify(nonce, frames),
            lambda _: self._ask_unlock_password(source),
            self._on_face_failed,
        )

    def _ask_unlock_password(self, source: Path) -> None:
        self._status.success("Face verified.")
        password = PasswordDialog.ask(self, include_generator=False)
        if password is None:
            self._set_busy(False)
            self._status.info("Unlocking cancelled.")
            return

        self._status.busy("Decrypting and extracting...")
        owner = self._controller.session.user_id

        run_async(
            lambda: operations.unlock(source, password, owner=owner),
            self._on_unlocked,
            self._on_failed,
        )

    def _on_unlocked(self, result: operations.UnlockResult) -> None:
        self._set_busy(False)
        self._status.success(
            f"Extracted {result.file_count} file(s) to {result.destination.name}."
        )

    # ------------------------------------------------------------------
    def _on_face_failed(self, message: str, exc: Exception) -> None:
        self._set_busy(False)
        if isinstance(exc, ApiError) and exc.type_slug == "liveness-failed":
            self._status.error(
                "The head movement was not detected. Start facing the camera, "
                "then turn slowly and hold."
            )
            return
        if isinstance(exc, ApiError) and exc.type_slug == "challenge-invalid":
            self._status.error("That challenge expired. Try unlocking again.")
            return
        self._on_failed(message, exc)

    def _on_failed(self, message: str, exc: Exception) -> None:
        self._set_busy(False)
        if isinstance(exc, AuthRequiredError):
            self._controller.navigate("sign_in")
            return
        if isinstance(exc, OwnershipError):
            self._status.error("This archive belongs to a different account.")
            return
        self._status.error(message)
