"""Signed-in session state.

The 2022 client tracked the logged-in user in a module-level global
(``USER_EMAIL``) alongside three ``shared_*`` globals used to pass values
between screens. State lives in one object here, and the long-lived refresh
token goes to the OS credential store rather than a variable or a file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "fzip-locker"


@dataclass
class Session:
    """Current authentication state.

    ``access_token`` deliberately stays in memory only - it lives 15 minutes,
    so persisting it would add exposure for no practical gain.
    """

    user_id: str = ""
    email: str = ""
    access_token: str = ""
    _refresh_token: str = field(default="", repr=False)
    #: Set after a successful face verification; consumed by the vault screen.
    face_token: str = field(default="", repr=False)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token and self.user_id)

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    def adopt(self, tokens: dict[str, str | int]) -> None:
        """Take the tokens from a login/register/refresh response."""
        self.user_id = str(tokens["user_id"])
        self.access_token = str(tokens["access_token"])
        self._refresh_token = str(tokens["refresh_token"])
        self._persist_refresh_token()

    def clear(self) -> None:
        self.user_id = ""
        self.email = ""
        self.access_token = ""
        self._refresh_token = ""
        self.face_token = ""
        self._forget_refresh_token()

    # -- keyring ----------------------------------------------------------
    # Every keyring call is guarded: on a headless Linux box with no secret
    # service, keyring raises. That should degrade to "you have to sign in
    # again next launch", never crash the app.
    def _persist_refresh_token(self) -> None:
        if not self.email:
            return
        try:
            keyring.set_password(SERVICE_NAME, self.email, self._refresh_token)
        except KeyringError:
            pass

    def _forget_refresh_token(self) -> None:
        if not self.email:
            return
        try:
            keyring.delete_password(SERVICE_NAME, self.email)
        except KeyringError:
            pass

    @staticmethod
    def stored_refresh_token(email: str) -> str:
        try:
            return keyring.get_password(SERVICE_NAME, email) or ""
        except KeyringError:
            return ""

    @staticmethod
    def remembered_email() -> str:
        from .config import state_dir

        path = state_dir() / "last-email"
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""

    @staticmethod
    def remember_email(email: str) -> None:
        from .config import state_dir

        # Only the address, never the password or token - this file is plain
        # text and exists purely to pre-fill the sign-in field.
        (state_dir() / "last-email").write_text(email, encoding="utf-8")
