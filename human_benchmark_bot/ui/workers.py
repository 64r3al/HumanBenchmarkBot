"""Qt worker for long-running automation tasks."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from threading import Event
from typing import Any

from PySide6.QtCore import QThread, Signal

from .services import RunConfig, run_game


class _SignalWriter(io.TextIOBase):
    """Redirect line-oriented text from the existing routines to a Qt signal."""

    def __init__(self, signal: Signal, level: str = "info"):
        super().__init__()
        self.signal = signal
        self.level = level
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            text = str(text)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            cleaned = line.strip()
            if cleaned:
                self.signal.emit(self.level, cleaned)
        return len(text)

    def flush(self) -> None:
        cleaned = self._buffer.strip()
        if cleaned:
            self.signal.emit(self.level, cleaned)
        self._buffer = ""


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
        writer = _SignalWriter(self.log)
        try:
            with redirect_stdout(writer), redirect_stderr(_SignalWriter(self.log, "warning")):
                result: dict[str, Any] = run_game(
                    self.config,
                    self.cancel_event,
                    self._log_message,
                )
            writer.flush()
            if result.get("status") == "cancelled" or self.cancel_event.is_set():
                self.cancelled.emit(str(result.get("message", "Run cancelled.")))
            else:
                self.result_ready.emit(result)
        except Exception as exc:
            if exc.__class__.__name__ == "RunCancelled" or self.cancel_event.is_set():
                self.cancelled.emit(str(exc) or "Run cancelled at a safe checkpoint.")
            else:
                self.error.emit(f"{exc.__class__.__name__}: {exc}")
        finally:
            writer.flush()

    def _log_message(self, level: str, message: str) -> None:
        self.log.emit(level, message)
