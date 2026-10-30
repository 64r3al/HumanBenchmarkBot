"""Experimental Number Memory routine with clipboard validation."""

from __future__ import annotations

import pyautogui
import pyperclip
from threading import Event

from ..automation import (
    AutomationError,
    DetectionTimeout,
    check_cancelled,
    click_point,
    emit_log,
    LogCallback,
    clipboard_modifier,
    interruptible_sleep,
    open_game,
    reference_point,
    save_diagnostic_screenshot,
    wait_for_color,
)
from ..clipboard import wait_for_numeric_clipboard
from ..config import GAME_URLS, NUMBER_INPUT_BLUE, NUMBER_READY_BLUE


def _copy_displayed_number(
    sample_point: tuple[int, int],
    *,
    cancel_event: Event | None = None,
) -> str:
    """Select and copy the displayed number, refusing stale clipboard content."""
    check_cancelled(cancel_event)
    try:
        pyperclip.copy("")
    except Exception as exc:
        raise AutomationError(
            "Clipboard access is unavailable. Check the operating-system "
            "clipboard backend and permissions."
        ) from exc

    click_point(sample_point, clicks=3, interval=0.08, cancel_event=cancel_event)
    check_cancelled(cancel_event)
    pyautogui.hotkey(clipboard_modifier(), "c")
    check_cancelled(cancel_event)
    number = wait_for_numeric_clipboard(pyperclip.paste, cancel_event=cancel_event)
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
    cancel_event: Event | None = None,
    log_callback: LogCallback | None = None,
) -> None:
    """Copy and submit displayed numbers with bounded state checks."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game(
        "Number Memory",
        GAME_URLS["number"],
        load_wait,
        cancel_event=cancel_event,
        log_callback=log_callback,
    )
    sample_point = reference_point(960, 360)
    start_point = reference_point(960, 460)

    if not wait_for_color(
        sample_point,
        NUMBER_READY_BLUE,
        timeout=15,
        tolerance=25,
        cancel_event=cancel_event,
    ):
        save_diagnostic_screenshot(
            "number-start-screen-not-detected",
            enabled=debug,
            directory=diagnostics_dir,
            log_callback=log_callback,
        )
        raise DetectionTimeout(
            "The Number Memory start screen was not detected. Check the "
            "browser tab, display layout, and observed UI colors."
        )

    click_point(start_point, cancel_event=cancel_event)
    interruptible_sleep(0.35, cancel_event)

    for turn in range(1, rounds + 1):
        check_cancelled(cancel_event)
        try:
            number = _copy_displayed_number(sample_point, cancel_event=cancel_event)
        except AutomationError:
            save_diagnostic_screenshot(
                "number-copy-failed",
                enabled=debug,
                directory=diagnostics_dir,
                log_callback=log_callback,
            )
            raise

        if not wait_for_color(
            sample_point,
            NUMBER_INPUT_BLUE,
            timeout=20,
            tolerance=25,
            cancel_event=cancel_event,
        ):
            save_diagnostic_screenshot(
                "number-input-state-timeout",
                enabled=debug,
                directory=diagnostics_dir,
                log_callback=log_callback,
            )
            raise DetectionTimeout(
                f"Round {turn}/{rounds}: the number-entry state was not detected. "
                "The page layout or colors may have changed."
            )

        click_point(sample_point, cancel_event=cancel_event)
        check_cancelled(cancel_event)
        pyautogui.write(number, interval=0.02)
        check_cancelled(cancel_event)
        pyautogui.press("enter")
        emit_log(
            f"Number Memory: submitted the copied value for round {turn}/{rounds}.",
            log_callback,
        )

        if turn < rounds:
            # Wait for the known ready-screen color before clicking the next-level
            # button. If the game ended or the layout changed, stop safely.
            if not wait_for_color(
                sample_point,
                NUMBER_READY_BLUE,
                timeout=8,
                tolerance=25,
                cancel_event=cancel_event,
            ):
                save_diagnostic_screenshot(
                    "number-next-level-not-detected",
                    enabled=debug,
                    directory=diagnostics_dir,
                    log_callback=log_callback,
                )
                raise DetectionTimeout(
                    f"Round {turn}/{rounds}: the next-level screen was not "
                    "detected after submitting the answer."
                )
            click_point(start_point, cancel_event=cancel_event)
            interruptible_sleep(0.35, cancel_event)

    emit_log(
        "Number Memory routine finished. Verify the game's on-screen result; "
        "text selection can vary with browser and website changes.",
        log_callback,
    )
