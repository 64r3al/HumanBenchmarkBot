"""Pure text-normalization helpers for OCR-backed game routines."""

from __future__ import annotations

import re

_TERMINAL_PHRASES = (
    "game over",
    "final score",
    "save score",
    "play again",
    "test complete",
    "test completed",
    "you scored",
)


def normalized_display_text(text: str) -> str:
    """Normalize recognized UI text for terminal-state comparisons."""
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def is_terminal_text(text: str) -> bool:
    """Return True when OCR text resembles a known end-of-game screen."""
    normalized = normalized_display_text(text)
    return any(phrase in normalized for phrase in _TERMINAL_PHRASES)


def normalize_word(text: str) -> str:
    """Return one normalized English word; reject multi-token OCR output."""
    tokens = re.findall(r"[a-z]+(?:['-][a-z]+)*", text.casefold())
    return tokens[0] if len(tokens) == 1 else ""


def classify_word(word: str, seen_words: set[str]) -> str:
    """Classify and remember a normalized word, rejecting empty OCR output."""
    normalized = normalize_word(word)
    if not normalized:
        raise ValueError("Expected exactly one readable word.")
    if normalized in seen_words:
        return "seen"
    seen_words.add(normalized)
    return "new"
