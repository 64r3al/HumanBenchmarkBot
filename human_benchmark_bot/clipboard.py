"""Clipboard helpers that reject stale or malformed copied values."""

from __future__ import annotations

import re
import time
from collections.abc import Callable


def wait_for_numeric_clipboard(
    read_text: Callable[[], str],
    *,
    timeout: float = 1.25,
    poll_interval: float = 0.05,
    max_digits: int = 20,
) -> str | None:
    """Return a fresh integer-like clipboard value, or None on timeout.

    The caller should clear the clipboard before triggering Ctrl+C/Command+C.
    This function never returns a value that fails the full numeric pattern.
    """
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("timeout and poll_interval must be positive.")
    if max_digits < 1:
        raise ValueError("max_digits must be at least 1.")

    pattern = re.compile(rf"\d{{1,{max_digits}}}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = read_text()
        except Exception:
            value = ""
        if isinstance(value, str):
            value = value.strip()
            if pattern.fullmatch(value):
                return value
        time.sleep(poll_interval)
    return None
