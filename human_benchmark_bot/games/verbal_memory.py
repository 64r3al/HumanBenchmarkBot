"""Experimental Verbal Memory routine using Tesseract OCR."""

from __future__ import annotations

import re
import time

import pyautogui
import pytesseract

from ..automation import open_game, reference_point, reference_region
from ..config import GAME_URLS


def run(rounds: int = 100, load_wait: int = 5) -> None:
    """Classify each OCR-read word as new or previously encountered."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game("Verbal Memory", GAME_URLS["verbal"], load_wait)

    start_point = reference_point(951, 507)
    seen_button = reference_point(870, 446)
    new_button = reference_point(1038, 444)
    word_region = reference_region(590, 292, 690, 75)

    pyautogui.click(*start_point)
    time.sleep(0.6)

    seen_words: set[str] = set()
    for turn in range(1, rounds + 1):
        screenshot = pyautogui.screenshot(region=word_region)
        raw_text = pytesseract.image_to_string(screenshot, config="--psm 7")
        word = re.sub(r"[^A-Za-z'-]", "", raw_text).lower().strip()

        if not word:
            time.sleep(0.15)
            screenshot = pyautogui.screenshot(region=word_region)
            raw_text = pytesseract.image_to_string(screenshot, config="--psm 7")
            word = re.sub(r"[^A-Za-z'-]", "", raw_text).lower().strip()

        if not word:
            raise RuntimeError(
                "OCR could not read the displayed word. Check Tesseract, "
                "browser focus, the screenshot region, and page zoom."
            )

        if word in seen_words:
            pyautogui.click(*seen_button)
            action = "seen"
        else:
            seen_words.add(word)
            pyautogui.click(*new_button)
            action = "new"

        if turn == 1 or turn % 10 == 0:
            print(
                f"Verbal Memory: {turn}/{rounds} — classified '{word}' as {action}."
            )
        time.sleep(0.25)

    print(f"Verbal Memory routine finished ({len(seen_words)} unique OCR words).")
