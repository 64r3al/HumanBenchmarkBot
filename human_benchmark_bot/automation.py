"""Reusable desktop automation helpers with explicit safety boundaries."""

from __future__ import annotations

import re
import time
import webbrowser
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TypeAlias

import pyautogui

from .geometry import Point, Region, scaled_point, scaled_region

RGB: TypeAlias = tuple[int, int, int]

# Keep PyAutoGUI's built-in emergency stop enabled and insert a small pause
# between input actions. Do not disable FAILSAFE in this project.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class AutomationError(RuntimeError):
    """Raised when an expected, safe automation step cannot be completed."""


class DetectionTimeout(AutomationError):
    """Raised when a visual state does not appear or disappear in time."""


class GameEnded(AutomationError):
    """Raised when a routine detects that the game has already ended."""


def reference_point(x: float, y: float) -> Point:
    """Return a reference-layout point scaled to the current display."""
    point = scaled_point(x, y, pyautogui.size())
    validate_point(point)
    return point


def reference_region(
    x: float, y: float, width: float, height: float
) -> Region:
    """Return a reference-layout region scaled to the display and bounds-checked."""
    region = scaled_region(x, y, width, height, pyautogui.size())
    left, top, region_width, region_height = region
    screen_width, screen_height = pyautogui.size()
    if (
        left < 0
        or top < 0
        or left + region_width > screen_width
        or top + region_height > screen_height
    ):
        raise AutomationError(
            f"Screenshot region {region} falls outside the primary display "
            f"({screen_width} x {screen_height})."
        )
    return region


def validate_point(point: Point) -> None:
    """Reject clicks or pixel reads outside the primary screen."""
    x, y = point
    screen_width, screen_height = pyautogui.size()
    if not (0 <= x < screen_width and 0 <= y < screen_height):
        raise AutomationError(
            f"Point {point} is outside the primary display "
            f"({screen_width} x {screen_height})."
        )


def click_point(
    point: Point,
    *,
    clicks: int = 1,
    interval: float = 0.1,
) -> None:
    """Click a validated screen point while retaining PyAutoGUI's fail-safe."""
    validate_point(point)
    if clicks < 1:
        raise ValueError("clicks must be at least 1.")
    if interval < 0:
        raise ValueError("interval must be zero or greater.")
    pyautogui.click(point[0], point[1], clicks=clicks, interval=interval)


def clipboard_modifier() -> str:
    """Return the operating-system modifier used for clipboard shortcuts."""
    import platform

    return "command" if platform.system() == "Darwin" else "ctrl"


def parse_hex_color(value: str) -> RGB:
    """Convert a color such as #18d971 to an RGB tuple."""
    color = value.strip().removeprefix("#")
    if len(color) != 6:
        raise ValueError("Expected a six-digit RGB hex color.")
    try:
        return tuple(
            int(color[index : index + 2], 16) for index in (0, 2, 4)
        )  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Invalid RGB hex color: {value!r}") from exc


def color_matches(
    actual: Sequence[int],
    expected: Sequence[int],
    tolerance: int = 12,
) -> bool:
    """Return whether RGB channels are within the requested tolerance."""
    if len(actual) < 3 or len(expected) < 3:
        raise ValueError("Colors must contain at least three RGB channels.")
    if not 0 <= tolerance <= 255:
        raise ValueError("tolerance must be between 0 and 255.")
    if any(not 0 <= int(value) <= 255 for value in (*actual[:3], *expected[:3])):
        raise ValueError("RGB channel values must be between 0 and 255.")
    return all(
        abs(int(actual[channel]) - int(expected[channel])) <= tolerance
        for channel in range(3)
    )


def wait_for_color(
    point: Point,
    expected: RGB,
    *,
    timeout: float = 15.0,
    tolerance: int = 18,
    poll_interval: float = 0.02,
) -> bool:
    """Poll a screen pixel until it matches a color or the timeout expires."""
    validate_point(point)
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("timeout and poll_interval must be positive.")
    if len(expected) != 3 or any(not 0 <= channel <= 255 for channel in expected):
        raise ValueError("expected must be a valid RGB triple.")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if color_matches(pyautogui.pixel(*point), expected, tolerance):
            return True
        time.sleep(poll_interval)
    return False


def wait_for_color_change(
    point: Point,
    original: RGB,
    *,
    timeout: float = 5.0,
    tolerance: int = 18,
    poll_interval: float = 0.02,
) -> bool:
    """Wait until a pixel differs from a previous visual state."""
    validate_point(point)
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("timeout and poll_interval must be positive.")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not color_matches(pyautogui.pixel(*point), original, tolerance):
            return True
        time.sleep(poll_interval)
    return False


def open_game(game_name: str, url: str, load_wait: int = 5) -> None:
    """Open a game in the default browser and provide a visible focus countdown."""
    if not 0 <= load_wait <= 120:
        raise ValueError("load_wait must be between 0 and 120 seconds.")

    print(f"Opening {game_name}: {url}")
    opened = webbrowser.open_new_tab(url)
    if opened is False:
        raise AutomationError(
            "The browser did not confirm that the game tab opened. "
            "Open it manually and retry."
        )
    for remaining in range(load_wait, 0, -1):
        print(
            f"Make sure the Human Benchmark tab is active — "
            f"starting in {remaining} second(s)..."
        )
        time.sleep(1)
    print(
        "Automation is active. Do not use the mouse or keyboard for other tasks."
    )


def save_diagnostic_screenshot(
    label: str,
    *,
    enabled: bool = False,
    directory: str | Path = "diagnostics",
) -> Path | None:
    """Optionally save a failure screenshot; never let diagnostics mask an error."""
    if not enabled:
        return None

    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "-", label).strip("-") or "failure"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    try:
        output_directory = Path(directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / f"{timestamp}-{safe_label}.png"
        pyautogui.screenshot().save(destination)
        print(f"Diagnostic screenshot saved: {destination}")
        return destination
    except Exception as exc:
        print(f"Warning: could not save diagnostic screenshot: {exc}")
        return None
