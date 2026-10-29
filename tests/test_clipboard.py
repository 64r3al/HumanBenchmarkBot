"""Tests for fresh clipboard numeric-value validation."""

import pytest

from human_benchmark_bot.clipboard import wait_for_numeric_clipboard


def test_wait_for_numeric_clipboard_returns_valid_number() -> None:
    values = iter(["", "old text", "  12345  "])
    assert wait_for_numeric_clipboard(
        lambda: next(values),
        timeout=0.2,
        poll_interval=0.001,
    ) == "12345"


def test_wait_for_numeric_clipboard_rejects_stale_or_non_numeric_values() -> None:
    assert (
        wait_for_numeric_clipboard(
            lambda: "previous answer",
            timeout=0.01,
            poll_interval=0.001,
        )
        is None
    )


def test_wait_for_numeric_clipboard_rejects_values_over_digit_limit() -> None:
    assert (
        wait_for_numeric_clipboard(
            lambda: "123456",
            timeout=0.01,
            poll_interval=0.001,
            max_digits=5,
        )
        is None
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout": 0},
        {"poll_interval": 0},
        {"max_digits": 0},
    ],
)
def test_wait_for_numeric_clipboard_validates_parameters(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        wait_for_numeric_clipboard(lambda: "", **kwargs)
