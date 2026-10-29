"""Experimental Reaction Time routine with bounded visual-state waits."""

from __future__ import annotations

from ..automation import (
    AutomationError,
    DetectionTimeout,
    click_point,
    open_game,
    reference_point,
    save_diagnostic_screenshot,
    wait_for_color,
    wait_for_color_change,
)
from ..config import GAME_URLS, REACTION_GREEN


def run(
    rounds: int = 5,
    load_wait: int = 5,
    *,
    debug: bool = False,
    diagnostics_dir: str = "diagnostics",
) -> None:
    """Run reaction-time trials using the reference UI coordinates.

    Live website behavior and pixel locations can change. Every expected visual
    transition has a timeout; the routine stops instead of clicking blindly.
    """
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Reaction Time", GAME_URLS["reaction"], load_wait)
    target = reference_point(960, 270)

    print(
        "Clicking the game starts a trial. Keep the game visible and avoid "
        "other mouse/keyboard input until the routine finishes."
    )
    click_point(target)

    for turn in range(1, rounds + 1):
        if not wait_for_color(
            target,
            REACTION_GREEN,
            timeout=30,
            tolerance=24,
            poll_interval=0.01,
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

        click_point(target)
        if not wait_for_color_change(
            target,
            REACTION_GREEN,
            timeout=5,
            tolerance=24,
        ):
            save_diagnostic_screenshot(
                "reaction-state-did-not-change",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise AutomationError(
                f"Trial {turn}/{rounds}: the green state did not change after "
                "the click. Stopping instead of risking extra clicks."
            )

        print(f"Reaction Time: interaction {turn}/{rounds} completed.")

        if turn < rounds:
            # The result screen normally accepts a click to begin the next trial.
            # The state-change check above prevents an immediate repeated click
            # while the green target is still visible.
            click_point(target)

    print(
        "Reaction Time routine finished. Verify the on-screen results before "
        "saving or sharing them."
    )
