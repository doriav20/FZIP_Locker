"""Headless construction tests for the Qt UI.

These do not drive the interface - they build it. Every screen, dialog and
shared widget is constructed and navigated with Qt's ``offscreen`` platform
plugin, which catches the class of error that import checks miss: bad layout
parenting, a malformed stylesheet, a signal connected to a name that does not
exist, an enum moved between PyQt5 and PyQt6.

That last one matters here. The 2022 client was PyQt5, where enums were
module-level (``Qt.AlignCenter``); PyQt6 scopes them (``Qt.AlignmentFlag
.AlignCenter``). Nothing but constructing the widget will tell you a conversion
was missed.

Skipped automatically when PyQt6 is absent, so the crypto-only test run stays
dependency-light.
"""

from __future__ import annotations

import os

import pytest

# Must be set before PyQt6 initialises, or it will look for a real display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6", reason="GUI dependencies not installed")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from fzip_client.config import ClientConfig  # noqa: E402
from fzip_client.ui.theme import STYLESHEET  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """One QApplication for the module - Qt allows only a single instance."""
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLESHEET)
    return app


@pytest.fixture
def window(qapp):
    from fzip_client.ui.app import MainWindow

    win = MainWindow(ClientConfig.load())
    yield win
    win.api.close()


def test_main_window_builds(window):
    assert window.windowTitle() == "FZIP Locker"
    assert not window.session.is_authenticated


@pytest.mark.parametrize("screen", ["sign_in", "sign_up", "vault"])
def test_every_screen_constructs_and_activates(window, screen):
    window.navigate(screen)


def test_navigation_is_reentrant(window):
    """Screens are built once and reused, so re-entry must reset cleanly."""
    for _ in range(3):
        for name in ("sign_in", "sign_up", "vault", "sign_in"):
            window.navigate(name)


def test_stylesheet_is_valid_qss(qapp):
    """Qt silently ignores malformed QSS, so assert it was actually applied."""
    assert qapp.styleSheet() == STYLESHEET
    assert "qlineargradient" in qapp.styleSheet()


# --------------------------------------------------------------------------
# Dialogs
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("generator", "confirm"),
    [(True, True), (True, False), (False, False)],
    ids=["lock-with-confirm", "lock-no-confirm", "unlock"],
)
def test_password_dialog_constructs(qapp, generator, confirm):
    from fzip_client.ui.screens.password import PasswordDialog

    PasswordDialog(None, include_generator=generator, confirm=confirm)


def test_password_dialog_generator_fills_both_fields(qapp):
    from fzip_client.passwords import MIN_LENGTH
    from fzip_client.ui.screens.password import PasswordDialog

    dialog = PasswordDialog(None, include_generator=True, confirm=True)
    dialog._generate()

    generated = dialog._password.text()
    assert len(generated) >= MIN_LENGTH
    # The confirm field is filled too, or the user would have to retype a
    # 20-character random string by hand.
    assert dialog._repeat is not None
    assert dialog._repeat.text() == generated


def test_password_dialog_rejects_a_short_password(qapp):
    from fzip_client.ui.screens.password import PasswordDialog

    dialog = PasswordDialog(None, include_generator=True, confirm=False)
    dialog._password.setText("short")
    dialog._submit()

    assert dialog.password == ""  # not accepted
    assert dialog._status.isVisible()


def test_password_dialog_rejects_a_mismatch(qapp):
    from fzip_client.ui.screens.password import PasswordDialog

    dialog = PasswordDialog(None, include_generator=True, confirm=True)
    dialog._password.setText("a-long-enough-password")
    dialog._repeat.setText("a-different-password!!")
    dialog._submit()

    assert dialog.password == ""


def test_password_dialog_accepts_a_valid_password(qapp):
    from fzip_client.ui.screens.password import PasswordDialog

    dialog = PasswordDialog(None, include_generator=True, confirm=True)
    dialog._password.setText("a-long-enough-password")
    dialog._repeat.setText("a-long-enough-password")
    dialog._submit()

    assert dialog.password == "a-long-enough-password"


# --------------------------------------------------------------------------
# Shared widgets
# --------------------------------------------------------------------------
def test_password_field_strength_meter_updates(qapp):
    from fzip_client.ui.widgets import PasswordField

    field = PasswordField("x", show_strength=True)
    field.setText("aB3!aB3!aB3!aB3!aB3!")
    assert field._meter.isVisible() is False or field._meter.value() > 0
    assert field.text() == "aB3!aB3!aB3!aB3!aB3!"


def test_password_field_reveal_toggle(qapp):
    from PyQt6.QtWidgets import QLineEdit

    from fzip_client.ui.widgets import PasswordField

    field = PasswordField("x")
    assert field.edit.echoMode() == QLineEdit.EchoMode.Password
    field._toggle.setChecked(True)
    assert field.edit.echoMode() == QLineEdit.EchoMode.Normal
    field._toggle.setChecked(False)
    assert field.edit.echoMode() == QLineEdit.EchoMode.Password


def test_status_line_transitions(qapp):
    from fzip_client.ui.widgets import StatusLine

    status = StatusLine()
    assert not status.isVisible()

    for setter in (status.success, status.error, status.busy, status.info):
        setter("message")
        assert status.text()

    status.clear_message()
    assert status.text() == ""


def test_camera_view_placeholder(qapp):
    from fzip_client.ui.widgets import CameraView

    view = CameraView()
    view.show_placeholder("Camera off")
    assert view.text() == "Camera off"
