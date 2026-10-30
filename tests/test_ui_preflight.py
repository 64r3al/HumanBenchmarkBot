"""Acceptance-oriented tests for desktop GUI preflight gates."""

from __future__ import annotations

import pyautogui
import pytest
import subprocess

from human_benchmark_bot.calibration import ScreenCalibration
from human_benchmark_bot.ui import services
from human_benchmark_bot.ui.services import (
    RunConfig,
    build_preflight,
    can_start_run,
)


def _full_screen_profile() -> ScreenCalibration:
    return ScreenCalibration(
        screen_width=1920,
        screen_height=1080,
        x=0,
        y=0,
        width=1920,
        height=1080,
        created_at="test",
    )


@pytest.fixture
def fixed_display(monkeypatch):
    monkeypatch.setattr(pyautogui, "size", lambda: (1920, 1080))


def test_preflight_blocks_when_viewport_is_not_calibrated(
    monkeypatch, fixed_display
) -> None:
    monkeypatch.setattr(services, "load_calibration", lambda: None)

    checks = build_preflight(RunConfig(game="reaction", rounds=5))

    viewport = next(check for check in checks if check.name == "Game viewport")
    assert viewport.status == "failed"
    assert viewport.blocking is True
    assert not can_start_run(checks)


def test_preflight_allows_compatible_geometry_but_warns_about_focus(
    monkeypatch, fixed_display
) -> None:
    monkeypatch.setattr(services, "load_calibration", _full_screen_profile)

    checks = build_preflight(RunConfig(game="reaction", rounds=5))

    geometry = next(check for check in checks if check.name == "Reference geometry")
    focus = next(check for check in checks if check.name == "Browser focus")
    assert geometry.status == "passed"
    assert focus.status == "attention"
    assert focus.blocking is False
    assert can_start_run(checks)


def test_preflight_blocks_when_calibrated_viewport_excludes_reference_points(
    monkeypatch, fixed_display
) -> None:
    profile = ScreenCalibration(
        screen_width=1920,
        screen_height=1080,
        x=100,
        y=100,
        width=500,
        height=300,
        created_at="test",
    )
    monkeypatch.setattr(services, "load_calibration", lambda: profile)

    checks = build_preflight(RunConfig(game="reaction", rounds=5))

    geometry = next(check for check in checks if check.name == "Reference geometry")
    assert geometry.status == "failed"
    assert geometry.blocking is True
    assert not can_start_run(checks)


def test_verbal_preflight_blocks_when_tesseract_is_missing(
    monkeypatch, fixed_display
) -> None:
    monkeypatch.setattr(services, "load_calibration", _full_screen_profile)
    monkeypatch.setattr(
        services,
        "_probe_tesseract",
        lambda _path="": (None, "Tesseract was not found."),
    )

    checks = build_preflight(RunConfig(game="verbal", rounds=100))

    ocr = next(check for check in checks if check.name == "Tesseract OCR")
    assert ocr.status == "failed"
    assert ocr.blocking is True
    assert not can_start_run(checks)


def test_tesseract_probe_requires_english_language_data(monkeypatch) -> None:
    monkeypatch.setattr(
        services, "_find_tesseract", lambda _path="": "/usr/bin/tesseract"
    )
    monkeypatch.setattr(
        services.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=["tesseract", "--list-langs"],
            returncode=0,
            stdout='List of available languages in "tessdata":\nfra\n',
            stderr="",
        ),
    )

    executable, detail = services._probe_tesseract()

    assert executable is None
    assert "English (eng) language data is missing" in detail


def test_tesseract_probe_accepts_available_english_language_data(monkeypatch) -> None:
    captured: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setattr(
        services, "_find_tesseract", lambda _path="": "/usr/bin/tesseract"
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
        captured.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=["tesseract", "--list-langs"],
            returncode=0,
            stdout='List of available languages in "tessdata":\neng\nosd\n',
            stderr="",
        )

    monkeypatch.setattr(services.subprocess, "run", fake_run)

    executable, detail = services._probe_tesseract()

    assert executable == "/usr/bin/tesseract"
    assert "English OCR language data is available" in detail
    assert captured[0][1]["timeout"] == 5
    assert captured[0][1]["check"] is False


def test_tesseract_probe_stops_on_process_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        services, "_find_tesseract", lambda _path="": "/usr/bin/tesseract"
    )

    def timed_out(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("tesseract", timeout=5)

    monkeypatch.setattr(services.subprocess, "run", timed_out)

    executable, detail = services._probe_tesseract()

    assert executable is None
    assert "did not respond within 5 seconds" in detail


def test_number_preflight_checks_clipboard_package_without_reading_clipboard(
    monkeypatch, fixed_display
) -> None:
    monkeypatch.setattr(services, "load_calibration", _full_screen_profile)
    monkeypatch.setattr(
        services.importlib.util,
        "find_spec",
        lambda name: None if name == "pyperclip" else object(),
    )

    checks = build_preflight(RunConfig(game="number", rounds=20))

    clipboard = next(check for check in checks if check.name == "Clipboard support")
    assert clipboard.status == "failed"
    assert clipboard.blocking is True
    assert not can_start_run(checks)


def test_invalid_run_configuration_stops_preflight_early() -> None:
    checks = build_preflight(RunConfig(game="reaction", rounds=0))

    assert len(checks) == 1
    assert checks[0].name == "Run configuration"
    assert checks[0].status == "failed"
    assert checks[0].blocking is True
