"""Camera capture dialogs for enrolment and verification.

Replaces the original FaceScanningScreen. Structural differences:

* The preview is embedded and live. The original ran a blocking OpenCV loop
  that opened its own OS window, froze the app, then showed a still afterwards.
* Verification captures a short burst while prompting a head movement the
  server asked for, so a single captured frame is not a reusable credential.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...camera import CameraThread, encode_jpeg, to_qimage
from ..widgets import (
    CameraView,
    Heading,
    StatusLine,
    confirm_button,
    ghost_button,
    primary_button,
)

ENROLMENT_CAPTURES = 3

#: Milliseconds between burst frames. Roughly 2.4 s for a 5-frame burst, which
#: is long enough for an unhurried head turn without feeling sluggish.
BURST_INTERVAL_MS = 600


class _CameraDialog(QDialog):
    """Shared camera lifecycle for both capture flows."""

    def __init__(self, parent: QWidget | None, title: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.frames: list[bytes] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(14)

        self.view = CameraView()
        self.status = StatusLine()

        self._camera = CameraThread()
        self._camera.frame_ready.connect(self._on_frame)
        self._camera.failed.connect(self._on_camera_failed)

    def start_camera(self) -> None:
        self.view.show_placeholder("Starting camera...")
        self._camera.start()

    def _on_frame(self, image: QImage) -> None:
        self.view.show_frame(image)

    def _on_camera_failed(self, message: str) -> None:
        self.view.show_placeholder("Camera unavailable")
        self.status.error(message)
        self._set_capture_enabled(False)

    def _set_capture_enabled(self, enabled: bool) -> None:  # overridden
        pass

    def current_frame_jpeg(self) -> bytes | None:
        frame = self._camera.latest_frame
        return None if frame is None else encode_jpeg(frame)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._camera.stop()
        super().closeEvent(event)

    def reject(self) -> None:
        self._camera.stop()
        super().reject()

    def accept(self) -> None:
        self._camera.stop()
        super().accept()


class EnrolmentCaptureDialog(_CameraDialog):
    """Capture three confirmed stills for enrolment."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, "Scan your face")

        self._heading = Heading(
            "Scan your face",
            "Three captures, so lighting and angle variation does not lock you "
            "out later. Face the camera directly and stay in good light.",
        )
        self._layout.addWidget(self._heading)

        centred = QHBoxLayout()
        centred.addStretch(1)
        centred.addWidget(self.view)
        centred.addStretch(1)
        self._layout.addLayout(centred)

        self._progress = QLabel("")
        self._progress.setObjectName("FieldLabel")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._progress)
        self._layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._cancel = ghost_button("Cancel", self.reject)
        buttons.addWidget(self._cancel)
        self._capture = primary_button("Capture", self._on_capture)
        buttons.addWidget(self._capture)
        self._layout.addLayout(buttons)

        self._update_progress()
        self.start_camera()

    def _set_capture_enabled(self, enabled: bool) -> None:
        self._capture.setEnabled(enabled)

    def _update_progress(self) -> None:
        remaining = ENROLMENT_CAPTURES - len(self.frames)
        self._progress.setText(
            f"{len(self.frames)} of {ENROLMENT_CAPTURES} captured - "
            f"{remaining} remaining"
        )

    def _on_capture(self) -> None:
        jpeg = self.current_frame_jpeg()
        if jpeg is None:
            self.status.error("No frame available yet. Give the camera a moment.")
            return

        self.frames.append(jpeg)
        self._update_progress()

        if len(self.frames) >= ENROLMENT_CAPTURES:
            self.status.success("All three captures taken.")
            self.accept()
        else:
            self.status.info("Captured. Shift your position slightly, then capture again.")


class VerificationCaptureDialog(_CameraDialog):
    """Capture a burst that demonstrates the server-requested head movement."""

    def __init__(
        self,
        direction: str,
        frames_required: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, "Verify your face")
        self._direction = direction
        self._required = frames_required
        self._timer = QTimer(self)
        self._timer.setInterval(BURST_INTERVAL_MS)
        self._timer.timeout.connect(self._grab)

        self._layout.addWidget(
            Heading(
                "Verify your face",
                f"Look at the camera, then slowly turn your head to your "
                f"{direction} and hold. The movement proves a live person is "
                f"present rather than a captured image.",
            )
        )

        centred = QHBoxLayout()
        centred.addStretch(1)
        centred.addWidget(self.view)
        centred.addStretch(1)
        self._layout.addLayout(centred)

        self._instruction = QLabel("Press Start when you are ready.")
        self._instruction.setObjectName("FieldLabel")
        self._instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._instruction)
        self._layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._cancel = ghost_button("Cancel", self.reject)
        buttons.addWidget(self._cancel)
        self._start = confirm_button("Start", self._begin)
        buttons.addWidget(self._start)
        self._layout.addLayout(buttons)

        self.start_camera()

    def _set_capture_enabled(self, enabled: bool) -> None:
        self._start.setEnabled(enabled)

    def _begin(self) -> None:
        if self._camera.latest_frame is None:
            self.status.error("No frame available yet. Give the camera a moment.")
            return
        self.frames.clear()
        self._start.setEnabled(False)
        self._timer.start()
        self._grab()

    def _grab(self) -> None:
        jpeg = self.current_frame_jpeg()
        if jpeg is None:
            return

        self.frames.append(jpeg)
        captured = len(self.frames)

        # The first couple of frames establish the neutral baseline the server
        # measures the turn against, so the prompt changes partway through.
        if captured <= 2:
            self._instruction.setText("Hold still, looking straight ahead...")
        else:
            self._instruction.setText(f"Now turn your head to your {self._direction}...")

        self.status.busy(f"Captured {captured} of {self._required}")

        if captured >= self._required:
            self._timer.stop()
            self.accept()
