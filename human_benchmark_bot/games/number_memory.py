"""Experimental Number Memory routine with clipboard validation."""

from __future__ import annotations

import time

import pyautogui
import pyperclip

from ..automation import (
    AutomationError,
    DetectionTimeout,
    click_point,
    clipboard_modifier,
    open_game,
    reference_point,
    save_diagnostic_screenshot,
    wait_for_color,
)
from ..clipboard import wait_for_numeric_clipboard
from ..config import GAME_URLS, NUMBER_INPUT_BLUE


def _copy_displayed_number(sample_point: tuple[int, int]) -> str:
    """Select and copy the displayed number, refusing stale clipboard content."""
    try:
        pyperclip.copy("")
    except Exception as exc:
        raise AutomationError(
            "Clipboard access is unavailable. Check the operating-system "
            "clipboard backend and permissions."
        ) from exc

    click_point(sample_point, clicks=3, interval=0.08)
    pyautogui.hotkey(clipboard_modifier(), "c")
    number = wait_for_numeric_clipboard(pyperclip.paste)
    if number is None:
        raise AutomationError(
            "Could not copy a numeric value. The displayed number may not be "
            "selectable, or the game layout may have changed."
        )
    return number


def run(
    rounds: int = 20,
    load_wait: int = 5,
    *,
    debug: bool = False,
    diagnostics_dir: str = "diagnostics",
) -> None:
    """Copy and submit displayed numbers with bounded state checks."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Number Memory", GAME_URLS["number"], load_wait)
    sample_point = reference_point(960, 360)
    start_point = reference_point(960, 460)

    click_point(start_point)
    time.sleep(0.35)

    for turn in range(1, rounds + 1):
        try:
            number = _copy_displayed_number(sample_point)
        except AutomationError:
            save_diagnostic_screenshot(
                "number-copy-failed",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise

        if not wait_for_color(
            sample_point,
            NUMBER_INPUT_BLUE,
            timeout=20,
            tolerance=25,
        ):
            save_diagnostic_screenshot(
                "number-input-state-timeout",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise DetectionTimeout(
                f"Round {turn}/{rounds}: the number-entry state was not detected. "
                "The page layout or colors may have changed."
            )

        click_point(sample_point)
        pyautogui.write(number, interval=0.02)
        pyautogui.press("enter")
        print(f"Number Memory: submitted the copied value for round {turn}/{rounds}.")

        if turn < rounds:
            # Start the next level only after the result transition has had time
            # to render. If the expected button location is wrong, stop testing
            # instead of relying on an unlimited series of clicks.
            time.sleep(0.35)
            click_point(start_point)
            time.sleep(0.35)

    print(
        "Number Memory routine finished. Verify the game's on-screen result; "
        "text selection can vary with browser and website changes."
    )
