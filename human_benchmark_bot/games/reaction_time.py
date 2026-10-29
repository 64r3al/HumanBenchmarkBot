"""Experimental Reaction Time routine with bounded visual-state waits."""

from __future__ import annotations

from threading import Event

from ..automation import (
    AutomationError,
    DetectionTimeout,
    check_cancelled,
    click_point,
    open_game,
    reference_point,
    save_diagnostic_screenshot,
    wait_for_color,
)
from ..config import GAME_URLS, REACTION_GREEN, REACTION_RESULT_BLUE


def run(
    rounds: int = 5,
    load_wait: int = 5,
    *,
    debug: bool = False,
    diagnostics_dir: str = "diagnostics",
    cancel_event: Event | None = None,
) -> None:
    """Run reaction-time trials using the reference UI coordinates.

    Live website behavior and pixel locations can change. Every expected visual
    transition has a timeout; the routine stops instead of clicking blindly.
    """
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game(
        "Reaction Time", GAME_URLS["reaction"], load_wait, cancel_event=cancel_event
    )
    target = reference_point(960, 270)

    print(
        "Clicking the game starts a trial. Keep the game visible and avoid "
        "other mouse/keyboard input until the routine finishes."
    )
    click_point(target, cancel_event=cancel_event)

    for turn in range(1, rounds + 1):
        check_cancelled(cancel_event)
        if not wait_for_color(
            target,
            REACTION_GREEN,
            timeout=30,
            tolerance=24,
            poll_interval=0.01,
            cancel_event=cancel_event,
        ):
            save_diagnostic_screenshot(
                "reaction-green-timeout",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise DetectionTimeout(
                f"Trial {turn}/{rounds}: the green state was not detected "
                "within 30 seconds. Check browser focus, zoom, and layout."
            )

        click_point(target, cancel_event=cancel_event)
        if not wait_for_color(
            target,
            REACTION_RESULT_BLUE,
            timeout=5,
            tolerance=24,
            cancel_event=cancel_event,
        ):
            save_diagnostic_screenshot(
                "reaction-state-did-not-change",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise AutomationError(
                f"Trial {turn}/{rounds}: the expected result screen was not "
                "detected after the click. Stopping instead of risking extra clicks."
            )

        print(f"Reaction Time: interaction {turn}/{rounds} completed.")

        if turn < rounds:
            # The result screen normally accepts a click to begin the next trial.
            click_point(target, cancel_event=cancel_event)

    print(
        "Reaction Time routine finished. Verify the on-screen results before "
        "saving or sharing them."
    )
