"""Clipboard helpers that reject stale or malformed copied values."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from threading import Event


def wait_for_numeric_clipboard(
    read_text: Callable[[], str],
    *,
    timeout: float = 1.25,
    poll_interval: float = 0.05,
    max_digits: int = 20,
    cancel_event: Event | None = None,
) -> str | None:
    """Return a fresh integer-like clipboard value, or None on timeout.

    The caller should clear the clipboard before triggering Ctrl+C/Command+C.
    This function never returns a value that fails the full numeric pattern.
    Cancellation is checked between clipboard reads.
    """
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("timeout and poll_interval must be positive.")
    if max_digits < 1:
        raise ValueError("max_digits must be at least 1.")

    from .automation import check_cancelled, interruptible_sleep

    pattern = re.compile(rf"\d{{1,{max_digits}}}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_cancelled(cancel_event)
        try:
            value = read_text()
        except Exception:
            value = ""
        if isinstance(value, str):
            value = value.strip()
            if pattern.fullmatch(value):
                return value
        interruptible_sleep(poll_interval, cancel_event)
    check_cancelled(cancel_event)
    return None
