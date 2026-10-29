"""Tests for automation helpers using mocked screen input."""

from pathlib import Path

import pytest
from PIL import Image

from human_benchmark_bot import automation


def test_parse_hex_color_accepts_optional_hash() -> None:
    assert automation.parse_hex_color("#18d971") == (24, 217, 113)
    assert automation.parse_hex_color("006ea5") == (0, 110, 165)


@pytest.mark.parametrize("value", ["", "#123", "1234567", "zzzzzz"])
def test_parse_hex_color_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        automation.parse_hex_color(value)


def test_color_matches_respects_tolerance() -> None:
    assert automation.color_matches((25, 216, 112), (24, 217, 113), 1)
    assert not automation.color_matches((30, 216, 112), (24, 217, 113), 1)


def test_color_matches_rejects_invalid_tolerance() -> None:
    with pytest.raises(ValueError):
        automation.color_matches((0, 0, 0), (0, 0, 0), -1)


def test_click_point_rejects_off_screen_coordinate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(automation.pyautogui, "size", lambda: (100, 100))
    monkeypatch.setattr(
        automation.pyautogui,
        "click",
        lambda *args, **kwargs: pytest.fail("out-of-bounds click was attempted"),
    )
    with pytest.raises(automation.AutomationError):
        automation.click_point((100, 25))


def test_click_point_passes_valid_coordinate_to_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(automation.pyautogui, "size", lambda: (100, 100))
    captured: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_click(*args: object, **kwargs: object) -> None:
        captured.append((args, kwargs))

    monkeypatch.setattr(automation.pyautogui, "click", fake_click)
    automation.click_point((20, 30), clicks=2, interval=0.1)
    assert captured == [((20, 30), {"clicks": 2, "interval": 0.1})]


def test_wait_for_color_returns_true_for_expected_pixel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(automation.pyautogui, "size", lambda: (100, 100))
    values = iter([(1, 2, 3), (24, 217, 113)])
    monkeypatch.setattr(automation.pyautogui, "pixel", lambda *args: next(values))
    assert automation.wait_for_color(
        (10, 10), (24, 217, 113), timeout=0.2, poll_interval=0.001
    )


def test_wait_for_color_returns_false_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(automation.pyautogui, "size", lambda: (100, 100))
    monkeypatch.setattr(automation.pyautogui, "pixel", lambda *args: (0, 0, 0))
    assert not automation.wait_for_color(
        (10, 10), (24, 217, 113), timeout=0.01, poll_interval=0.001
    )


def test_wait_for_color_change_detects_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(automation.pyautogui, "size", lambda: (100, 100))
    values = iter([(24, 217, 113), (0, 137, 206)])
    monkeypatch.setattr(automation.pyautogui, "pixel", lambda *args: next(values))
    assert automation.wait_for_color_change(
        (10, 10), (24, 217, 113), timeout=0.2, poll_interval=0.001
    )


def test_diagnostic_screenshot_is_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        automation.pyautogui,
        "screenshot",
        lambda **kwargs: Image.new("RGB", (10, 10), (0, 0, 0)),
    )
    assert automation.save_diagnostic_screenshot(
        "failed-state", enabled=False, directory=tmp_path
    ) is None
    assert not tmp_path.exists()

    destination = automation.save_diagnostic_screenshot(
        "failed state!", enabled=True, directory=tmp_path
    )
    assert destination is not None
    assert destination.exists()
    assert destination.suffix == ".png"
