"""Shared UI components.

The original repeated the same label/entry/message construction in all five
screens, each with its own copy of the show/hide-password logic and its own
"add_message / remove_message / buttons_arrangement_with_message" trio. These
widgets exist once.
"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..passwords import estimate_strength


class Card(QFrame):
    """Rounded surface used as the main container on every screen."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(32, 28, 32, 28)
        self.body.setSpacing(16)


class Heading(QWidget):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("Title")
        layout.addWidget(label)

        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("Subtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setVisible(bool(subtitle))
        layout.addWidget(self._subtitle)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        self._subtitle.setVisible(bool(text))


class PasswordField(QWidget):
    """Password entry with a reveal toggle and optional strength meter."""

    textChanged = pyqtSignal(str)
    returnPressed = pyqtSignal()

    def __init__(self, placeholder: str = "", *, show_strength: bool = False) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self._on_text_changed)
        self.edit.returnPressed.connect(self.returnPressed.emit)
        row.addWidget(self.edit, 1)

        self._toggle = QPushButton("Show")
        self._toggle.setObjectName("Ghost")
        self._toggle.setCheckable(True)
        self._toggle.setFixedWidth(74)
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.toggled.connect(self._on_toggled)
        row.addWidget(self._toggle)

        outer.addLayout(row)

        self._show_strength = show_strength
        self._meter = QProgressBar()
        self._meter.setRange(0, 100)
        self._meter.setTextVisible(False)
        self._meter.setVisible(False)
        self._label = QLabel("")
        self._label.setObjectName("FieldLabel")
        self._label.setVisible(False)
        if show_strength:
            outer.addWidget(self._meter)
            outer.addWidget(self._label)

    def text(self) -> str:
        return self.edit.text()

    def setText(self, value: str) -> None:  # noqa: N802 - matches Qt naming
        self.edit.setText(value)

    def clear(self) -> None:
        self.edit.clear()

    def _on_toggled(self, shown: bool) -> None:
        self.edit.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)
        self._toggle.setText("Hide" if shown else "Show")

    def _on_text_changed(self, value: str) -> None:
        if self._show_strength:
            strength = estimate_strength(value)
            self._meter.setVisible(bool(value))
            self._label.setVisible(bool(value))
            self._meter.setValue(int(strength.fraction * 100))
            self._meter.setObjectName(
                {"weak": "Weak", "fair": "Fair"}.get(strength.label, "Strong")
            )
            # Re-polish so the objectName-based chunk colour actually applies.
            self._meter.style().unpolish(self._meter)
            self._meter.style().polish(self._meter)
            self._label.setText(
                f"{strength.label.title()} - about {strength.bits:.0f} bits of entropy"
            )
        self.textChanged.emit(value)


class StatusLine(QLabel):
    """One place for success and error text.

    Replaces the original's per-screen add_message/remove_message pair plus the
    two icon QLabels that were shown and hidden by hand.
    """

    def __init__(self) -> None:
        super().__init__("")
        self.setWordWrap(True)
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _set(self, text: str, kind: str) -> None:
        self.setText(text)
        self.setObjectName(kind)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(bool(text))

    def success(self, text: str) -> None:
        self._set(f"✓  {text}", "Success")

    def error(self, text: str) -> None:
        self._set(f"✕  {text}", "Danger")

    def info(self, text: str) -> None:
        self._set(text, "Subtitle")

    def busy(self, text: str) -> None:
        self._set(f"⋯  {text}", "Warning")

    def clear_message(self) -> None:
        self.setText("")
        self.setVisible(False)


class CameraView(QLabel):
    """Live preview surface with a framing guide."""

    def __init__(self, width: int = 480, height: int = 360) -> None:
        super().__init__()
        self.setObjectName("CameraFrame")
        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Camera off")

    def show_frame(self, image: QImage) -> None:
        self.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def show_placeholder(self, text: str) -> None:
        self.setPixmap(QPixmap())
        self.setText(text)


def primary_button(text: str, handler: Callable[[], None]) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Primary")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(handler)
    return button


def confirm_button(text: str, handler: Callable[[], None]) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Confirm")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(handler)
    return button


def ghost_button(text: str, handler: Callable[[], None]) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Ghost")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(handler)
    return button


def link_button(text: str, handler: Callable[[], None]) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Link")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(handler)
    return button


def labelled(text: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    layout.addWidget(label)
    layout.addWidget(widget)
    return container


def checkbox(text: str, *, checked: bool = True) -> QCheckBox:
    box = QCheckBox(text)
    box.setChecked(checked)
    box.setCursor(Qt.CursorShape.PointingHandCursor)
    return box
