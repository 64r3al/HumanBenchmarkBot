"""Experimental Verbal Memory routine using confidence-checked Tesseract OCR."""

from __future__ import annotations

import pyautogui
import pytesseract
from PIL import Image, ImageOps
from threading import Event

from ..automation import (
    AutomationError,
    GameEnded,
    check_cancelled,
    click_point,
    interruptible_sleep,
    open_game,
    reference_point,
    reference_region,
    save_diagnostic_screenshot,
)
from ..config import GAME_URLS
from ..recognition import classify_word, is_terminal_text, normalize_word

_MIN_OCR_CONFIDENCE = 55.0


def _read_once(image: Image.Image, *, threshold: bool) -> tuple[str, float, str]:
    """Read a word and average OCR confidence for recognized text tokens."""
    grayscale = ImageOps.autocontrast(image.convert("L"))
    width, height = grayscale.size
    if width < 1 or height < 1:
        return "", 0.0, ""

    enlarged = grayscale.resize(
        (max(width * 3, 1), max(height * 3, 1)),
        Image.Resampling.LANCZOS,
    )
    if threshold:
        enlarged = enlarged.point(lambda value: 255 if value >= 155 else 0)

    data = pytesseract.image_to_data(
        enlarged,
        config="--oem 3 --psm 7",
        lang="eng",
        output_type=pytesseract.Output.DICT,
    )
    raw_tokens: list[str] = []
    confidences: list[float] = []
    for text, confidence in zip(data.get("text", []), data.get("conf", [])):
        token = str(text).strip()
        if not token:
            continue
        raw_tokens.append(token)
        try:
            parsed_confidence = float(confidence)
        except (TypeError, ValueError):
            continue
        if parsed_confidence >= 0:
            confidences.append(parsed_confidence)

    raw_text = " ".join(raw_tokens)
    if is_terminal_text(raw_text):
        raise GameEnded(
            "The Verbal Memory screen appears to show an end-of-game state."
        )

    word = normalize_word(raw_text)
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return word, confidence, raw_text


def read_displayed_word(image: Image.Image) -> tuple[str, float]:
    """Read a single displayed word, retrying with thresholded imagery."""
    failures: list[str] = []
    for threshold in (False, True):
        word, confidence, raw_text = _read_once(image, threshold=threshold)
        if word and confidence >= _MIN_OCR_CONFIDENCE:
            return word, confidence
        failures.append(
            f"text={raw_text!r}, confidence={confidence:.1f}, word={word!r}"
        )

    raise AutomationError(
        "OCR could not read the displayed word with sufficient confidence. "
        + " | ".join(failures)
    )


def run(
    rounds: int = 100,
    load_wait: int = 5,
    *,
    debug: bool = False,
    diagnostics_dir: str = "diagnostics",
    cancel_event: Event | None = None,
) -> None:
    """Classify words using OCR; stop on unreadable or terminal states."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1.")

    open_game(
        "Verbal Memory", GAME_URLS["verbal"], load_wait, cancel_event=cancel_event
    )

    start_point = reference_point(951, 507)
    seen_button = reference_point(870, 446)
    new_button = reference_point(1038, 444)
    word_region = reference_region(590, 292, 690, 75)

    click_point(start_point, cancel_event=cancel_event)
    interruptible_sleep(0.6, cancel_event)

    seen_words: set[str] = set()
    for turn in range(1, rounds + 1):
        check_cancelled(cancel_event)
        screenshot = pyautogui.screenshot(region=word_region)
        try:
            word, confidence = read_displayed_word(screenshot)
            check_cancelled(cancel_event)
        except GameEnded:
            print(f"Verbal Memory ended after {turn - 1} completed interaction(s).")
            return
        except (AutomationError, pytesseract.TesseractNotFoundError) as exc:
            save_diagnostic_screenshot(
                "verbal-ocr-failed",
                enabled=debug,
                directory=diagnostics_dir,
            )
            if isinstance(exc, pytesseract.TesseractNotFoundError):
                raise AutomationError(
                    "Tesseract was not found. Install it separately or set "
                    "--tesseract-cmd to its executable path."
                ) from exc
            raise

        try:
            action = classify_word(word, seen_words)
        except ValueError as exc:
            save_diagnostic_screenshot(
                "verbal-word-invalid",
                enabled=debug,
                directory=diagnostics_dir,
            )
            raise AutomationError(str(exc)) from exc

        button = seen_button if action == "seen" else new_button
        click_point(button, cancel_event=cancel_event)
        if turn == 1 or turn % 10 == 0:
            print(
                f"Verbal Memory: {turn}/{rounds} — {action} "
                f"(OCR confidence {confidence:.1f}%)."
            )
        interruptible_sleep(0.25, cancel_event)

    print(
        f"Verbal Memory routine reached its configured limit of {rounds} "
        f"interactions ({len(seen_words)} unique words). Verify the result "
        "on screen; the routine may stop early if it detects a terminal state."
    )
