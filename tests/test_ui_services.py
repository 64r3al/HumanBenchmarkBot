"""Regression tests for the Qt-independent UI services."""

from __future__ import annotations

from threading import Event

import pytest

from human_benchmark_bot.calibration import (
    CalibrationError,
    ScreenCalibration,
    load_calibration,
    save_calibration,
    validate_current_display,
)
from human_benchmark_bot.ui.services import (
    HistoryStore,
    RunConfig,
    build_preview,
    can_start_run,
    run_game,
    validate_run_config,
)


@pytest.mark.parametrize(
    ("game", "rounds"),
    [
        ("reaction", 1),
        ("number", 20),
        ("verbal", 100),
        ("visual", 15),
    ],
)
def test_valid_game_configurations(game: str, rounds: int) -> None:
    validate_run_config(RunConfig(game=game, rounds=rounds))


@pytest.mark.parametrize(
    ("game", "rounds"),
    [
        ("missing", 1),
        ("reaction", 0),
        ("reaction", 21),
        ("number", 101),
        ("verbal", 251),
        ("visual", 51),
    ],
)
def test_invalid_game_configurations_are_rejected(game: str, rounds: int) -> None:
    with pytest.raises(ValueError):
        validate_run_config(RunConfig(game=game, rounds=rounds))


def test_preview_is_explicitly_non_invasive() -> None:
    preview = build_preview(RunConfig(game="reaction", rounds=5))
    assert "PREVIEW ONLY" in preview
    assert "no desktop input will be sent" in preview
    assert "https://www.humanbenchmark.com/tests/reactiontime" in preview
    assert "not a guarantee" in preview


def test_cancelled_run_does_not_import_or_execute_game() -> None:
    cancellation = Event()
    cancellation.set()
    result = run_game(
        RunConfig(game="reaction", rounds=5),
        cancellation,
        lambda _level, _message: None,
    )
    assert result["status"] == "cancelled"


def test_preflight_gate_respects_blocking_checks() -> None:
    from human_benchmark_bot.ui.services import PreflightCheck

    assert can_start_run([PreflightCheck("Display", "passed", "ok", True)])
    assert not can_start_run([PreflightCheck("Viewport", "failed", "missing", True)])
    assert can_start_run([PreflightCheck("Focus", "attention", "manual check", False)])


def test_history_store_is_bounded_and_does_not_store_answers(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.json", limit=2)
    store.add(
        {
            "game": "Reaction Time",
            "rounds": 5,
            "status": "completed_review",
            "elapsed_seconds": 4.1,
        }
    )
    store.add(
        {
            "game": "Number Memory",
            "rounds": 10,
            "status": "failed",
            "elapsed_seconds": 2.0,
            "answer": "123456",
        }
    )
    store.add(
        {
            "game": "Visual Memory",
            "rounds": 4,
            "status": "cancelled",
            "elapsed_seconds": 1.0,
        }
    )

    rows = store.read()
    assert len(rows) == 2
    assert [row["game"] for row in rows] == ["Number Memory", "Visual Memory"]
    assert all("answer" not in row for row in rows)


def test_calibration_round_trip_and_display_mismatch(monkeypatch, tmp_path) -> None:
    import human_benchmark_bot.calibration as calibration_module

    path = tmp_path / "calibration.json"
    monkeypatch.setattr(calibration_module, "calibration_path", lambda: path)

    saved = save_calibration(
        screen_width=1920,
        screen_height=1080,
        x=500,
        y=200,
        width=900,
        height=600,
    )
    assert load_calibration() == saved
    validate_current_display(saved, 1920, 1080)
    with pytest.raises(CalibrationError):
        validate_current_display(saved, 1366, 768)


def test_invalid_calibration_bounds_are_rejected() -> None:
    profile = ScreenCalibration(
        screen_width=1920,
        screen_height=1080,
        x=1800,
        y=900,
        width=300,
        height=300,
        created_at="test",
    )
    with pytest.raises(CalibrationError):
        profile.validate()


def test_history_store_sanitizes_malformed_records_and_unknown_fields(tmp_path) -> None:
    import json

    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            [
                {
                    "timestamp": None,
                    "game": ["invalid"],
                    "rounds": "not-a-number",
                    "status": None,
                    "elapsed_seconds": "nan",
                    "message": {"answer": "private"},
                    "answer": "private",
                    "clipboard": "private",
                },
                "not a record",
                {
                    "timestamp": "2026-10-30T12:00:00+00:00",
                    "game": "Reaction Time",
                    "rounds": 4,
                    "status": "failed",
                    "elapsed_seconds": 1.25,
                    "message": "Routine stopped safely.",
                    "screenshot": "private",
                },
            ]
        ),
        encoding="utf-8",
    )

    rows = HistoryStore(path).read()

    assert len(rows) == 2
    assert rows[0] == {
        "timestamp": "",
        "game": "Unknown game",
        "rounds": 0,
        "status": "unknown",
        "elapsed_seconds": 0.0,
        "message": "",
    }
    assert rows[1]["game"] == "Reaction Time"
    assert rows[1]["elapsed_seconds"] == 1.25
    assert set(rows[1]) == {
        "timestamp",
        "game",
        "rounds",
        "status",
        "elapsed_seconds",
        "message",
    }
    assert all("answer" not in row and "clipboard" not in row for row in rows)

