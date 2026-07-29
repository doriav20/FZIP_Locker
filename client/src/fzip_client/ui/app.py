"""Main window and navigation.

The 2022 client navigated by constructing a brand-new ``QMainWindow`` for each
screen and closing the previous one, passing state between them through module
level globals. One window with a ``QStackedWidget`` replaces both mechanisms:
screens are created once, and shared state lives on this controller.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from ..api import FzipApi, ca_bundle_hint
from ..config import ClientConfig
from ..session import Session
from .screens.sign_in import SignInScreen
from .screens.sign_up import SignUpScreen
from .screens.vault import VaultScreen
from .theme import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, config: ClientConfig) -> None:
        super().__init__()
        self.setWindowTitle("FZIP Locker")
        # Resizable, unlike the original's fixed 960x540 with matching minimum
        # and maximum sizes.
        self.setMinimumSize(QSize(860, 620))
        self.resize(1000, 700)

        self.config = config
        self.session = Session()
        self.api = FzipApi(config, self.session)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._screens: dict[str, QWidget] = {
            "sign_in": SignInScreen(self),
            "sign_up": SignUpScreen(self),
            "vault": VaultScreen(self),
        }
        for screen in self._screens.values():
            self._stack.addWidget(screen)

        self.navigate("sign_in")

        hint = ca_bundle_hint(config)
        if hint:
            screen = self._screens["sign_in"]
            status = getattr(screen, "_status", None)
            if status is not None:
                status.info(hint)

    def navigate(self, name: str) -> None:
        screen = self._screens[name]
        self._stack.setCurrentWidget(screen)
        # Screens reset their own transient state on entry, so returning to
        # sign-in never leaves a stale password in a field.
        on_enter = getattr(screen, "on_enter", None)
        if callable(on_enter):
            on_enter()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.api.close()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FZIP Locker")
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(ClientConfig.load())
    window.show()
    return app.exec()
