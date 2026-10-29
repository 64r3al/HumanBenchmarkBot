"""Tests for OCR text normalization and word classification."""

import pytest

from human_benchmark_bot.recognition import (
    classify_word,
    is_terminal_text,
    normalize_word,
    normalized_display_text,
)


def test_normalize_word_is_case_insensitive() -> None:
    assert normalize_word("  HELLo!  ") == "hello"
    assert normalize_word("don't") == "don't"
    assert normalize_word("well-being") == "well-being"


@pytest.mark.parametrize("value", ["", "two words", "123", "word 123"])
def test_normalize_word_rejects_ambiguous_text(value: str) -> None:
    assert normalize_word(value) == ""


def test_terminal_state_detection() -> None:
    assert is_terminal_text("Game Over!")
    assert is_terminal_text("Your final score: 12")
    assert not is_terminal_text("game")
    assert not is_terminal_text("overview")


def test_normalized_display_text_collapses_punctuation() -> None:
    assert normalized_display_text("Game-Over!!") == "game over"


def test_classify_word_tracks_seen_words() -> None:
    seen: set[str] = set()
    assert classify_word("Apple", seen) == "new"
    assert classify_word("apple", seen) == "seen"
    assert seen == {"apple"}


def test_classify_word_rejects_empty_or_ambiguous_input() -> None:
    with pytest.raises(ValueError):
        classify_word("", set())
    with pytest.raises(ValueError):
        classify_word("two words", set())
