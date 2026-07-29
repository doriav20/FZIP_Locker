"""Webcam capture on a background thread.

The 2022 client called ``cv2.imshow`` in a blocking ``while`` loop on the Qt
main thread, which froze the whole application for the duration of the scan
and opened a separate OS window outside the app. Here frames are pulled on a
QThread and delivered by signal, so the preview is embedded in the UI and the
window stays responsive.
"""

from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from .errors import CameraError

#: Encoding quality for frames sent to the server. 85 keeps faces clearly
#: recognisable while keeping a 5-frame verification burst small.
JPEG_QUALITY = 85


def encode_jpeg(frame: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise CameraError("Could not encode the captured frame.")
    return bytes(buffer)


def to_qimage(frame: np.ndarray) -> QImage:
    """Wrap a BGR OpenCV frame as a QImage.

    ``.copy()`` is not optional: QImage does not take ownership of the buffer,
    and the numpy array it points at is reused for the next frame.
    """
    height, width, _ = frame.shape
    return QImage(
        frame.data, width, height, width * 3, QImage.Format.Format_BGR888
    ).copy()


def open_capture(index: int = 0) -> cv2.VideoCapture:
    """Open a camera, preferring a backend that does not log spurious warnings."""
    if hasattr(cv2, "CAP_DSHOW"):
        # DirectShow on Windows avoids the noisy async-callback teardown
        # warning the original code worked around the same way.
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if capture.isOpened():
            return capture
        capture.release()

    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        raise CameraError
    return capture


class CameraThread(QThread):
    """Continuously reads frames and emits them until stopped."""

    frame_ready = pyqtSignal(QImage)
    #: Emitted with the raw BGR frame, for capture rather than display.
    raw_frame = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, camera_index: int = 0) -> None:
        super().__init__()
        self._camera_index = camera_index
        self._running = False
        self._latest: np.ndarray | None = None

    @property
    def latest_frame(self) -> np.ndarray | None:
        """Most recent frame, or None before the first read."""
        return None if self._latest is None else self._latest.copy()

    def run(self) -> None:
        try:
            capture = open_capture(self._camera_index)
        except CameraError as exc:
            self.failed.emit(exc.user_message)
            return

        self._running = True
        try:
            while self._running:
                ok, frame = capture.read()
                if not ok or frame is None:
                    self.failed.emit(CameraError.user_message)
                    return
                # Mirror for display only. The frames sent to the server stay
                # un-mirrored, because the server's head-turn check depends on
                # the true left/right orientation.
                self._latest = frame
                self.raw_frame.emit(frame)
                self.frame_ready.emit(to_qimage(cv2.flip(frame, 1)))
                self.msleep(30)  # ~30 fps
        finally:
            capture.release()

    def stop(self) -> None:
        self._running = False
        self.wait(2000)
