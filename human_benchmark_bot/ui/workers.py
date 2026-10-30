"""Qt worker for long-running automation tasks."""

from __future__ import annotations

from threading import Event
from typing import Any

from PySide6.QtCore import QThread, Signal

from ..automation import RunCancelled
from .services import RunConfig, run_game


class RunWorker(QThread):
    """Execute a game routine outside the UI thread and report its real outcome."""

    log = Signal(str, str)
    result_ready = Signal(dict)
    error = Signal(str)
    cancelled = Signal(str)

    def __init__(self, config: RunConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.cancel_event = Event()

    def request_cancel(self) -> None:
        """Ask the running routine to stop at its next cooperative checkpoint."""
        self.cancel_event.set()

    def run(self) -> None:
        try:
            result: dict[str, Any] = run_game(
                self.config,
                self.cancel_event,
                self._log_message,
            )
            if result.get("status") == "cancelled" or self.cancel_event.is_set():
                self.cancelled.emit(str(result.get("message", "Run cancelled.")))
            else:
                self.result_ready.emit(result)
        except RunCancelled as exc:
            self.cancelled.emit(str(exc) or "Run cancelled at a safe checkpoint.")
        except Exception as exc:
            self.error.emit(f"{exc.__class__.__name__}: {exc}")

    def _log_message(self, level: str, message: str) -> None:
        self.log.emit(level, message)
