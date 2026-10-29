"""Experimental Reaction Time automation routine."""

from __future__ import annotations

import time

import pyautogui

from ..automation import open_game, reference_point, wait_for_color
from ..config import GAME_URLS, REACTION_GREEN


def run(rounds: int = 5, load_wait: int = 5) -> None:
    """Run reaction-time rounds using the reference UI coordinates."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Reaction Time", GAME_URLS["reaction"], load_wait)
    target = reference_point(960, 270)

    print("Click the game panel to begin.")
    pyautogui.click(*target)

    for turn in range(1, rounds + 1):
        if not wait_for_color(target, REACTION_GREEN, timeout=30, tolerance=22):
            raise RuntimeError(
                "The green state was not detected. Check browser focus, zoom, "
                "screen layout, and the game's current UI colors."
            )
        pyautogui.click(*target)
        print(f"Reaction Time: completed click {turn}/{rounds}.")

        if turn < rounds:
            time.sleep(0.35)
            pyautogui.click(*target)
            time.sleep(0.2)

    print("Reaction Time routine finished.")
