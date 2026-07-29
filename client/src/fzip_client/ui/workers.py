"""Run blocking work off the Qt event loop.

Every network call, key derivation and archive operation in the 2022 client
ran inline in a button handler, so the window locked up -- Argon2id at 64 MiB
plus a multi-gigabyte archive would make that unbearable rather than merely
untidy. These helpers push the work to a thread pool and deliver the result
back as a signal.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from ..errors import FzipError


class _Signals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str, object)


class Task(QRunnable):
    """Runs ``fn`` on the thread pool and emits the outcome.

    ``failed`` carries both a display-ready message and the exception itself,
    so a caller that needs to branch on the specific error type still can.

    Not generic: Qt signals carry ``object``, so the result type is erased the
    moment it crosses the signal boundary anyway.
    """

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self._fn = fn
        self.signals = _Signals()

    @property
    def finished(self) -> pyqtSignal:
        return self.signals.finished

    @property
    def failed(self) -> pyqtSignal:
        return self.signals.failed

    def run(self) -> None:
        try:
            result = self._fn()
        except FzipError as exc:
            self.signals.failed.emit(exc.user_message, exc)
        except Exception as exc:
            # Unexpected failures still have to reach the UI. The old client
            # swallowed these in bare `except:` blocks, so a genuine bug was
            # indistinguishable from a wrong password.
            self.signals.failed.emit(f"Unexpected error: {exc}", exc)
        else:
            self.signals.finished.emit(result)


def run_async(
    fn: Callable[[], Any],
    on_success: Callable[[Any], None],
    on_error: Callable[[str, Exception], None],
) -> None:
    """Submit ``fn`` to the global thread pool."""
    task = Task(fn)
    task.signals.finished.connect(on_success)
    task.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(task)
