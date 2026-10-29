"""Reusable browser, mouse, screenshot, and pixel-detection helpers."""

from __future__ import annotations

import time
import webbrowser
from collections.abc import Sequence

import pyautogui

from .geometry import Point, Region, scaled_point, scaled_region

RGB = tuple[int, int, int]

# Keep the safety stop enabled: moving the pointer to the top-left corner
# triggers PyAutoGUI's fail-safe exception.
pyautogui.FAILSAFE = True


def reference_point(x: float, y: float) -> Point:
    """Return a reference-layout point scaled to the current display."""
    return scaled_point(x, y, pyautogui.size())


def reference_region(
    x: float, y: float, width: float, height: float
) -> Region:
    """Return a reference-layout screenshot region scaled to the display."""
    return scaled_region(x, y, width, height, pyautogui.size())


def parse_hex_color(value: str) -> RGB:
    """Convert an RGB color such as #18d971 to a tuple."""
    color = value.strip().removeprefix("#")
    if len(color) != 6:
        raise ValueError("Expected a six-digit RGB hex color.")
    try:
        return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Invalid RGB hex color: {value!r}") from exc


def color_matches(
    actual: Sequence[int], expected: Sequence[int], tolerance: int = 12
) -> bool:
    """Return whether each RGB channel is within the supplied tolerance."""
    return len(actual) >= 3 and len(expected) >= 3 and all(
        abs(int(actual[channel]) - int(expected[channel])) <= tolerance
        for channel in range(3)
    )


def wait_for_color(
    point: Point,
    expected: RGB,
    timeout: float = 15.0,
    tolerance: int = 18,
    poll_interval: float = 0.01,
) -> bool:
    """Poll a screen pixel until it matches a color or the timeout expires."""
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("Timeout and poll interval must be positive.")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if color_matches(pyautogui.pixel(*point), expected, tolerance):
            return True
        time.sleep(poll_interval)
    return False


def open_game(game_name: str, url: str, load_wait: int = 5) -> None:
    """Open a game in the default browser and allow time for page loading."""
    if load_wait < 0:
        raise ValueError("load_wait must be zero or greater.")
    print(f"Opening {game_name}: {url}")
    webbrowser.open_new_tab(url)
    for remaining in range(load_wait, 0, -1):
        print(f"Focus the game tab — starting in {remaining} second(s)...")
        time.sleep(1)
    print("Automation started. Do not use the mouse or keyboard for other tasks.")
