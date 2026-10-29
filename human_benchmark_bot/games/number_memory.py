"""Experimental Number Memory automation routine."""

from __future__ import annotations

import re
import time

import pyautogui
import pyperclip

from ..automation import open_game, reference_point, wait_for_color
from ..config import GAME_URLS, NUMBER_INPUT_BLUE


def run(rounds: int = 20, load_wait: int = 5) -> None:
    """Copy each displayed number and submit it when the entry state appears."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Number Memory", GAME_URLS["number"], load_wait)
    sample_point = reference_point(960, 360)
    start_point = reference_point(960, 460)

    pyautogui.click(*start_point)
    time.sleep(0.3)

    for turn in range(1, rounds + 1):
        # The number is expected to be selectable text in the reference layout.
        # Clear old clipboard data so a failed copy cannot reuse a prior answer.
        pyperclip.copy("")
        pyautogui.click(*sample_point, clicks=3, interval=0.08)
        pyautogui.hotkey("ctrl", "c")
        number = pyperclip.paste().strip()

        if not re.fullmatch(r"\d{1,20}", number):
            raise RuntimeError(
                "Could not copy a numeric value from the game. The current "
                "page may not support text selection at the configured point."
            )

        if not wait_for_color(
            sample_point, NUMBER_INPUT_BLUE, timeout=20, tolerance=25
        ):
            raise RuntimeError(
                "The number-entry state was not detected before timeout."
            )

        pyautogui.click(*sample_point)
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        print(f"Number Memory: submitted value for round {turn}/{rounds}.")
        time.sleep(0.5)

        if turn < rounds:
            pyautogui.click(*sample_point)
            time.sleep(0.2)

    print("Number Memory routine finished.")
